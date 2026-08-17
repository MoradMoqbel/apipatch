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
        """Cleans and extracts JSON payload from LLM responses."""
        text = raw_text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Fallback regex extraction if model enclosed text in conversational blocks
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise
