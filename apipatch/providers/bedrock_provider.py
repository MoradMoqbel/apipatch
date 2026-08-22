"""
AWS Bedrock Provider for ApiPatch
Supports Anthropic Claude, Amazon Nova, Meta Llama, and Mistral models on AWS Bedrock
via the universal Bedrock Runtime converse API.
"""

import os
from typing import Dict, Any, List, Optional
from apipatch.providers.base import BaseProvider


MODEL_ALIASES = {
    "claude-3-5-sonnet": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "claude-3-5-sonnet-v2": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "claude-3-5-sonnet-v1": "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "claude-3-5-haiku": "anthropic.claude-3-5-haiku-20241022-v1:0",
    "claude-3-sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
    "claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "claude-3-opus": "anthropic.claude-3-opus-20240229-v1:0",
    "nova-pro": "amazon.nova-pro-v1:0",
    "nova-lite": "amazon.nova-lite-v1:0",
    "nova-micro": "amazon.nova-micro-v1:0",
    "llama3-70b": "meta.llama3-70b-instruct-v1:0",
    "llama3-8b": "meta.llama3-8b-instruct-v1:0",
}


class BedrockProvider(BaseProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
        region_name: Optional[str] = None
    ):
        # Resolve credentials with support for standard and custom env names
        self.aws_access_key_id = (
            aws_access_key_id
            or os.getenv("AWS_ACCESS_KEY_ID")
            or os.getenv("AWS_ACCESS_KEY")
            or os.getenv("aws_access_key")
        )
        self.aws_secret_access_key = (
            aws_secret_access_key
            or os.getenv("AWS_SECRET_ACCESS_KEY")
            or os.getenv("AWS_SECRET_KEY")
            or os.getenv("AWS_SECRET_CLIENT")
            or os.getenv("aws_secret_client")
        )
        self.aws_session_token = (
            aws_session_token
            or os.getenv("AWS_SESSION_TOKEN")
            or os.getenv("aws_session_token")
        )
        self.region_name = (
            region_name
            or os.getenv("AWS_REGION")
            or os.getenv("AWS_DEFAULT_REGION")
            or os.getenv("aws_region")
            or os.getenv("aws_default_region")
            or "us-east-2"
        )

        # Support --api-key passed as "ACCESS_KEY:SECRET_KEY"
        if api_key and ":" in api_key and not self.aws_access_key_id:
            parts = api_key.split(":", 1)
            self.aws_access_key_id = parts[0].strip()
            self.aws_secret_access_key = parts[1].strip()

        # Resolve model name with alias mapping
        resolved_model = (
            model
            or os.getenv("BEDROCK_MODEL_ID")
            or os.getenv("AWS_BEDROCK_MODEL")
            or "anthropic.claude-3-5-sonnet-20241022-v2:0"
        )
        resolved_model = MODEL_ALIASES.get(resolved_model.lower(), resolved_model)

        super().__init__(
            api_key=self.aws_access_key_id,
            model=resolved_model
        )

    def _get_client(self):
        """Initializes and returns a boto3 bedrock-runtime client."""
        try:
            import boto3
            from botocore.config import Config
        except ImportError:
            raise ImportError(
                "AWS Bedrock provider requires 'boto3'. Install it via: pip install boto3"
            )

        boto_config = Config(
            retries={"max_attempts": 3, "mode": "standard"},
            connect_timeout=15,
            read_timeout=120
        )

        client_kwargs: Dict[str, Any] = {
            "service_name": "bedrock-runtime",
            "region_name": self.region_name,
            "config": boto_config
        }

        if self.aws_access_key_id and self.aws_secret_access_key:
            client_kwargs["aws_access_key_id"] = self.aws_access_key_id
            client_kwargs["aws_secret_access_key"] = self.aws_secret_access_key
            if self.aws_session_token:
                client_kwargs["aws_session_token"] = self.aws_session_token

        return boto3.client(**client_kwargs)

    def _call_bedrock(self, prompt: str, system_msg: str) -> Dict[str, Any]:
        if not self.aws_access_key_id or not self.aws_secret_access_key:
            raise ValueError(
                "AWS Bedrock credentials missing. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY "
                "in your .env file or environment variables, or pass --api-key ACCESS_KEY:SECRET_KEY."
            )

        client = self._get_client()

        messages = [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ]

        system_prompts = [{"text": system_msg}] if system_msg else []

        try:
            response = client.converse(
                modelId=self.model,
                messages=messages,
                system=system_prompts,
                inferenceConfig={
                    "temperature": 0.0,
                    "maxTokens": 4096
                }
            )

            output_message = response.get("output", {}).get("message", {})
            content_blocks = output_message.get("content", [])
            raw_text = "".join([block.get("text", "") for block in content_blocks if "text" in block])

            return self.clean_json_response(raw_text)

        except Exception as e:
            err_str = str(e)
            if "AccessDeniedException" in err_str or "UnrecognizedClientException" in err_str:
                raise PermissionError(
                    f"AWS Bedrock authentication/permission failed ({self.region_name}): {err_str}\n"
                    f"Ensure model access for '{self.model}' is enabled in AWS Bedrock Console under region {self.region_name}."
                ) from e
            elif "ResourceNotFoundException" in err_str:
                raise ValueError(
                    f"AWS Bedrock model '{self.model}' not found in region {self.region_name}. "
                    f"Check model ID or specify another with --model."
                ) from e
            raise

    def audit_code(
        self,
        file_name: str,
        code: str,
        detected_libraries: List[str],
        project_context: Optional[str] = None
    ) -> Dict[str, Any]:
        prompt = self.build_prompt(file_name, code, detected_libraries, project_context=project_context)
        return self._call_bedrock(
            prompt=prompt,
            system_msg="You are ApiPatch, an autonomous code auditor. Respond ONLY with a valid JSON object matching the requested schema — no markdown fences, no preamble, no explanation."
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
        prompt = self.build_healing_prompt(
            file_name=file_name,
            original_code=original_code,
            broken_code=broken_code,
            validation_error=validation_error,
            detected_libraries=detected_libraries,
            project_context=project_context
        )
        return self._call_bedrock(
            prompt=prompt,
            system_msg="You are ApiPatch, an autonomous code repair agent. Respond ONLY with a valid JSON object — no markdown fences, no preamble, no explanation."
        )
