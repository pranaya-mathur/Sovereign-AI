"""Sovereign AI LlamaIndex Integration."""

from typing import Any, Optional
import httpx
import logging

logger = logging.getLogger(__name__)

class SovereignLlamaGuard:
    """LlamaIndex Post-Processor for content guarding."""
    
    def __init__(self, endpoint: str = "http://localhost:8000/api/detect", api_key: Optional[str] = None):
        self.endpoint = endpoint
        self.api_key = api_key

    def postprocess_response(self, response: Any) -> Any:
        """Process response from LlamaIndex query engine."""
        text = str(response)
        
        try:
            with httpx.Client(timeout=10.0) as client:
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                res = client.post(
                    self.endpoint,
                    json={"text": text, "context": {}},
                    headers=headers
                )
                
                if res.status_code == 200:
                    data = res.json()
                    if data.get("action") == "block":
                        raise PermissionError(f"Security Policy Violation: {data.get('explanation')}")
        except PermissionError:
            raise
        except Exception as e:
            logger.warning("Sovereign AI call failed: %s", e)
            
        return response
