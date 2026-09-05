import unittest
from unittest.mock import patch, MagicMock
import io
import json
from apipatch.doc_hunter import DocHunter, _PACKAGE_METADATA_CACHE
from apipatch.knowledge import get_relevant_knowledge


class TestDocHunter(unittest.TestCase):
    def setUp(self):
        _PACKAGE_METADATA_CACHE.clear()

    @patch("urllib.request.urlopen")
    def test_fetch_pypi_metadata_success(self, mock_urlopen):
        mock_data = {
            "info": {
                "name": "agno",
                "version": "2.9.0",
                "summary": "Multi-agent framework for autonomous AI",
                "home_page": "https://agno.com",
                "project_urls": {
                    "Documentation": "https://docs.agno.com",
                    "Repository": "https://github.com/agno-agi/agno"
                }
            }
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_data).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        res = DocHunter.fetch_pypi_metadata("agno")
        self.assertIsNotNone(res)
        self.assertEqual(res["name"], "agno")
        self.assertEqual(res["version"], "2.9.0")
        self.assertEqual(res["documentation_url"], "https://docs.agno.com")
        self.assertEqual(res["repository_url"], "https://github.com/agno-agi/agno")
        self.assertTrue(res["is_active"])

    @patch("urllib.request.urlopen")
    def test_fetch_npm_metadata_success(self, mock_urlopen):
        mock_data = {
            "name": "axios",
            "dist-tags": {"latest": "1.7.9"},
            "description": "Promise based HTTP client",
            "homepage": "https://axios-http.com",
            "repository": {"url": "https://github.com/axios/axios"}
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_data).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        res = DocHunter.fetch_npm_metadata("axios")
        self.assertIsNotNone(res)
        self.assertEqual(res["name"], "axios")
        self.assertEqual(res["version"], "1.7.9")
        self.assertEqual(res["documentation_url"], "https://axios-http.com")

    @patch.object(DocHunter, "get_package_grounding")
    def test_build_grounded_context(self, mock_get_grounding):
        mock_get_grounding.return_value = {
            "name": "agno",
            "version": "2.9.0",
            "summary": "Multi-agent framework",
            "documentation_url": "https://docs.agno.com",
            "repository_url": "https://github.com/agno-agi/agno"
        }

        context = DocHunter.build_grounded_context(["agno"])
        self.assertIn("Authoritative Live Package Grounding", context)
        self.assertIn("Package 'agno' (Latest Official Release: v2.9.0)", context)
        self.assertIn("https://docs.agno.com", context)

    @patch("urllib.request.urlopen")
    def test_fetch_llms_txt_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.headers = {"Content-Type": "text/markdown"}
        mock_resp.read.return_value = b"# Cohere API Documentation\nOverview of Embed v4 and Chat v2 APIs"
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        res = DocHunter.fetch_llms_txt("https://docs.cohere.com/reference")
        self.assertIn("Cohere API Documentation", res)

    @patch("urllib.request.urlopen")
    def test_fetch_github_changelog_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"# Changelog\n\n## v5.0.0 (2025-01-01)\n- Breaking: Introduce ClientV2 for modern chat/embed"
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        res = DocHunter.fetch_github_changelog("https://github.com/cohere-ai/cohere-python")
        self.assertIn("v5.0.0", res)
        self.assertIn("ClientV2", res)


if __name__ == "__main__":
    unittest.main()
