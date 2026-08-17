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
        """
        Robustly extracts the structured JSON payload from LLM responses.
        Handles the common case where refactored_code contains JS/TS source with
        raw backslash sequences (\\n, \\t, \\uXXXX, regex literals, etc.)
        that break standard JSON parsers.
        """
        text = raw_text.strip()

        # Strip markdown fences
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        # ── Attempt 1: direct parse (works for Python files / simple responses) ──
        try:
            return json.loads(text, strict=False)
        except Exception:
            pass

        # ── Attempt 2: repair unescaped backslashes ──────────────────────────────
        # e.g. \d \w \s \/ \u without 4 hex digits → \\d \\w etc.
        repaired = re.sub(r'\\([^"\\/bfnrtu]|u(?![0-9a-fA-F]{4}))', r'\\\\\1', text)
        try:
            return json.loads(repaired, strict=False)
        except Exception:
            pass

        # ── Attempt 3: surgical field extraction ─────────────────────────────────
        # Extract has_breaking_changes and detected_issues via regex,
        # then extract refactored_code as the raw string between its delimiters.
        try:
            result = self._extract_fields_surgically(text)
            if result is not None:
                return result
        except Exception:
            pass

        # ── Attempt 4: extract outermost JSON block and retry ────────────────────
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            block = match.group(0)
            for attempt in (block, re.sub(r'\\([^"\\/bfnrtu]|u(?![0-9a-fA-F]{4}))', r'\\\\\1', block)):
                try:
                    return json.loads(attempt, strict=False)
                except Exception:
                    pass

        raise ValueError(
            f"Could not parse valid JSON from LLM response: {raw_text[:400]}..."
        )

    def _extract_fields_surgically(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Last-resort parser: extracts the three known fields individually.
        Handles the case where refactored_code contains raw JS/TS source with
        backslashes that make the entire JSON unparseable.
        """
        # has_breaking_changes
        hbc_match = re.search(r'"has_breaking_changes"\s*:\s*(true|false)', text, re.IGNORECASE)
        if not hbc_match:
            return None
        has_breaking = hbc_match.group(1).lower() == "true"

        # detected_issues — extract the array as a substring and parse it
        issues: list = []
        issues_match = re.search(r'"detected_issues"\s*:\s*(\[.*?\])', text, re.DOTALL)
        if issues_match:
            try:
                issues = json.loads(issues_match.group(1), strict=False)
            except Exception:
                # Try to count issue objects at minimum
                issues = []

        # refactored_code — find the value after the key, handle escaped/raw content
        # Strategy: find the key, then capture everything until the last closing "
        # that is followed by optional whitespace and } or ,
        code = ""
        code_key_match = re.search(r'"refactored_code"\s*:\s*"', text)
        if code_key_match:
            start = code_key_match.end()
            # Walk forward to find the closing quote that ends the JSON string
            # (must not be preceded by odd number of backslashes)
            i = start
            while i < len(text):
                ch = text[i]
                if ch == '\\':
                    i += 2  # skip escape sequence
                    continue
                if ch == '"':
                    code = text[start:i]
                    break
                i += 1

        return {
            "has_breaking_changes": has_breaking,
            "detected_issues": issues,
            "refactored_code": code
        }

