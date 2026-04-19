"""Agentic / tool-use rails: whitelist validation and goal-hijack heuristics (OWASP Agentic Top 10)."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Set, Tuple

from contracts.failure_classes import FailureClass

_GOAL_HIJACK_PATTERNS: Tuple[Tuple[re.Pattern, float], ...] = (
    (re.compile(r"\bignore\s+(all\s+)?(previous|prior|above)\s+instructions\b", re.I), 0.92),
    (re.compile(r"\bdisregard\s+(your|the)\s+(rules|guidelines|policy)\b", re.I), 0.88),
    (re.compile(r"\bnew\s+(system|developer)\s+message\b", re.I), 0.85),
    (re.compile(r"\bgoal\s*:\s*(exfiltrate|steal|leak|dump)\b", re.I), 0.9),
    (re.compile(r"\b(you\s+)?must\s+(now\s+)?call\s+the\s+tool\b", re.I), 0.55),
    (re.compile(r"\boverride\s+(safety|guardrails|filters)\b", re.I), 0.87),
)


def goal_hijack_score(text: str) -> float:
    """Return 0..1 heuristic score for goal hijack / instruction override attempts."""
    if not text:
        return 0.0
    best = 0.0
    for pat, score in _GOAL_HIJACK_PATTERNS:
        if pat.search(text):
            best = max(best, score)
    return round(best, 4)


def validate_tool_use(
    tool_name: str,
    allowed: Optional[Set[str]],
) -> tuple[bool, str]:
    """If ``allowed`` is set, only those tool names may run (ASI02 tool misuse)."""
    if not tool_name:
        return True, ""
    if allowed is None:
        return True, ""
    if tool_name in allowed:
        return True, ""
    return False, f"tool_not_whitelisted:{tool_name}"


def agentic_preflight(text: str, context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Return a Tier-3-style dict to short-circuit LLM if rails trip; else None."""
    ctx = context or {}
    tool = ctx.get("tool_name") or ctx.get("planned_tool")
    allowed_raw = ctx.get("allowed_tools") or ctx.get("allowed_tool_names")
    allowed: Optional[Set[str]] = None
    if allowed_raw is not None:
        allowed = set(allowed_raw) if not isinstance(allowed_raw, set) else allowed_raw
    if tool:
        ok, reason = validate_tool_use(str(tool), allowed)
        if not ok:
            return {
                "confidence": 0.95,
                "failure_class": FailureClass.PROMPT_INJECTION,
                "method": "agentic_tool_rail",
                "should_allow": False,
                "explanation": reason,
            }
    gh = goal_hijack_score(text)
    if gh >= 0.88:
        return {
            "confidence": gh,
            "failure_class": FailureClass.PROMPT_INJECTION,
            "method": "agentic_goal_hijack_heuristic",
            "should_allow": False,
            "explanation": "Goal hijack / instruction override pattern (agentic rail)",
        }
    return None
