"""LLM provider integrations for Groq and Ollama (100% free).

Provides unified interface for LLM calls with fallback support.
"""

import os
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod


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

        if self.api_key:
            try:
                from langchain.chat_models import ChatGroq

                self.client = ChatGroq(
                    groq_api_key=self.api_key,
                    model_name=self.model,
                    temperature=0.0,  # Deterministic responses
                )
            except ImportError:
                raise ImportError(
                    "langchain not installed. Run: pip install langchain langchain-groq"
                )

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate response using Groq API."""
        if not self.client:
            raise ValueError("Groq API key not configured")

        try:
            from langchain.schema import HumanMessage

            response = self.client([HumanMessage(content=prompt)])
            return {
                "content": response.content,
                "model": self.model,
                "provider": "groq",
                "success": True,
            }
        except Exception as e:
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

        try:
            from langchain_community.llms import Ollama

            self.client = Ollama(
                model=self.model,
                base_url=self.base_url,
                temperature=0.0,
            )
        except ImportError:
            raise ImportError(
                "langchain-community not installed. Run: pip install langchain-community"
            )

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate response using Ollama."""
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

    def __init__(self):
        """Initialize provider manager with Groq and Ollama."""
        self.providers = []

        # Try Groq first (faster, cloud-based)
        try:
            groq = GroqProvider()
            if groq.is_available():
                self.providers.append(groq)
        except:
            pass

        # Fallback to Ollama (local, always available if running)
        try:
            ollama = OllamaProvider()
            if ollama.is_available():
                self.providers.append(ollama)
        except:
            pass

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
