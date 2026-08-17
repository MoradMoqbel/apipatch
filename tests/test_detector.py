"""
Unit tests for AutoDeprecationDetector
"""

import unittest
import os
import tempfile
from apipatch.auto_detector import AutoDeprecationDetector


class TestAutoDetector(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.test_dir.cleanup()

    def test_requirements_txt_detection(self):
        req_file = os.path.join(self.test_dir.name, "requirements.txt")
        with open(req_file, "w", encoding="utf-8") as f:
            f.write("openai>=1.0.0\nstripe==5.0.0\npydantic~=2.0\n# comment\n")

        detector = AutoDeprecationDetector(target_dir=self.test_dir.name)
        deps = detector.detect_dependencies()
        self.assertIn("openai", deps)
        self.assertIn("stripe", deps)
        self.assertIn("pydantic", deps)

    def test_ast_import_detection(self):
        py_file = os.path.join(self.test_dir.name, "main.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write("import langchain\nfrom supabase import create_client\nimport os\n")

        detector = AutoDeprecationDetector(target_dir=self.test_dir.name)
        deps = detector.detect_dependencies()
        self.assertIn("langchain", deps)
        self.assertIn("supabase", deps)
        self.assertNotIn("os", deps)  # Standard library should be ignored


if __name__ == "__main__":
    unittest.main()
