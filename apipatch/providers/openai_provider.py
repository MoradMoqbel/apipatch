"""
OpenAI Provider implementation for ApiPatch
"""

import os
from typing import Dict, Any, List, Optional
from apipatch.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(api_key=api_key or os.getenv("OPENAI_API_KEY"), model=model or "gpt-4o")

    def audit_code(self, file_name: str, code: str, detected_libraries: List[str]) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set.")

        import openai
        client = openai.OpenAI(api_key=self.api_key)

        libraries_hint = ", ".join(detected_libraries) if detected_libraries else "any imported 3rd-party library"

        system_prompt = f"""You are an autonomous static code auditor and API migration agent for modern software development.
Your goal is to audit source code and detect ANY breaking or deprecated 3rd-party API calls (e.g. OpenAI v1.0+, Pydantic v2, LangChain LCEL, Stripe PaymentIntents, SQLAlchemy 2.0, FastAPI lifespan, Supabase v2, Twilio, HuggingFace, Celery, etc.).

Detected 3rd-party dependencies in this project/file: [{libraries_hint}].

Rules:
1. Examine imports, functions, class configs, and method calls.
2. If deprecated/breaking syntax exists, generate the modernized replacement preserving 100% of business logic.
3. Return ONLY valid JSON matching this schema:
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
  "refactored_code": "Full refactored file code preserving 100% logic and syntax correctness"
}}
If no breaking changes are found, set has_breaking_changes to false, detected_issues to [], and refactored_code to the original code.
"""

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"File: {file_name}\n\nSource Code:\n{code}"}
            ],
            temperature=0.0,
            response_format={"type": "json_object"} if "gpt-4o" in self.model or "o3" in self.model else None
        )

        raw_text = response.choices[0].message.content
        return self.clean_json_response(raw_text)
