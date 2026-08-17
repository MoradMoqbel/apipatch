"""
Unit tests for CLI
"""

import unittest
import subprocess
import sys
import os
import tempfile


class TestCLI(unittest.TestCase):
    def test_cli_version(self):
        res = subprocess.run(
            [sys.executable, "-m", "apipatch.cli", "--version"],
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("apipatch", res.stdout.lower() + res.stderr.lower())

    def test_cli_scan_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write("import openai\ndef ask():\n    return openai.ChatCompletion.create(model='gpt-3.5-turbo')\n")
            temp_path = f.name

        try:
            res = subprocess.run(
                [sys.executable, "-m", "apipatch.cli", "scan", temp_path],
                capture_output=True,
                text=True
            )
            self.assertEqual(res.returncode, 0)
            self.assertIn("DEPRECATION", res.stdout)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
