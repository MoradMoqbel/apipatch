"""
Base LLM Provider Interface for ApiPatch
"""

import abc
import json
import re
from typing import Dict, Any, List, Optional


# Universal system prompt shared across all provider implementations
UNIVERSAL_AUDIT_PROMPT = """\
You are ApiPatch, an autonomous expert static-code auditor and API migration agent.

Your mission:
  Detect ANY deprecated, breaking, or outdated third-party API calls in the provided
  source file and produce a complete, fully-functional modernized replacement.

Supported languages: Python, JavaScript, TypeScript, JSX, TSX, and any other language.

Known third-party packages detected in this project: [{libraries_hint}]

Audit scope — look for ALL of the following:
  • Renamed or removed functions/methods/classes (e.g. openai.ChatCompletion.create → client.chat.completions.create)
  • Changed constructor signatures (e.g. new SDK(key) → new SDK({{ apiKey: key }}))
  • Deprecated import paths (e.g. from langchain.chains import LLMChain → LCEL)
  • Old configuration patterns (e.g. Pydantic class Config → model_config = ConfigDict(...))
  • Auth API changes (e.g. supabase.auth.signIn → supabase.auth.signInWithPassword)
  • Lifecycle/hook renames (e.g. FastAPI on_event → lifespan, React componentDidMount → useEffect)
  • Any other breaking change in ANY library version migration

Rules:
  1. Preserve 100%% of the original business logic, variable names, and function signatures.
  2. Preserve all imports that are still needed; update or add imports as required.
  3. If NO breaking changes exist, return has_breaking_changes=false and refactored_code="".
  4. Never truncate the refactored code — return the COMPLETE modernized file.
  5. Respond ONLY with a valid JSON object matching the exact schema below.
     Do NOT include any preamble, explanation, markdown fences, or commentary.

Response schema:
{{
  "has_breaking_changes": true | false,
  "detected_issues": [
    {{
      "library": "<package name>",
      "deprecated_symbol": "<exact deprecated code pattern>",
      "replacement_symbol": "<modern replacement>",
      "description": "<one-sentence explanation>",
      "line_hint": "<approximate code line or line number>"
    }}
  ],
  "refactored_code": "<complete modernized source file, or empty string if no changes>"
}}
"""


class BaseProvider(abc.ABC):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model

    def build_prompt(self, file_name: str, code: str, detected_libraries: List[str]) -> str:
        """Builds the universal audit prompt for any LLM provider."""
        libraries_hint = (
            ", ".join(detected_libraries)
            if detected_libraries
            else "any third-party library present in the code"
        )
        prompt = UNIVERSAL_AUDIT_PROMPT.format(libraries_hint=libraries_hint)
        prompt += f"\n\nFile: {file_name}\n\nSource Code:\n```\n{code}\n```\n"
        return prompt

    @abc.abstractmethod
    def audit_code(
        self, file_name: str, code: str, detected_libraries: List[str]
    ) -> Dict[str, Any]:
        """
        Analyzes source code for deprecated API calls across any library.
        Returns structured JSON:
        {
          "has_breaking_changes": bool,
          "detected_issues": [...],
          "refactored_code": str
        }
        """
        pass

    def clean_json_response(self, raw_text: str) -> Dict[str, Any]:
        """Robustly cleans and extracts JSON payload from LLM responses."""
        text = raw_text.strip()
        # Strip markdown fences
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        # Attempt 1: direct parse
        try:
            return json.loads(text, strict=False)
        except Exception:
            pass

        # Attempt 2: repair unescaped backslashes common in JS/regex code
        repaired = re.sub(r'\\([^"\\/bfnrtuU0-9])', r'\\\\\\1', text)
        try:
            return json.loads(repaired, strict=False)
        except Exception:
            pass

        # Attempt 3: extract outermost JSON object block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            block = match.group(0)
            try:
                return json.loads(block, strict=False)
            except Exception:
                block_repaired = re.sub(r'\\([^"\\/bfnrtuU0-9])', r'\\\\\\1', block)
                try:
                    return json.loads(block_repaired, strict=False)
                except Exception:
                    pass

        raise ValueError(
            f"Could not parse valid JSON from LLM response: {raw_text[:300]}..."
        )
