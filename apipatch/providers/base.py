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
{project_context_section}
Audit scope — look for ALL of the following:
  • Google GenAI / Gemini migrations (e.g. google.generativeai / raw endpoints → google.genai Client, gemini-3.1-flash-image / gemini-3-pro-image with response_modalities=['IMAGE'])
  • Renamed or removed functions/methods/classes (e.g. openai.ChatCompletion.create → client.chat.completions.create)
  • Changed constructor signatures (e.g. new SDK(key) → new SDK({{ apiKey: key }}))
  • Deprecated import paths (e.g. from langchain.chains import LLMChain → LCEL, from langchain.chat_models import ChatOpenAI → langchain_openai)
  • Old configuration patterns (e.g. Pydantic class Config → model_config = ConfigDict(...))
  • Auth API changes (e.g. supabase.auth.signIn → supabase.auth.signInWithPassword)
  • Lifecycle/hook renames (e.g. FastAPI on_event → lifespan, React componentDidMount → useEffect)
  • Any other breaking change in ANY library version migration

Rules (STRICT ZERO-TOLERANCE FOR HALLUCINATIONS & OVER-REFACTORING):
  1. HIGH PRECISION & ZERO FALSE POSITIVES: If you are not 100%% certain that an API method or import has been officially deprecated or removed in a published library release, DO NOT TOUCH IT. Return has_breaking_changes=false and refactored_code="".
  2. NEVER SWAP FRAMEWORKS: Never replace a project's native framework components with a competing framework (e.g. In Haystack, LlamaIndex, LiteLLM, or custom AI projects, NEVER replace their native generators/components with LangChain or other third-party libraries).
  3. NEVER RENAME INTERNAL VARIABLES/CONSTANTS: Never modify internal property names, configuration keys, or constants (e.g. leave GROQ_BASE_URL, ollama_base_url, model identifiers, and config attributes exactly as written).
  4. NO COSMETIC OR STYLE CHANGES: Do NOT reformat strings, do NOT adjust whitespace/docstrings, do NOT change `dict[...]` to `dict.get(...)`, and do NOT rewrite working file loaders (like toml.load).
  5. NEVER REFACTOR STANDARD LIBRARY: posixpath, ntpath, os.path, urllib, sys, json, re, math, and tempfile are Python standard library modules. NEVER replace them with pathlib or third-party packages.
  6. PRESERVE 100%% OF ORIGINAL BUSINESS LOGIC: Function signatures, class structures, variable names, and string literals must remain completely intact.
  7. NEVER DOWNGRADE MODELS OR SDK VERSIONS: If a model name (e.g. `gemini-3-flash`, `gemini-3-pro-image`, `gemini-2.5`, `gpt-4o`, `claude-3-7`) or API pattern is newer or unfamiliar, DO NOT TOUCH IT. NEVER downgrade a modern/preview model to an older legacy model (e.g. NEVER change Gemini 3.x/2.x to Gemini 1.5). Treat newer models and APIs as valid and modern.
  8. DO NOT CONFUSE PYPI PACKAGE NAMES WITH PYTHON IMPORT NAMES: Many packages on PyPI use different names than their Python import statements. For example, `python-dotenv` MUST be imported as `dotenv` (NEVER `import python_dotenv`), `pillow` is imported as `PIL`, `pyyaml` is imported as `yaml`, and `beautifulsoup4` is imported as `bs4`. Keep the valid import name.
  9. NEVER REPLACE CODE WITH COMMENTS: Never comment out working code or replace implementation with `# Example for ...` placeholder comments.
  10. If NO genuine third-party breaking changes exist, ALWAYS return has_breaking_changes=false and refactored_code="".
  11. Respond ONLY with a valid JSON object matching the exact schema below.
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

SELF_HEALING_PROMPT = """\
You are ApiPatch, an autonomous expert static-code auditor and API migration agent.

A previously generated code refactor for file '{file_name}' FAILED automated validation.

Validation / Test Error:
{validation_error}

Original source code:
```
{original_code}
```

Previously attempted refactored code (contained the error above):
```
{broken_code}
```
{project_context_section}
Your mission:
  1. Analyze the exact validation/test error (e.g. SyntaxError, dropped functions/classes, unclosed braces/brackets, or broken test assertion).
  2. Fix the error completely while keeping the modernized third-party library calls intact.
  3. Preserve 100%% of the original business logic, classes, and function signatures.
  4. Never truncate the refactored code — return the COMPLETE corrected modernized file.
  5. Respond ONLY with a valid JSON object matching the schema below.
     Do NOT include any preamble, markdown fences, or commentary.

Response schema:
{{
  "has_breaking_changes": true,
  "detected_issues": [
    {{
      "library": "<package name>",
      "deprecated_symbol": "<exact deprecated code pattern>",
      "replacement_symbol": "<modern replacement>",
      "description": "<one-sentence explanation>",
      "line_hint": "<approximate code line or line number>"
    }}
  ],
  "refactored_code": "<complete corrected modernized source file>"
}}
"""


from apipatch.knowledge import get_relevant_knowledge


class BaseProvider(abc.ABC):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model

    def build_prompt(
        self,
        file_name: str,
        code: str,
        detected_libraries: List[str],
        project_context: Optional[str] = None
    ) -> str:
        """Builds the universal audit prompt for any LLM provider."""
        libraries_hint = (
            ", ".join(detected_libraries)
            if detected_libraries
            else "any third-party library present in the code"
        )
        ctx_section = f"\nProject Architecture & Context:\n{project_context}\n" if project_context else ""
        prompt = UNIVERSAL_AUDIT_PROMPT.format(
            libraries_hint=libraries_hint,
            project_context_section=ctx_section
        )
        knowledge_section = get_relevant_knowledge(detected_libraries, code)
        if knowledge_section:
            prompt += f"\n{knowledge_section}\n"

        prompt += f"\n\nFile: {file_name}\n\nSource Code:\n```\n{code}\n```\n"
        return prompt

    def build_healing_prompt(
        self,
        file_name: str,
        original_code: str,
        broken_code: str,
        validation_error: str,
        detected_libraries: Optional[List[str]] = None,
        project_context: Optional[str] = None
    ) -> str:
        """Builds the self-healing correction prompt."""
        ctx_section = f"\nProject Architecture & Context:\n{project_context}\n" if project_context else ""
        prompt = SELF_HEALING_PROMPT.format(
            file_name=file_name,
            validation_error=validation_error,
            original_code=original_code,
            broken_code=broken_code,
            project_context_section=ctx_section
        )
        knowledge_section = get_relevant_knowledge(detected_libraries, original_code)
        if knowledge_section:
            prompt += f"\n{knowledge_section}\n"

        return prompt

    @abc.abstractmethod
    def audit_code(
        self,
        file_name: str,
        code: str,
        detected_libraries: List[str],
        project_context: Optional[str] = None
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

    @abc.abstractmethod
    def heal_code(
        self,
        file_name: str,
        original_code: str,
        broken_code: str,
        validation_error: str,
        detected_libraries: Optional[List[str]] = None,
        project_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Requests the LLM to fix syntax, structural, or test errors in a previously generated refactor.
        """
        pass

    def clean_json_response(self, raw_text: str) -> Dict[str, Any]:
        """
        Robustly extracts the structured JSON payload from LLM responses.
        Handles markdown fences, unescaped regexes/backslashes, and surgical extraction.
        """
        text = raw_text.strip()

        # Strip markdown fences
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        # ── Attempt 1: direct parse ──
        try:
            return json.loads(text, strict=False)
        except Exception:
            pass

        # ── Attempt 2: repair unescaped backslashes ──────────────────────────────
        repaired = re.sub(r'\\([^"\\/bfnrtu]|u(?![0-9a-fA-F]{4}))', r'\\\\\1', text)
        try:
            return json.loads(repaired, strict=False)
        except Exception:
            pass

        # ── Attempt 3: surgical field extraction ─────────────────────────────────
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
        """Last-resort parser: extracts the three known fields individually."""
        hbc_match = re.search(r'"has_breaking_changes"\s*:\s*(true|false)', text, re.IGNORECASE)
        if not hbc_match:
            return None
        has_breaking = hbc_match.group(1).lower() == "true"

        issues: list = []
        issues_match = re.search(r'"detected_issues"\s*:\s*(\[.*?\])', text, re.DOTALL)
        if issues_match:
            try:
                issues = json.loads(issues_match.group(1), strict=False)
            except Exception:
                issues = []

        code = ""
        code_key_match = re.search(r'"refactored_code"\s*:\s*"', text)
        if code_key_match:
            start = code_key_match.end()
            i = start
            while i < len(text):
                ch = text[i]
                if ch == '\\':
                    i += 2
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
