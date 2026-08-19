"""
Unit tests for GitHubPRHunter live PR automation and REST API operations
"""

import unittest
from unittest.mock import patch, MagicMock
from apipatch.proactive_hunter import GitHubPRHunter, _build_raw_url


class TestPRSubmitter(unittest.TestCase):
    def test_build_raw_url_with_html_url(self):
        item = {
            "html_url": "https://github.com/openai/openai-python/blob/main/src/openai/client.py"
        }
        url = _build_raw_url(item)
        self.assertEqual(url, "https://raw.githubusercontent.com/openai/openai-python/main/src/openai/client.py")

    def test_build_raw_url_with_raw_url(self):
        item = {
            "raw_url": "https://raw.githubusercontent.com/custom/repo/v1/main.py"
        }
        self.assertEqual(_build_raw_url(item), "https://raw.githubusercontent.com/custom/repo/v1/main.py")

    def test_generate_pr_payload(self):
        hunter = GitHubPRHunter(github_token="fake_token")
        audit_result = {
            "issues": [{
                "library": "openai",
                "deprecated_symbol": "openai.ChatCompletion.create()",
                "replacement_symbol": "client.chat.completions.create()",
                "description": "Upgrade to OpenAI Python v1 SDK"
            }]
        }
        payload = hunter.generate_pr_payload("owner/repo", "services/ai.py", audit_result)
        self.assertIn("[ApiPatch] Migrate deprecated openai API calls in ai.py", payload["title"])
        self.assertIn("Automated API Migration by [ApiPatch]", payload["body"])
        self.assertIn("openai.ChatCompletion.create()", payload["body"])

    @patch.object(GitHubPRHunter, "_request")
    def test_get_authenticated_user(self, mock_request):
        mock_request.return_value = {"login": "apipatch-bot", "id": 12345}
        hunter = GitHubPRHunter(github_token="valid_token")
        user = hunter.get_authenticated_user()
        self.assertEqual(user, "apipatch-bot")
        mock_request.assert_called_with("/user")

    @patch.object(GitHubPRHunter, "_request")
    def test_get_default_branch(self, mock_request):
        mock_request.return_value = {"default_branch": "develop"}
        hunter = GitHubPRHunter(github_token="valid_token")
        branch = hunter.get_default_branch("test-org/repo")
        self.assertEqual(branch, "develop")

    @patch.object(GitHubPRHunter, "_request")
    def test_create_branch(self, mock_request):
        mock_request.return_value = {"ref": "refs/heads/apipatch/migrate-123"}
        hunter = GitHubPRHunter(github_token="valid_token")
        success = hunter.create_branch("owner/repo", "apipatch/migrate-123", "abcdef123456")
        self.assertTrue(success)

    @patch.object(GitHubPRHunter, "_request")
    def test_submit_pull_request(self, mock_request):
        mock_request.return_value = {
            "html_url": "https://github.com/owner/repo/pull/42",
            "number": 42
        }
        hunter = GitHubPRHunter(github_token="valid_token")
        res = hunter.submit_pull_request(
            base_repo="owner/repo",
            head_branch="myuser:apipatch/migrate-1",
            base_branch="main",
            title="[ApiPatch] Migrate openai",
            body="PR Description"
        )
        self.assertIsNotNone(res)
        self.assertEqual(res["html_url"], "https://github.com/owner/repo/pull/42")


if __name__ == "__main__":
    unittest.main()
