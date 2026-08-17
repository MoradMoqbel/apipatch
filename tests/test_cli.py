"""
Unit tests for CLI
"""

import unittest
import subprocess
import sys


class TestCLI(unittest.TestCase):
    def test_cli_version(self):
        res = subprocess.run(
            [sys.executable, "-m", "apipatch.cli", "--version"],
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("apipatch", res.stdout.lower() + res.stderr.lower())

    def test_cli_scan_demo(self):
        res = subprocess.run(
            [sys.executable, "-m", "apipatch.cli", "scan", "demo/target_sample.py"],
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("DEPRECATION", res.stdout)


if __name__ == "__main__":
    unittest.main()
