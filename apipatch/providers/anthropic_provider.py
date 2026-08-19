"""
Anthropic Claude Provider for ApiPatch
"""

import os
from typing import Dict, Any, List, Optional
from apipatch.providers.base import BaseProvider


class AnthropicProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY"),
            model=model or "claude-3-5-sonnet-20241022"
        )

    def _call_anthropic(self, prompt: str, system_msg: str) -> Dict[str, Any]:
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)

        message = client.messages.create(
            model=self.model,
            max_tokens=32768,
            temperature=0.0,
            system=system_msg,
            messages=[{"role": "user", "content": prompt}]
        )

        raw_text = message.content[0].text
        return self.clean_json_response(raw_text)

    def audit_code(
        self,
        file_name: str,
        code: str,
        detected_libraries: List[str],
        project_context: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError(
                "No Anthropic API key found. Set ANTHROPIC_API_KEY environment variable "
                "or pass --api-key via CLI."
            )
        prompt = self.build_prompt(file_name, code, detected_libraries, project_context=project_context)
        return self._call_anthropic(
            prompt=prompt,
            system_msg="You are ApiPatch, an autonomous code auditor. Respond ONLY with a valid JSON object — no markdown, no preamble, no explanation."
        )

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
                "No Anthropic API key found. Set ANTHROPIC_API_KEY environment variable "
                "or pass --api-key via CLI."
            )
        prompt = self.build_healing_prompt(
            file_name=file_name,
            original_code=original_code,
            broken_code=broken_code,
            validation_error=validation_error,
            detected_libraries=detected_libraries,
            project_context=project_context
        )
        return self._call_anthropic(
            prompt=prompt,
            system_msg="You are ApiPatch, an autonomous code repair agent. Respond ONLY with a valid JSON object — no markdown, no preamble, no explanation."
        )
