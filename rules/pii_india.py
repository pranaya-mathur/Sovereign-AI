"""India-focused PII and sensitive identifier detection with Presidio-style results.

Regex-based (no extra ML deps). Returns spans, entity types, per-match confidence,
and redacted text suitable for DPDP-oriented pipelines.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple


@dataclass
class PIIMatch:
    """A single detected span (Presidio-like)."""

    entity_type: str
    start: int
    end: int
    text: str
    score: float
    recognition_metadata: Dict[str, str] = field(default_factory=dict)


# Order matters: longer / more specific patterns first where applicable.
_PATTERNS: List[Tuple[str, str, float]] = [
    (
        "IN_AADHAAR",
        r"\b\d{4}\s?\d{4}\s?\d{4}\b",
        0.85,
    ),
    (
        "IN_PAN",
        r"\b[A-Z]{5}\d{4}[A-Z]\b",
        0.9,
    ),
    (
        "IN_GSTIN",
        r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d][Z][A-Z\d]\b",
        0.88,
    ),
    (
        "IN_UPI_VPA",
        r"\b[a-zA-Z0-9._-]{2,256}@[a-zA-Z][a-zA-Z._-]+\b",
        0.55,
    ),
    (
        "IN_IFSC",
        r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
        0.82,
    ),
    (
        "IN_VEHICLE_REG",
        r"\b[A-Z]{2}\s?\d{2}\s?[A-Z]{1,2}\s?\d{3,4}\b",
        0.6,
    ),
    (
        "IN_PINCODE",
        r"\b[1-9][0-9]{5}\b",
        0.35,
    ),
    (
        "PHONE_IN",
        r"(?:\+91[\s-]?)?(?:0)?[6-9]\d{9}\b",
        0.75,
    ),
    (
        "EMAIL",
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        0.65,
    ),
    (
        "CREDIT_CARD_LIKE",
        r"\b(?:\d[ -]*?){13,19}\b",
        0.4,
    ),
]

_COMPILED: List[Tuple[str, re.Pattern, float]] = [
    (name, re.compile(pat), score) for name, pat, score in _PATTERNS
]


def _refine_scores(text: str, matches: List[PIIMatch]) -> List[PIIMatch]:
    refined: List[PIIMatch] = []
    for m in matches:
        if m.entity_type == "IN_AADHAAR":
            raw = re.sub(r"\D", "", m.text)
            # 12 digits starting with 91 + mobile range = +91 mobile, not Aadhaar
            if len(raw) == 12 and raw.startswith("91") and raw[2] in "6789" and raw[2:].isdigit():
                refined.append(
                    PIIMatch(
                        entity_type="PHONE_IN",
                        start=m.start,
                        end=m.end,
                        text=m.text,
                        score=0.88,
                        recognition_metadata={"reclassified_from": "IN_AADHAAR"},
                    )
                )
                continue
            meta: Dict[str, str] = {"digits": str(len(raw))}
            refined.append(
                PIIMatch(
                    entity_type=m.entity_type,
                    start=m.start,
                    end=m.end,
                    text=m.text,
                    score=m.score if len(raw) == 12 else max(0.05, m.score - 0.3),
                    recognition_metadata=meta,
                )
            )
        elif m.entity_type == "IN_PINCODE":
            refined.append(
                PIIMatch(
                    entity_type=m.entity_type,
                    start=m.start,
                    end=m.end,
                    text=m.text,
                    score=m.score,
                    recognition_metadata={"note": "weak_location_signal"},
                )
            )
        else:
            refined.append(m)
    return refined


def detect_india_pii(text: str) -> List[PIIMatch]:
    """Return non-overlapping matches (greedy by start, prefer higher score on tie)."""
    if not text:
        return []
    raw: List[PIIMatch] = []
    for entity_type, pattern, base_score in _COMPILED:
        for m in pattern.finditer(text):
            raw.append(
                PIIMatch(
                    entity_type=entity_type,
                    start=m.start(),
                    end=m.end(),
                    text=m.group(0),
                    score=base_score,
                )
            )
    raw.sort(key=lambda x: (-x.score, x.start, -(x.end - x.start)))
    used: List[Tuple[int, int]] = []
    chosen: List[PIIMatch] = []
    for m in raw:
        overlap = any(not (m.end <= s or m.start >= e) for s, e in used)
        if overlap:
            continue
        used.append((m.start, m.end))
        chosen.append(m)
    chosen.sort(key=lambda x: x.start)
    return _refine_scores(text, chosen)


def redact_india_pii(
    text: str,
    mask: str = "[REDACTED]",
    mask_builder: Optional[Callable[[PIIMatch], str]] = None,
) -> Dict[str, object]:
    """Redact detected spans; return structured result for APIs and audits."""
    matches = detect_india_pii(text)
    if not matches:
        return {
            "redacted_text": text,
            "matches": [],
            "entity_counts": {},
            "aggregate_score": 0.0,
        }

    parts: List[str] = []
    cursor = 0
    counts: Dict[str, int] = {}
    serializable_matches: List[Dict[str, object]] = []

    for m in matches:
        counts[m.entity_type] = counts.get(m.entity_type, 0) + 1
        replacement = mask_builder(m) if mask_builder else f"{mask}:{m.entity_type}"
        parts.append(text[cursor : m.start])
        parts.append(replacement)
        cursor = m.end
        serializable_matches.append(
            {
                "entity_type": m.entity_type,
                "start": m.start,
                "end": m.end,
                "score": m.score,
                "recognition_metadata": m.recognition_metadata,
            }
        )
    parts.append(text[cursor:])
    aggregate = sum(m.score for m in matches) / len(matches)
    return {
        "redacted_text": "".join(parts),
        "matches": serializable_matches,
        "entity_counts": counts,
        "aggregate_score": round(aggregate, 4),
    }
