"""
Anthropic Claude Provider implementation for ApiPatch
"""

import os
from typing import Dict, Any, List, Optional
from apipatch.providers.base import BaseProvider


class AnthropicProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"), model=model or "claude-3-7-sonnet-20250219")

    def audit_code(self, file_name: str, code: str, detected_libraries: List[str]) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set.")

        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)

        libraries_hint = ", ".join(detected_libraries) if detected_libraries else "any imported 3rd-party library"

        prompt = f"""You are an expert static code analysis & API deprecation audit agent.
Analyze the source code of {file_name}.
Audit for deprecated or breaking 3rd-party API calls across any library (e.g. OpenAI, Pydantic, Stripe, LangChain, Supabase, SQLAlchemy, etc.).
Known detected dependencies in context: [{libraries_hint}].

Return a valid JSON object ONLY with the following schema (no preamble, no markdown, ONLY JSON):
{{
  "has_breaking_changes": true/false,
  "detected_issues": [
    {{
      "library": "package name",
      "deprecated_symbol": "exact code pattern that is deprecated",
      "replacement_symbol": "modern recommended replacement",
      "description": "Short explanation of the breaking change",
      "line_hint": "approximate code line"
    }}
  ],
  "refactored_code": "The complete modern refactored version of the entire file code preserving 100% of business logic"
}}

Source Code:
{code}
"""

        message = client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}]
        )

        raw_text = message.content[0].text
        return self.clean_json_response(raw_text)
