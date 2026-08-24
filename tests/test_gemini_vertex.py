"""
Unit tests for GeminiProvider Google Cloud & Vertex AI support
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from apipatch.providers.gemini_provider import GeminiProvider
from apipatch.providers.factory import ProviderFactory


class TestGeminiVertexProvider(unittest.TestCase):
    def test_gemini_provider_with_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            provider = GeminiProvider(api_key="test_key_123")
            self.assertEqual(provider.api_key, "test_key_123")
            self.assertFalse(provider.is_vertex)

    @patch("google.genai.Client")
    def test_gemini_provider_vertex_ai_initialization(self, mock_genai_client):
        mock_instance = MagicMock()
        mock_genai_client.return_value = mock_instance

        with patch.dict(os.environ, {
            "VERTEX_PROJECT": "test-project-123",
            "VERTEX_LOCATION": "us-central1"
        }, clear=True):
            provider = GeminiProvider(project_id="test-project-123")
            self.assertTrue(provider.is_vertex)
            self.assertEqual(provider.project_id, "test-project-123")

    def test_factory_explicit_vertex_provider(self):
        provider = ProviderFactory.get_provider("vertex", api_key="dummy")
        self.assertIsInstance(provider, GeminiProvider)


if __name__ == "__main__":
    unittest.main()
