"""
Unit tests for ApiPatch GitHub App Webhook daemon server
"""

import hmac
import hashlib
import json
import unittest
import urllib.request
import urllib.parse
from unittest.mock import patch, MagicMock
from apipatch.webhook import verify_signature, ApiPatchWebhookHandler, ThreadedHTTPServer


class TestWebhook(unittest.TestCase):

    def test_verify_signature_without_secret(self):
        # When no secret is configured, should always pass
        self.assertTrue(verify_signature(b"payload", None, None))
        self.assertTrue(verify_signature(b"payload", "sha256=123", None))

    def test_verify_signature_with_secret_valid(self):
        secret = "super_secret_key"
        payload = b'{"action": "ping"}'
        sig = "sha256=" + hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        self.assertTrue(verify_signature(payload, sig, secret))

    def test_verify_signature_with_secret_invalid(self):
        secret = "super_secret_key"
        payload = b'{"action": "ping"}'
        sig = "sha256=invalid_hash_value"
        self.assertFalse(verify_signature(payload, sig, secret))
        self.assertFalse(verify_signature(payload, None, secret))

    @patch("apipatch.webhook.GitHubPRHunter")
    def test_webhook_server_http_lifecycle(self, mock_hunter_cls):
        mock_hunter = MagicMock()
        mock_hunter.github_token = "valid_token"
        mock_hunter.get_authenticated_user.return_value = "morad"
        mock_hunter_cls.return_value = mock_hunter

        # Spin up test server on localhost ephemeral port
        server = ThreadedHTTPServer(("127.0.0.1", 0), ApiPatchWebhookHandler)
        server.hunter = mock_hunter
        server.webhook_secret = "test_secret"
        port = server.server_address[1]

        import threading
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()

        base_url = f"http://127.0.0.1:{port}"

        try:
            # 1. Health check GET /health
            req = urllib.request.Request(f"{base_url}/health")
            with urllib.request.urlopen(req, timeout=5) as res:
                self.assertEqual(res.status, 200)
                body = json.loads(res.read().decode())
                self.assertEqual(body["status"], "healthy")
                self.assertTrue(body["authenticated"])

            # 2. Ping Event POST /webhook
            ping_body = json.dumps({"zen": "Keep it simple."}).encode("utf-8")
            sig = "sha256=" + hmac.new(b"test_secret", ping_body, hashlib.sha256).hexdigest()
            req = urllib.request.Request(
                f"{base_url}/webhook",
                data=ping_body,
                headers={
                    "Content-Type": "application/json",
                    "X-GitHub-Event": "ping",
                    "X-Hub-Signature-256": sig
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as res:
                self.assertEqual(res.status, 200)
                body = json.loads(res.read().decode())
                self.assertEqual(body["status"], "pong")

            # 3. Push Event POST /webhook (Non-apipatch branch)
            push_body = json.dumps({
                "ref": "refs/heads/main",
                "repository": {"full_name": "owner/repo"}
            }).encode("utf-8")
            sig_push = "sha256=" + hmac.new(b"test_secret", push_body, hashlib.sha256).hexdigest()
            req = urllib.request.Request(
                f"{base_url}/webhook",
                data=push_body,
                headers={
                    "Content-Type": "application/json",
                    "X-GitHub-Event": "push",
                    "X-Hub-Signature-256": sig_push
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as res:
                self.assertEqual(res.status, 202)
                body = json.loads(res.read().decode())
                self.assertEqual(body["status"], "accepted")
                self.assertEqual(body["repo"], "owner/repo")

            # 4. Push Event from apipatch branch (should be ignored)
            self_push = json.dumps({
                "ref": "refs/heads/apipatch/migrate-123",
                "repository": {"full_name": "owner/repo"}
            }).encode("utf-8")
            sig_self = "sha256=" + hmac.new(b"test_secret", self_push, hashlib.sha256).hexdigest()
            req = urllib.request.Request(
                f"{base_url}/webhook",
                data=self_push,
                headers={
                    "Content-Type": "application/json",
                    "X-GitHub-Event": "push",
                    "X-Hub-Signature-256": sig_self
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as res:
                self.assertEqual(res.status, 200)
                body = json.loads(res.read().decode())
                self.assertEqual(body["status"], "ignored")

        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
