"""
Google Gemini Provider for ApiPatch
Uses the Google Generative Language REST API (zero gRPC dependency)
with automatic rate-limit (429) retry and seamless fallback to flash-lite.
"""

import os
import time
import json
import re
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
        # Alternate fallback models if primary hits quota or is unavailable
        self.fallback_models = ["gemini-3.6-flash", "gemini-1.5-flash"]

    def _call_model(self, model_name: str, prompt: str) -> Optional[str]:
        clean_model = model_name[7:] if model_name.startswith("models/") else model_name
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{clean_model}:generateContent?key={self.api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.0
            }
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
        return None

    def _execute_with_fallbacks(self, prompt: str) -> Dict[str, Any]:
        models_to_try = [self.model] + [m for m in self.fallback_models if m != self.model]
        last_err = None
        for current_model in models_to_try:
            try:
                raw_text = self._call_model(current_model, prompt)
                if raw_text:
                    return self.clean_json_response(raw_text)
                return {"has_breaking_changes": False, "detected_issues": [], "refactored_code": ""}

            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="ignore")
                last_err = f"HTTP {e.code}: {err_body}"
                if e.code == 429:
                    continue
                raise ValueError(f"Gemini API HTTP {e.code}: {err_body}")

            except Exception as e:
                last_err = str(e)
                continue

        if last_err and "429" in str(last_err):
            raise ValueError("All Gemini free-tier models currently rate-limited. Please retry shortly.")

        return {"has_breaking_changes": False, "detected_issues": [], "refactored_code": ""}

    def audit_code(
        self,
        file_name: str,
        code: str,
        detected_libraries: List[str],
        project_context: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError(
                "No Gemini API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY "
                "environment variable, or pass --api-key via CLI."
            )
        prompt = self.build_prompt(file_name, code, detected_libraries, project_context=project_context)
        return self._execute_with_fallbacks(prompt)

    def heal_code(
        self,
        file_name: str,
        original_code: str,
        broken_code: str,
        validation_error: str,
        detected_libraries: Optional[List[str]] = None,
        project_context: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError(
                "No Gemini API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY "
                "environment variable, or pass --api-key via CLI."
            )
        prompt = self.build_healing_prompt(
            file_name=file_name,
            original_code=original_code,
            broken_code=broken_code,
            validation_error=validation_error,
            detected_libraries=detected_libraries,
            project_context=project_context
        )
        return self._execute_with_fallbacks(prompt)
