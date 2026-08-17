"""
Google Gemini Provider for ApiPatch
Uses the Google Generative Language REST API (zero gRPC dependency).
"""

import os
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Any, List, Optional
from apipatch.providers.base import BaseProvider


class GeminiProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(
            api_key=api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
            model=model or "gemini-2.5-flash"
        )

    def audit_code(
        self, file_name: str, code: str, detected_libraries: List[str]
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError(
                "No Gemini API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY "
                "environment variable, or pass --api-key via CLI."
            )

        prompt = self.build_prompt(file_name, code, detected_libraries)

        model_name = self.model[7:] if self.model.startswith("models/") else self.model
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent?key={self.api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.0,
                "thinkingConfig": {
                    "thinkingBudget": 0
                }
            }
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return self.clean_json_response(parts[0].get("text", ""))
                return {"has_breaking_changes": False, "detected_issues": [], "refactored_code": ""}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            raise ValueError(f"Gemini API HTTP {e.code}: {err_body}")
        except Exception as e:
            raise ValueError(f"Gemini API connection error: {e}")
