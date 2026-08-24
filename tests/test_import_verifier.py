"""
Unit tests for Autonomous Dynamic Registry & Import Fact-Checking Engine
Verifies that hallucinated or non-existent package imports are rejected without hardcoded static rules.
"""

import unittest
from apipatch.doc_hunter import DocHunter
from apipatch.validator import CodeValidator


class TestImportVerifier(unittest.TestCase):
    def test_standard_library_imports_are_valid(self):
        self.assertTrue(DocHunter.is_valid_registry_import("os"))
        self.assertTrue(DocHunter.is_valid_registry_import("sys"))
        self.assertTrue(DocHunter.is_valid_registry_import("json"))
        self.assertTrue(DocHunter.is_valid_registry_import("pathlib"))
        self.assertTrue(DocHunter.is_valid_registry_import("typing"))
        self.assertTrue(DocHunter.is_valid_registry_import("asyncio"))

    def test_known_mapping_and_registered_pypi_imports_are_valid(self):
        self.assertTrue(DocHunter.is_valid_registry_import("dotenv"))
        self.assertTrue(DocHunter.is_valid_registry_import("yaml"))
        self.assertTrue(DocHunter.is_valid_registry_import("PIL"))
        self.assertTrue(DocHunter.is_valid_registry_import("google.genai"))
        self.assertTrue(DocHunter.is_valid_registry_import("google.adk"))
        self.assertTrue(DocHunter.is_valid_registry_import("pydantic"))
        self.assertTrue(DocHunter.is_valid_registry_import("openai"))

    def test_hallucinated_package_imports_are_rejected(self):
        # google_generativeai does not exist on PyPI as an import module
        self.assertFalse(DocHunter.is_valid_registry_import("google_generativeai"))
        self.assertFalse(DocHunter.is_valid_registry_import("non_existent_fake_package_xyz_9999"))

    def test_validator_rejects_hallucinated_import_in_refactored_code(self):
        orig_code = """
from google.adk.agents import LlmAgent, SequentialAgent
from google.genai import types

def run():
    pass
"""
        # Bad refactored code that hallucinates google_generativeai
        bad_refactored = """
from google_generativeai.agents import LlmAgent, SequentialAgent
from google.generativeai import types

def run():
    pass
"""
        result = CodeValidator.validate(orig_code, bad_refactored, file_extension=".py")
        self.assertFalse(result.is_valid)
        self.assertIn("google_generativeai", result.error_message)

    def test_validator_accepts_valid_modern_import_in_refactored_code(self):
        orig_code = """
import openai

def ask():
    return 1
"""
        good_refactored = """
from openai import OpenAI

client = OpenAI()

def ask():
    return 1
"""
        result = CodeValidator.validate(orig_code, good_refactored, file_extension=".py")
        self.assertTrue(result.is_valid)


if __name__ == "__main__":
    unittest.main()
