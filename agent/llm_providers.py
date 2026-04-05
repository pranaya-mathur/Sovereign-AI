"""LLM provider integrations for Groq and Ollama (100% free).

Provides unified interface for LLM calls with fallback support.
"""

import os
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import time
from opentelemetry import trace
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate response from LLM."""
        pass


class GroqProvider(LLMProvider):
    """Groq API provider (free tier: 14,400 requests/day)."""

    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        """
        Initialize Groq provider.

        Args:
            api_key: Groq API key (or set GROQ_API_KEY env var)
            model: Model name (default: llama-3.3-70b-versatile)
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self.client = None
        self.tracer = trace.get_tracer("sovereign-llm-provider")

        if self.api_key:
            try:
                from langchain_groq import ChatGroq

                self.client = ChatGroq(
                    groq_api_key=self.api_key,
                    model_name=self.model,
                    temperature=0.0,  # Deterministic responses
                )
            except ImportError:
                raise ImportError(
                    "langchain-groq not installed. Run: pip install langchain-groq"
                )
            except Exception as e:
                print(f"Warning: Groq initialization failed: {e}")

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate response using Groq API with tracing."""
        with self.tracer.start_as_current_span(f"groq_generate:{self.model}") as span:
            if not self.client:
                raise ValueError("Groq API key not configured")

            try:
                from langchain_core.messages import HumanMessage

                response = self.client.invoke([HumanMessage(content=prompt)])
                return {
                    "content": response.content,
                    "model": self.model,
                    "provider": "groq",
                    "success": True,
                }
            except Exception as e:
                span.record_exception(e)
                return {
                    "content": "",
                    "model": self.model,
                    "provider": "groq",
                    "success": False,
                    "error": str(e),
                }

    def is_available(self) -> bool:
        """Check if Groq is configured and accessible."""
        return self.client is not None


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider (100% free, runs locally)."""

    def __init__(
        self,
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434",
    ):
        """
        Initialize Ollama provider.

        Args:
            model: Model name (default: llama3.2)
            base_url: Ollama server URL
        """
        self.model = model
        self.base_url = base_url
        self.client = None
        self.tracer = trace.get_tracer("sovereign-llm-provider")

        try:
            from langchain_ollama import OllamaLLM

            self.client = OllamaLLM(
                model=self.model,
                base_url=self.base_url,
                temperature=0.0,
            )
        except ImportError:
            raise ImportError(
                "langchain-ollama not installed. Run: pip install langchain-ollama"
            )
        except Exception as e:
            print(f"Warning: Ollama initialization failed: {e}")

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate response using Ollama with tracing."""
        with self.tracer.start_as_current_span(f"ollama_generate:{self.model}") as span:
            if not self.client:
                raise ValueError("Ollama not configured")

            try:
                response = self.client.invoke(prompt)
                return {
                    "content": response,
                    "model": self.model,
                    "provider": "ollama",
                    "success": True,
                }
            except Exception as e:
                span.record_exception(e)
                return {
                    "content": "",
                    "model": self.model,
                    "provider": "ollama",
                    "success": False,
                    "error": str(e),
                }

    def is_available(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            import httpx

            response = httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
            return response.status_code == 200
        except:
            return False


class LLMProviderManager:
    """Manages multiple LLM providers with fallback support."""

    def __init__(self, policy_path: str = "config/policy.yaml"):
        """Initialize provider manager with Groq and Ollama."""
        self.providers = []
        
        # Load policy configuration
        from config.policy_loader import PolicyLoader
        try:
            policy = PolicyLoader(policy_path)
            llm_config = policy.get_llm_config()
        except Exception as e:
            print(f"⚠️ Could not load policy for LLM providers: {e}")
            llm_config = {
                "groq_model": "llama-3.3-70b-versatile",
                "ollama_model": "llama3.2",
                "ollama_base_url": "http://localhost:11434"
            }

        # Try Groq first (faster, cloud-based)
        try:
            groq = GroqProvider(model=llm_config["groq_model"])
            if groq.is_available():
                self.providers.append(groq)
                print("✅ Groq provider initialized")
        except Exception as e:
            print(f"⚠️ Groq provider not available: {e}")

        # Fallback to Ollama (local, always available if running)
        try:
            ollama = OllamaProvider(
                model=llm_config["ollama_model"],
                base_url=llm_config["ollama_base_url"]
            )
            if ollama.is_available():
                self.providers.append(ollama)
                print("✅ Ollama provider initialized")
        except Exception as e:
            print(f"⚠️ Ollama provider not available: {e}")

        if not self.providers:
            print("⚠️ No LLM providers available. Tier 3 detection will not work.")

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate response with automatic fallback."""
        if not self.providers:
            return {
                "content": "",
                "success": False,
                "error": "No LLM providers available",
            }

        # Try each provider in order
        for provider in self.providers:
            result = provider.generate(prompt, **kwargs)
            if result["success"]:
                return result

        # All providers failed
        return {
            "content": "",
            "success": False,
            "error": "All LLM providers failed",
        }

    def get_available_providers(self) -> list[str]:
        """List available provider names."""
        return [p.__class__.__name__ for p in self.providers]
