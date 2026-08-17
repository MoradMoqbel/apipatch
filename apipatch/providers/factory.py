"""
LLM Provider Factory for ApiPatch
"""

import os
from typing import Optional
from apipatch.providers.base import BaseProvider
from apipatch.providers.openai_provider import OpenAIProvider
from apipatch.providers.anthropic_provider import AnthropicProvider
from apipatch.providers.gemini_provider import GeminiProvider


class ProviderFactory:
    @staticmethod
    def get_provider(
        provider_name: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ) -> Optional[BaseProvider]:
        """
        Instantiates appropriate LLM provider.
        If provider_name is not specified, auto-discovers based on available API keys.
        """
        # Explicit provider selection
        if provider_name:
            provider_name = provider_name.lower().strip()
            if provider_name == "openai":
                return OpenAIProvider(api_key=api_key, model=model)
            elif provider_name in {"anthropic", "claude"}:
                return AnthropicProvider(api_key=api_key, model=model)
            elif provider_name in {"gemini", "google"}:
                return GeminiProvider(api_key=api_key, model=model)
            else:
                raise ValueError(f"Unknown provider '{provider_name}'. Supported: openai, anthropic, gemini")

        # Auto-discovery by environment variables or passed API key
        if api_key:
            return OpenAIProvider(api_key=api_key, model=model)

        if os.getenv("OPENAI_API_KEY"):
            return OpenAIProvider(model=model)
        elif os.getenv("ANTHROPIC_API_KEY"):
            return AnthropicProvider(model=model)
        elif os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
            return GeminiProvider(model=model)

        return None
