"""Multimodal guardrails starter (images / PDF previews).

Wire a small VLM or provider moderation here; this module stays import-safe without torch.
"""

from __future__ import annotations

from typing import Any, Dict


def analyze_image_stub(image_bytes: bytes, policy: str = "default") -> Dict[str, Any]:
    """Placeholder until a vision model or cloud moderation is configured."""
    _ = image_bytes
    return {
        "status": "skipped",
        "policy": policy,
        "reason": "vision_pipeline_not_configured",
        "pii_entities": [],
        "toxicity_score": None,
        "modality": "image",
    }


def analyze_pdf_bytes_stub(pdf_bytes: bytes, policy: str = "default") -> Dict[str, Any]:
    """PDF path: extract text then run text rails; stub returns metadata only."""
    _ = pdf_bytes
    return {
        "status": "skipped",
        "policy": policy,
        "reason": "pdf_text_pipeline_not_configured",
        "modality": "pdf",
        "page_count_estimate": None,
        "toxicity_score": None,
        "pii_hint": "wire rules/pii_india after text extraction",
    }
