#!/usr/bin/env python3
"""Nightly-style red-team runner: load templates and score /detect outcomes.

Usage:
  BASE_URL=http://127.0.0.1:8000 python scripts/redteam/run_redteam.py

Uses unauthenticated POST /detect (api.main_v2) by default. For /api/detect,
set USE_AUTH and provide TOKEN (Bearer).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_templates(path: Path) -> List[str]:
    lines: List[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if s and not s.startswith("#"):
            lines.append(s)
    return lines


def post_detect(base: str, text: str, token: Optional[str]) -> Dict[str, Any]:
    url = base.rstrip("/") + "/detect"
    payload = json.dumps({"llm_response": text, "context": {"redteam": True}}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": str(e), "body": body[:500]}
    except Exception as e:
        return {"error": str(e)}


def score_response(data: Dict[str, Any]) -> str:
    if data.get("error"):
        return "error"
    if data.get("blocked") is True or data.get("action") == "block":
        return "blocked"
    if data.get("action") in ("warn", "log"):
        return "flagged"
    return "allowed"


def main() -> int:
    p = argparse.ArgumentParser(description="Red-team templates against /detect")
    p.add_argument("--base-url", default=os.getenv("BASE_URL", "http://127.0.0.1:8000"))
    p.add_argument(
        "--templates",
        default=str(Path(__file__).resolve().parent / "jailbreak_templates.txt"),
    )
    p.add_argument("--token", default=os.getenv("TOKEN"))
    args = p.parse_args()

    tpl_path = Path(args.templates)
    if not tpl_path.exists():
        print(f"Missing templates: {tpl_path}", file=sys.stderr)
        return 2

    templates = load_templates(tpl_path)
    exp_path = Path(__file__).resolve().parent / "expanded_templates.py"
    if exp_path.exists():
        spec = importlib.util.spec_from_file_location("redteam_expanded", exp_path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            templates = templates + mod.extra_owasp_and_agentic_templates()
    counts = {"blocked": 0, "flagged": 0, "allowed": 0, "error": 0}
    print(f"Loaded {len(templates)} red-team prompts (file + expanded corpus).", file=sys.stderr)

    for i, text in enumerate(templates):
        data = post_detect(args.base_url, text, args.token)
        label = score_response(data)
        counts[label] = counts.get(label, 0) + 1
        print(f"[{i+1:03d}/{len(templates)}] {label:8s} {text[:72]!r}")

    print(json.dumps({"summary": counts, "total": len(templates)}, indent=2))
    return 0 if counts["error"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
