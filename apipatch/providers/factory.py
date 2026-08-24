"""
LLM Provider Factory for ApiPatch
"""

import os
from typing import Optional
from apipatch.providers.base import BaseProvider
from apipatch.providers.openai_provider import OpenAIProvider
from apipatch.providers.anthropic_provider import AnthropicProvider
from apipatch.providers.gemini_provider import GeminiProvider
from apipatch.providers.bedrock_provider import BedrockProvider


def _load_env_file():
    """Lightweight .env loader without external dependencies."""
    pkg_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for env_path in [os.path.join(os.getcwd(), ".env"), os.path.join(pkg_dir, ".env")]:
        if os.path.isfile(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k and k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass

    # Normalize common AWS and Gemini variable aliases
    if "gemini_api_key" in os.environ and "GEMINI_API_KEY" not in os.environ:
        os.environ["GEMINI_API_KEY"] = os.environ["gemini_api_key"]
    if "aws_access_key" in os.environ and "AWS_ACCESS_KEY_ID" not in os.environ:
        os.environ["AWS_ACCESS_KEY_ID"] = os.environ["aws_access_key"]
    if "aws_secret_client" in os.environ and "AWS_SECRET_ACCESS_KEY" not in os.environ:
        os.environ["AWS_SECRET_ACCESS_KEY"] = os.environ["aws_secret_client"]
    if "aws_region" in os.environ and "AWS_REGION" not in os.environ:
        os.environ["AWS_REGION"] = os.environ["aws_region"]


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
        _load_env_file()

        # Explicit provider selection
        if provider_name:
            provider_name = provider_name.lower().strip()
            if provider_name == "openai":
                return OpenAIProvider(api_key=api_key, model=model)
            elif provider_name in {"anthropic", "claude"}:
                return AnthropicProvider(api_key=api_key, model=model)
            elif provider_name in {"gemini", "google", "vertex", "vertexai"}:
                return GeminiProvider(api_key=api_key, model=model)
            elif provider_name in {"bedrock", "aws", "aws_bedrock"}:
                return BedrockProvider(api_key=api_key, model=model)
            else:
                raise ValueError(f"Unknown provider '{provider_name}'. Supported: openai, anthropic, gemini, vertex, bedrock")

        # Auto-discovery by environment variables, service account credentials, or passed API key
        if api_key:
            if ":" in api_key:
                return BedrockProvider(api_key=api_key, model=model)
            return OpenAIProvider(api_key=api_key, model=model)

        if os.getenv("OPENAI_API_KEY"):
            return OpenAIProvider(model=model)
        elif os.getenv("ANTHROPIC_API_KEY"):
            return AnthropicProvider(model=model)
        elif (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            or os.getenv("VERTEX_PROJECT")
            or os.getenv("GOOGLE_CLOUD_PROJECT")
        ):
            return GeminiProvider(model=model)
        elif (
            os.getenv("AWS_ACCESS_KEY_ID")
            or os.getenv("AWS_ACCESS_KEY")
            or os.getenv("aws_access_key")
        ) and (
            os.getenv("AWS_SECRET_ACCESS_KEY")
            or os.getenv("AWS_SECRET_KEY")
            or os.getenv("AWS_SECRET_CLIENT")
            or os.getenv("aws_secret_client")
        ):
            return BedrockProvider(model=model)
        elif os.path.isfile("gcc_auth.json") or os.path.isfile("gcc-auth.json"):
            return GeminiProvider(model=model)

        return None

