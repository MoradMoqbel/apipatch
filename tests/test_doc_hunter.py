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

    @patch.object(DocHunter, "build_grounded_context")
    def test_get_relevant_knowledge_incorporates_grounding(self, mock_grounding):
        mock_grounding.return_value = "\n[Authoritative Live Package Grounding]\n• Package 'agno' v2.9.0\n"
        
        guidance = get_relevant_knowledge(detected_libraries=["agno"])
        self.assertIn("Authoritative Live Package Grounding", guidance)
        self.assertIn("agno", guidance)


if __name__ == "__main__":
    unittest.main()
