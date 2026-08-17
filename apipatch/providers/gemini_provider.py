"""
Google Gemini Provider implementation for ApiPatch
Supports direct Google Generative Language API via standard REST requests and Google GenAI SDK.
"""

import os
import json
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from apipatch.providers.base import BaseProvider


class GeminiProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(
            api_key=api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
            model=model or "gemini-1.5-flash"
        )

    def audit_code(self, file_name: str, code: str, detected_libraries: List[str]) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is not set.")

        libraries_hint = ", ".join(detected_libraries) if detected_libraries else "any imported 3rd-party library"
        prompt = f"""You are an expert static code analysis & API deprecation audit agent.
Analyze the source code of {file_name}.
Audit for deprecated or breaking 3rd-party API calls across any library (e.g. OpenAI, Pydantic, Stripe, LangChain, Supabase, SQLAlchemy, etc.).
Detected dependencies in context: [{libraries_hint}].

Rules:
1. If there are NO breaking deprecations, set "has_breaking_changes" to false, "detected_issues" to [], and "refactored_code" to "".
2. If breaking deprecations exist, specify the issues and provide the complete modernized refactored code.

Return a valid JSON object ONLY matching this schema:
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
  "refactored_code": "Full refactored code if breaking changes exist, otherwise empty string"
}}

Source Code:
{code}
"""

        # Direct REST request to Google Generative Language API (zero gRPC dependency)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.0
            }
        }

        headers = {
            "Content-Type": "application/json"
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            raw_text = parts[0].get("text", "")
                            return self.clean_json_response(raw_text)
                    return {"has_breaking_changes": False, "detected_issues": [], "refactored_code": ""}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            raise ValueError(f"Gemini API HTTP Error {e.code}: {err_body}")
        except Exception as e:
            raise ValueError(f"Gemini API connection error: {e}")
