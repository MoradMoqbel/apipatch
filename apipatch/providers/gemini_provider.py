"""
Google Gemini Provider implementation for ApiPatch
"""

import os
from typing import Dict, Any, List, Optional
from apipatch.providers.base import BaseProvider


class GeminiProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(api_key=api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"), model=model or "gemini-2.5-flash")

    def audit_code(self, file_name: str, code: str, detected_libraries: List[str]) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is not set.")

        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)

            libraries_hint = ", ".join(detected_libraries) if detected_libraries else "any imported 3rd-party library"
            prompt = f"""You are an expert static code analysis & API deprecation audit agent.
Analyze the source code of {file_name}.
Audit for deprecated or breaking 3rd-party API calls across any library (e.g. OpenAI, Pydantic, Stripe, LangChain, Supabase, SQLAlchemy, etc.).
Known detected dependencies in context: [{libraries_hint}].

Return a valid JSON object ONLY with the following schema:
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
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            raw_text = response.text
            return self.clean_json_response(raw_text)
        except ImportError:
            # Try legacy google.generativeai if google-genai is not installed
            import google.generativeai as genai_legacy
            genai_legacy.configure(api_key=self.api_key)
            model_inst = genai_legacy.GenerativeModel(self.model)
            response = model_inst.generate_content(prompt)
            return self.clean_json_response(response.text)
