"""Optional cloud moderation: OpenAI, Azure AI Content Safety, Anthropic (lite).

Scores are fused in ``TierRouter.fuse_external`` / ``fuse_external_with_tier1`` after Tier 1.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from contracts.failure_classes import FailureClass

logger = logging.getLogger(__name__)


def _post_json(url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout: float = 12.0) -> Optional[Dict[str, Any]]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
        logger.debug("external moderation request failed: %s", e)
        return None


def moderate_openai(text: str, api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """OpenAI moderations API."""
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key or not text:
        return None
    url = "https://api.openai.com/v1/moderations"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body = _post_json(url, headers, {"model": "text-moderation-latest", "input": text[:32000]})
    if not body or "results" not in body:
        return None
    res = body["results"][0]
    cats = res.get("category_scores") or {}
    flagged = bool(res.get("flagged"))
    max_score = max((float(v) for v in cats.values()), default=0.0)
    return {
        "provider": "openai",
        "flagged": flagged,
        "max_category_score": max_score,
        "categories": cats,
    }


def moderate_azure_content_safety(text: str) -> Optional[Dict[str, Any]]:
    """Azure AI Content Safety text analyze (REST).

    Env:
      ``AZURE_CONTENT_SAFETY_ENDPOINT`` — e.g. ``https://<name>.cognitiveservices.azure.com``
      ``AZURE_CONTENT_SAFETY_KEY`` — subscription key
    """
    endpoint = (os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT") or "").rstrip("/")
    key = os.getenv("AZURE_CONTENT_SAFETY_KEY")
    if not endpoint or not key or not text:
        return None
    url = f"{endpoint}/contentsafety/text:analyze?api-version=2023-10-01"
    headers = {"Ocp-Apim-Subscription-Key": key, "Content-Type": "application/json"}
    payload = {
        "text": text[:10000],
        "categories": ["Hate", "SelfHarm", "Sexual", "Violence"],
        "outputType": "FourSeverityLevels",
    }
    body = _post_json(url, headers, payload)
    if not body:
        return None
    analyses = body.get("categoriesAnalysis") or body.get("categoriesAnalysisResults") or []
    severities: List[float] = []
    for item in analyses:
        sev = item.get("severity")
        if isinstance(sev, (int, float)):
            severities.append(float(sev))
    max_sev = max(severities, default=0.0)
    max_score = min(1.0, max_sev / 6.0) if severities else 0.0
    flagged = max_sev >= 4
    return {
        "provider": "azure_content_safety",
        "flagged": flagged,
        "max_category_score": max_score,
        "categories": {"max_severity": max_sev},
    }


def moderate_anthropic_lite(text: str) -> Optional[Dict[str, Any]]:
    """Optional single-digit toxicity probe (costs a Haiku call).

    Set ``ANTHROPIC_MODERATION_LITE=true`` and ``ANTHROPIC_API_KEY``.
    """
    if os.getenv("ANTHROPIC_MODERATION_LITE", "").lower() not in ("1", "true", "yes"):
        return None
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key or not text:
        return None
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 8,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Reply with one digit 0-9 only (9=max toxicity) for this user text, "
                    "no other characters:\n\n" + text[:1800]
                ),
            }
        ],
    }
    body = _post_json(url, headers, payload, timeout=20.0)
    if not body:
        return None
    content = ""
    for block in body.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            content += block.get("text", "")
    digit = None
    for ch in content:
        if ch.isdigit():
            digit = int(ch)
            break
    if digit is None:
        return None
    score = min(1.0, digit / 9.0)
    return {
        "provider": "anthropic_lite",
        "flagged": score >= 0.72,
        "max_category_score": score,
        "categories": {},
    }


def aggregate_external_results(results: List[Optional[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
    """Fuse multiple provider payloads: max score, any-flagged, per-source breakdown."""
    parts = [r for r in results if r]
    if not parts:
        return None
    flagged = any(bool(p.get("flagged")) for p in parts)
    max_score = max(float(p.get("max_category_score") or 0.0) for p in parts)
    return {
        "provider": "fused",
        "flagged": flagged,
        "max_category_score": max_score,
        "categories": {},
        "sources": [
            {"provider": p.get("provider"), "max_category_score": p.get("max_category_score"), "flagged": p.get("flagged")}
            for p in parts
        ],
    }


def run_external_moderation_pipeline(text: str, cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Run providers from policy (order preserved); return fused scores or None."""
    raw = cfg.get("providers")
    if raw is None:
        legacy = cfg.get("provider", "openai")
        providers = [legacy] if isinstance(legacy, str) else ["openai"]
    elif isinstance(raw, str):
        providers = [raw]
    else:
        providers = list(raw)
    results: List[Optional[Dict[str, Any]]] = []
    for name in providers:
        n = (name or "").strip().lower()
        if n == "openai":
            results.append(moderate_openai(text))
        elif n in ("azure", "azure_content_safety", "azure-contentsafety"):
            results.append(moderate_azure_content_safety(text))
        elif n in ("anthropic", "anthropic_lite"):
            results.append(moderate_anthropic_lite(text))
        else:
            logger.debug("unknown external moderation provider: %s", name)
    return aggregate_external_results(results)


def fuse_external_with_tier1(
    tier1_result: Dict[str, Any],
    external: Optional[Dict[str, Any]],
    fuse_weight: float = 0.35,
) -> Dict[str, Any]:
    """Raise threat confidence when external moderation is hot; keep structure."""
    if not external:
        return tier1_result
    out = dict(tier1_result)
    ext_score = float(external.get("max_category_score") or 0.0)
    if external.get("flagged") or ext_score >= 0.6:
        base = float(out.get("confidence", 0.0))
        fused = min(0.99, base + fuse_weight * ext_score)
        out["confidence"] = fused
        out["method"] = f"{out.get('method', 'regex')}+external"
        meta: Dict[str, Any] = {
            "provider": external.get("provider"),
            "flagged": external.get("flagged"),
            "max_category_score": ext_score,
        }
        if external.get("sources"):
            meta["sources"] = external["sources"]
        out["external_moderation"] = meta
        if fused >= 0.5 and out.get("failure_class") is None and external.get("flagged"):
            out["failure_class"] = FailureClass.TOXICITY
            out["should_allow"] = False
            out["explanation"] = "External moderation flagged content"
    else:
        meta = {"provider": external.get("provider"), "max_category_score": ext_score}
        if external.get("sources"):
            meta["sources"] = external["sources"]
        out["external_moderation"] = meta
    return out
