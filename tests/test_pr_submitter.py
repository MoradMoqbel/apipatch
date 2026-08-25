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
    def test_generate_pr_markdown_with_custom_title_and_scope_prefix(self):
        from apipatch.github_client import GitHubClient
        audit_results = [{
            "file": "apps/beifong/models/schemas.py",
            "detected_issues": [{
                "library": "pydantic",
                "deprecated_symbol": "class Config",
                "replacement_symbol": "model_config = ConfigDict()"
            }]
        }]
        
        # Test default with scope prefix
        payload_scope = GitHubClient.generate_pr_markdown("owner/repo", audit_results, scope_prefix="[Beifong] ")
        self.assertEqual(payload_scope["title"], "[Beifong] [ApiPatch] Migrate deprecated pydantic API calls (1 file)")
        
        # Test custom title override
        payload_custom = GitHubClient.generate_pr_markdown("owner/repo", audit_results, custom_title="[Beifong] Modernize Pydantic v2")
        self.assertEqual(payload_custom["title"], "[Beifong] Modernize Pydantic v2")

    @patch.object(GitHubPRHunter, "get_authenticated_user")
    @patch.object(GitHubPRHunter, "get_default_branch")
    @patch.object(GitHubPRHunter, "get_branch_sha")
    def test_audit_and_pr_repository_filters_target_path(self, mock_sha, mock_branch, mock_user):
        mock_user.return_value = "test-user"
        mock_branch.return_value = "main"
        mock_sha.return_value = "abc12345"
        
        hunter = GitHubPRHunter(github_token="fake_token")
        hunter.client.get_repo_file_tree = MagicMock(return_value=[
            {"path": "apps/beifong/models/podcast.py", "type": "blob"},
            {"path": "apps/beifong/models/user.py", "type": "blob"},
            {"path": "apps/other_app/server.py", "type": "blob"},
            {"path": "readme.md", "type": "blob"}
        ])
        hunter.client.fetch_file_content = MagicMock(return_value="import os\n")
        
        # Run with target_path="beifong" in dry_run mode
        res = hunter.audit_and_pr_repository(
            repo_name="owner/repo",
            dry_run=True,
            target_path="beifong"
        )
        self.assertEqual(res["status"], "clean")


if __name__ == "__main__":
    unittest.main()
