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
        return {
            "has_breaking_changes": True,
            "detected_issues": [{
                "library": "openai",
                "deprecated_symbol": "openai.ChatCompletion.create",
                "replacement_symbol": "client.chat.completions.create",
                "description": "Migrate to OpenAI v1.0",
                "line_hint": "line 2"
            }],
            "refactored_code": "def ask():\n    return client.chat.completions.create(model='gpt-4o'\n"
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

        self.assertFalse(res["has_breaking_changes"])
        self.assertEqual(res["refactored_code"], orig_code)

    def test_self_healing_recovers_from_hallucinated_import(self):
        class MockHallucinatedThenHealedProvider(BaseProvider):
            def __init__(self):
                super().__init__()
                self.heal_called = False
                self.received_val_error = None

            def audit_code(self, file_name, code, detected_libraries, project_context=None):
                return {
                    "has_breaking_changes": True,
                    "detected_issues": [{"library": "google-genai", "deprecated_symbol": "genai", "replacement_symbol": "genai.Client", "description": "Migrate SDK", "line_hint": "1"}],
                    "refactored_code": "from google_generativeai.agents import LlmAgent\n\ndef run():\n    pass\n"
                }

            def heal_code(self, file_name, original_code, broken_code, validation_error, detected_libraries=None, project_context=None):
                self.heal_called = True
                self.received_val_error = validation_error
                return {
                    "has_breaking_changes": True,
                    "detected_issues": [{"library": "google-genai", "deprecated_symbol": "genai", "replacement_symbol": "genai.Client", "description": "Migrate SDK", "line_hint": "1"}],
                    "refactored_code": "from google.adk.agents import LlmAgent\nfrom google import genai\n\ndef run():\n    pass\n"
                }

        engine = ApiPatchEngine()
        mock_provider = MockHallucinatedThenHealedProvider()
        engine.provider = mock_provider

        orig_code = "from google.adk.agents import LlmAgent\nimport google.generativeai as genai\n\ndef run():\n    pass\n"
        res = engine.audit_code("agent.py", orig_code, detected_libraries=["google-genai"])

        self.assertTrue(mock_provider.heal_called)
        self.assertIn("google_generativeai", mock_provider.received_val_error)
        self.assertTrue(res["has_breaking_changes"])
        self.assertIn("from google.adk.agents import LlmAgent", res["refactored_code"])

    def test_rich_syntax_error_diagnostics_formatting(self):
        from apipatch.validator import CodeValidator
        broken_try_code = "def fetch_data():\n    try:\n        data = request()\n"
        val = CodeValidator.validate_python_syntax(broken_try_code)
        self.assertFalse(val.is_valid)
        self.assertIn("Line", val.error_message)
        self.assertIn("Diagnostic Hint", val.error_message)
        self.assertIn("try:", val.error_message)

    def test_self_healing_recovers_missing_except_block(self):
        class MockTryExceptHealer(BaseProvider):
            def __init__(self):
                super().__init__()
                self.heal_called = False
                self.received_val_error = None

            def audit_code(self, file_name, code, detected_libraries, project_context=None):
                return {
                    "has_breaking_changes": True,
                    "detected_issues": [{"library": "openai", "deprecated_symbol": "create", "replacement_symbol": "create", "description": "fix", "line_hint": "1"}],
                    "refactored_code": "import openai\n\ndef run():\n    try:\n        openai.ChatCompletion.create()\n"
                }

            def heal_code(self, file_name, original_code, broken_code, validation_error, detected_libraries=None, project_context=None):
                self.heal_called = True
                self.received_val_error = validation_error
                return {
                    "has_breaking_changes": True,
                    "detected_issues": [{"library": "openai", "deprecated_symbol": "create", "replacement_symbol": "create", "description": "fix", "line_hint": "1"}],
                    "refactored_code": "import openai\n\ndef run():\n    try:\n        client = openai.OpenAI()\n        client.chat.completions.create()\n    except Exception as e:\n        pass\n"
                }

        engine = ApiPatchEngine()
        mock_provider = MockTryExceptHealer()
        engine.provider = mock_provider

        orig_code = "import openai\n\ndef run():\n    try:\n        openai.ChatCompletion.create()\n    except Exception as e:\n        pass\n"
        res = engine.audit_code("tools.py", orig_code, detected_libraries=["openai"])

        self.assertTrue(mock_provider.heal_called)
        self.assertIn("Diagnostic Hint", mock_provider.received_val_error)
        self.assertTrue(res["has_breaking_changes"])
        self.assertIn("except Exception as e:", res["refactored_code"])


if __name__ == "__main__":
    unittest.main()

