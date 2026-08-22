"""
Unit tests for AWS Bedrock Provider in ApiPatch
Tests BedrockProvider initialization, credential resolution, mock converse API calls,
and ProviderFactory integration.
"""

import os
import json
import unittest
from unittest.mock import MagicMock, patch
from apipatch.providers.bedrock_provider import BedrockProvider, MODEL_ALIASES
from apipatch.providers.factory import ProviderFactory


class TestBedrockProvider(unittest.TestCase):
    def setUp(self):
        self.env_patcher = patch.dict(os.environ, {
            "AWS_ACCESS_KEY_ID": "test_access_key",
            "AWS_SECRET_ACCESS_KEY": "test_secret_key",
            "AWS_REGION": "us-east-2",
            "AWS_DEFAULT_REGION": "us-east-2",
        }, clear=False)
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    def test_initialization_defaults(self):
        provider = BedrockProvider()
        self.assertEqual(provider.aws_access_key_id, "test_access_key")
        self.assertEqual(provider.aws_secret_access_key, "test_secret_key")
        self.assertEqual(provider.region_name, "us-east-2")
        self.assertEqual(provider.model, "anthropic.claude-3-5-sonnet-20241022-v2:0")

    def test_model_alias_resolution(self):
        provider = BedrockProvider(model="claude-3-5-sonnet")
        self.assertEqual(provider.model, "anthropic.claude-3-5-sonnet-20241022-v2:0")

        provider_nova = BedrockProvider(model="nova-pro")
        self.assertEqual(provider_nova.model, "amazon.nova-pro-v1:0")

    def test_api_key_split_support(self):
        with patch.dict(os.environ, {}, clear=True):
            provider = BedrockProvider(api_key="MY_KEY_ID:MY_SECRET_KEY")
            self.assertEqual(provider.aws_access_key_id, "MY_KEY_ID")
            self.assertEqual(provider.aws_secret_access_key, "MY_SECRET_KEY")

    @patch("boto3.client")
    def test_audit_code_successful_mock(self, mock_boto_client):
        mock_client_instance = MagicMock()
        mock_boto_client.return_value = mock_client_instance

        expected_response = {
            "has_breaking_changes": True,
            "detected_issues": [
                {
                    "library": "openai",
                    "deprecated_symbol": "openai.ChatCompletion.create",
                    "replacement_symbol": "client.chat.completions.create",
                    "description": "Migrated to OpenAI SDK v1.x+",
                    "line_hint": "line 12"
                }
            ],
            "refactored_code": "import openai\nclient = openai.OpenAI()\nclient.chat.completions.create()\n"
        }

        mock_client_instance.converse.return_value = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": json.dumps(expected_response)}]
                }
            }
        }

        provider = BedrockProvider()
        result = provider.audit_code(
            file_name="test.py",
            code="import openai\nopenai.ChatCompletion.create()",
            detected_libraries=["openai"]
        )

        self.assertTrue(result["has_breaking_changes"])
        self.assertEqual(len(result["detected_issues"]), 1)
        self.assertEqual(result["detected_issues"][0]["library"], "openai")
        self.assertIn("client.chat.completions.create", result["refactored_code"])

    @patch("boto3.client")
    def test_heal_code_successful_mock(self, mock_boto_client):
        mock_client_instance = MagicMock()
        mock_boto_client.return_value = mock_client_instance

        expected_response = {
            "has_breaking_changes": True,
            "detected_issues": [],
            "refactored_code": "def healed(): pass"
        }

        mock_client_instance.converse.return_value = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": json.dumps(expected_response)}]
                }
            }
        }

        provider = BedrockProvider()
        result = provider.heal_code(
            file_name="broken.py",
            original_code="def broken(): pass",
            broken_code="def broken( pass",
            validation_error="SyntaxError: invalid syntax"
        )

        self.assertEqual(result["refactored_code"], "def healed(): pass")

    def test_provider_factory_explicit(self):
        provider = ProviderFactory.get_provider("bedrock")
        self.assertIsInstance(provider, BedrockProvider)
        self.assertEqual(provider.region_name, "us-east-2")

    @patch("apipatch.providers.factory._load_env_file")
    def test_provider_factory_auto_discovery(self, mock_load_env):
        with patch.dict(os.environ, {
            "AWS_ACCESS_KEY_ID": "AKIA_FAKE",
            "AWS_SECRET_ACCESS_KEY": "SECRET_FAKE",
            "AWS_REGION": "us-east-2"
        }, clear=True):
            provider = ProviderFactory.get_provider()
            self.assertIsInstance(provider, BedrockProvider)


if __name__ == "__main__":
    unittest.main()
