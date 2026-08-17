"""
Base LLM Provider Interface for ApiPatch
"""

import abc
import json
import re
from typing import Dict, Any, List, Optional


class BaseProvider(abc.ABC):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model

    @abc.abstractmethod
    def audit_code(self, file_name: str, code: str, detected_libraries: List[str]) -> Dict[str, Any]:
        """
        Dynamically analyzes code for breaking changes and deprecated APIs across any library,
        returning structured JSON:
        {
          "has_breaking_changes": bool,
          "detected_issues": [
            {
              "library": str,
              "deprecated_symbol": str,
              "replacement_symbol": str,
              "description": str,
              "line_hint": str
            }
          ],
          "refactored_code": str
        }
        """
        pass

    def clean_json_response(self, raw_text: str) -> Dict[str, Any]:
        """Robustly cleans and extracts JSON payload from LLM responses, repairing common escape issues."""
        text = raw_text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        # Attempt 1: Direct parse with non-strict mode
        try:
            return json.loads(text, strict=False)
        except Exception:
            pass

        # Attempt 2: Repair unescaped invalid backslashes (common in JS regex/strings like \d, \w, \s, \/)
        repaired = re.sub(r'\\([^"\\/bfnrtuU0-9])', r'\\\\\1', text)
        try:
            return json.loads(repaired, strict=False)
        except Exception:
            pass

        # Attempt 3: Extract outermost JSON object block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            block = match.group(0)
            try:
                return json.loads(block, strict=False)
            except Exception:
                block_repaired = re.sub(r'\\([^"\\/bfnrtuU0-9])', r'\\\\\1', block)
                return json.loads(block_repaired, strict=False)

        raise ValueError(f"Could not parse valid JSON from LLM response: {raw_text[:200]}...")
