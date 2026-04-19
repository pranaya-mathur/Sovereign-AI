from typing import Dict, Any, List, Optional
from signals.registry import ALL_SIGNALS


def run_signals(
    *,
    prompt: str,
    response: str,
    metadata: Optional[Dict[str, Any]] = None
) -> List[dict]:
    metadata = metadata or {}
    results = []

    for signal in ALL_SIGNALS:
        results.append(
            signal.extract(
                prompt=prompt,
                response=response,
                metadata=metadata
            )
        )

    return results
