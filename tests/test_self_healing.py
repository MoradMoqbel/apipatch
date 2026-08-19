"""
Unit tests for Self-Healing Feedback Loop in ApiPatchEngine
"""

import unittest
from apipatch.engine import ApiPatchEngine
from apipatch.providers.base import BaseProvider
from typing import Dict, Any, List, Optional


class MockBrokenThenHealedProvider(BaseProvider):
    """
    Simulates an LLM provider that initially generates invalid syntax,
    then fixes it when heal_code is invoked with the error message.
    """
    def __init__(self):
        super().__init__()
        self.heal_called = False
        self.received_val_error = None

    def audit_code(
        self,
        file_name: str,
        code: str,
        detected_libraries: List[str],
        project_context: Optional[str] = None
    ) -> Dict[str, Any]:
        # Returns code with a syntax error (unclosed parenthesis)
        return {
            "has_breaking_changes": True,
            "detected_issues": [{
                "library": "openai",
                "deprecated_symbol": "openai.ChatCompletion.create",
                "replacement_symbol": "client.chat.completions.create",
                "description": "Migrate to OpenAI v1.0",
                "line_hint": "line 2"
            }],
            "refactored_code": "def ask():\n    return client.chat.completions.create(model='gpt-4o'\n"  # syntax error: missing closing paren
        }

    def heal_code(
        self,
        file_name: str,
        original_code: str,
        broken_code: str,
        validation_error: str,
        detected_libraries: Optional[List[str]] = None,
        project_context: Optional[str] = None
    ) -> Dict[str, Any]:
        self.heal_called = True
        self.received_val_error = validation_error
        # Returns corrected syntactically valid code
        return {
            "has_breaking_changes": True,
            "detected_issues": [{
                "library": "openai",
                "deprecated_symbol": "openai.ChatCompletion.create",
                "replacement_symbol": "client.chat.completions.create",
                "description": "Migrate to OpenAI v1.0",
                "line_hint": "line 2"
            }],
            "refactored_code": "def ask():\n    return client.chat.completions.create(model='gpt-4o')\n"
        }


class MockPermanentlyBrokenProvider(BaseProvider):
    """Simulates an LLM provider that fails self-healing repeatedly."""
    def audit_code(self, file_name, code, detected_libraries, project_context=None):
        return {
            "has_breaking_changes": True,
            "detected_issues": [{"library": "openai", "deprecated_symbol": "old", "replacement_symbol": "new", "description": "desc", "line_hint": "1"}],
            "refactored_code": "def broken(:"
        }

    def heal_code(self, file_name, original_code, broken_code, validation_error, detected_libraries=None, project_context=None):
        return {
            "has_breaking_changes": True,
            "detected_issues": [{"library": "openai", "deprecated_symbol": "old", "replacement_symbol": "new", "description": "desc", "line_hint": "1"}],
            "refactored_code": "def still_broken(:"
        }


class TestSelfHealing(unittest.TestCase):
    def test_self_healing_recovers_syntax_error(self):
        engine = ApiPatchEngine()
        mock_provider = MockBrokenThenHealedProvider()
        engine.provider = mock_provider

        orig_code = "def ask():\n    return openai.ChatCompletion.create()\n"
        res = engine.audit_code("test.py", orig_code, detected_libraries=["openai"])

        self.assertTrue(mock_provider.heal_called, "heal_code should have been called")
        self.assertIsNotNone(mock_provider.received_val_error)
        self.assertIn("SyntaxError", mock_provider.received_val_error)
        self.assertTrue(res["has_breaking_changes"])
        self.assertIn("client.chat.completions.create(model='gpt-4o')", res["refactored_code"])

    def test_permanently_broken_falls_back_safely(self):
        engine = ApiPatchEngine()
        engine.provider = MockPermanentlyBrokenProvider()

        orig_code = "def original_func():\n    pass\n"
        res = engine.audit_code("test.py", orig_code, detected_libraries=["openai"])

        # When self-healing fails all attempts, it should safely return empty_result without crashing
        self.assertFalse(res["has_breaking_changes"])
        self.assertEqual(res["refactored_code"], orig_code)


if __name__ == "__main__":
    unittest.main()
