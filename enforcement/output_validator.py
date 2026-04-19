"""Post-LLM groundedness scoring and optional self-correction via Tier 3."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


def _tokenize(s: str) -> set:
    s = s.lower()
    return set(re.findall(r"[a-z0-9]{3,}", s))


def compute_groundedness(response: str, source_text: str) -> float:
    """Lexical overlap score in [0, 1] — fast baseline without extra models."""
    if not response or not source_text:
        return 0.0
    rt = _tokenize(response)
    st = _tokenize(source_text)
    if not rt or not st:
        return 0.0
    inter = len(rt & st)
    union = len(rt | st)
    if union == 0:
        return 0.0
    return round(inter / union, 4)


def run_output_validation(
    llm_response: str,
    context: Dict[str, Any],
    llm_agent: Any,
    threshold: float = 0.7,
    max_retries: int = 1,
) -> Dict[str, Any]:
    """Score groundedness; optionally ask Tier 3 to produce a corrected answer."""
    user_prompt = (context or {}).get("user_prompt") or (context or {}).get("query") or ""
    retrieval = (context or {}).get("retrieval_context") or (context or {}).get("documents") or ""
    source = (retrieval if retrieval else user_prompt).strip()
    if not source:
        return {
            "groundedness_score": None,
            "skipped": True,
            "reason": "no_source_context",
            "corrected_response": None,
            "attempts": 0,
        }

    score = compute_groundedness(llm_response, source)
    out: Dict[str, Any] = {
        "groundedness_score": score,
        "skipped": False,
        "corrected_response": None,
        "attempts": 0,
    }

    if score >= threshold or not llm_agent:
        return out

    attempts = 0
    corrected = llm_response
    for _ in range(max_retries):
        attempts += 1
        if hasattr(llm_agent, "revise_for_grounding"):
            rev = llm_agent.revise_for_grounding(corrected, source, user_prompt)
        else:
            break
        corrected = rev.get("revised_response", corrected)
        new_score = rev.get("groundedness_score", compute_groundedness(corrected, source))
        out["corrected_response"] = corrected
        out["groundedness_score"] = new_score
        out["attempts"] = attempts
        if new_score >= threshold:
            break

    return out
