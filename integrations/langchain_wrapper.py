"""Sovereign AI LangChain Integration.
Allows using Sovereign AI as a Runnable tool or middle layer.
"""

from typing import Any, Dict, List, Optional
from langchain_core.runnables import RunnableSerializable, RunnableConfig
from langchain_core.messages import BaseMessage
import httpx

class SovereignLangChainGuard(RunnableSerializable[Any, Any]):
    """LangChain Runnable that guards against unsafe content."""
    
    endpoint: str = "http://localhost:8000/detect"
    api_key: Optional[str] = None
    
    def invoke(self, input: Any, config: Optional[RunnableConfig] = None) -> Any:
        # Determine text to check
        text = ""
        if isinstance(input, str):
            text = input
        elif isinstance(input, list) and len(input) > 0:
            if hasattr(input[-1], "content"):
                text = input[-1].content
            else:
                text = str(input[-1])
        
        # Call Sovereign AI
        try:
            with httpx.Client(timeout=10.0) as client:
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                
                response = client.post(
                    self.endpoint,
                    json={"llm_response": text, "context": {}},
                    headers=headers
                )
                
                if response.status_code == 200:
                    res = response.json()
                    if res.get("action") == "block":
                        raise ValueError(f"Sovereign AI Blocked: {res.get('explanation')}")
        except Exception as e:
            if "Sovereign AI Blocked" in str(e):
                raise e
            # Log and allow if system is down (fail-safe)
            print(f"Sovereign AI Integration Error: {e}")
            
        return input
