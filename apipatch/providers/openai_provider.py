"""
OpenAI Provider for ApiPatch
"""

import os
from typing import Dict, Any, List, Optional
from apipatch.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            model=model or "gpt-4o"
        )

    def _call_openai(self, prompt: str, system_msg: str) -> Dict[str, Any]:
        import openai
        client = openai.OpenAI(api_key=self.api_key)

        use_json_mode = any(m in self.model for m in ("gpt-4o", "gpt-4-turbo", "o3", "o4"))

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            response_format={"type": "json_object"} if use_json_mode else None
        )

        raw_text = response.choices[0].message.content
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
                "No OpenAI API key found. Set OPENAI_API_KEY environment variable "
                "or pass --api-key via CLI."
            )
        prompt = self.build_prompt(file_name, code, detected_libraries, project_context=project_context)
        return self._call_openai(
            prompt=prompt,
            system_msg="You are ApiPatch, an autonomous code auditor. Respond ONLY with a valid JSON object — no markdown, no preamble."
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
                "No OpenAI API key found. Set OPENAI_API_KEY environment variable "
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
        return self._call_openai(
            prompt=prompt,
            system_msg="You are ApiPatch, an autonomous code repair agent. Respond ONLY with a valid JSON object — no markdown, no preamble."
        )
