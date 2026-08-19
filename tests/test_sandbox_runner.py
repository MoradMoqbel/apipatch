"""
Unit tests for SandboxTestRunner
"""

import os
import unittest
import tempfile
import json
from apipatch.test_runner import SandboxTestRunner


class TestSandboxRunner(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.test_dir.cleanup()

    def test_detect_pytest_framework(self):
        # Create a test file
        test_file = os.path.join(self.test_dir.name, "test_sample.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("def test_ok():\n    assert 1 == 1\n")

        framework = SandboxTestRunner.detect_test_framework(self.test_dir.name)
        self.assertEqual(framework, "pytest")

    def test_detect_npm_framework(self):
        pkg_file = os.path.join(self.test_dir.name, "package.json")
        with open(pkg_file, "w", encoding="utf-8") as f:
            json.dump({"scripts": {"test": "jest"}}, f)

        framework = SandboxTestRunner.detect_test_framework(self.test_dir.name)
        self.assertEqual(framework, "npm")

    def test_detect_no_framework(self):
        framework = SandboxTestRunner.detect_test_framework(self.test_dir.name)
        self.assertIsNone(framework)

    def test_run_passing_python_test(self):
        test_file = os.path.join(self.test_dir.name, "test_math.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("def test_addition():\n    assert 2 + 2 == 4\n")

        passed, log = SandboxTestRunner.run_tests(self.test_dir.name)
        self.assertTrue(passed)

    def test_run_failing_python_test(self):
        test_file = os.path.join(self.test_dir.name, "test_broken.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("def test_failing():\n    assert 2 + 2 == 5\n")

        passed, log = SandboxTestRunner.run_tests(self.test_dir.name)
        self.assertFalse(passed)
        self.assertIn("AssertionError", log)


if __name__ == "__main__":
    unittest.main()
