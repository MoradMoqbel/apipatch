"""
Unit tests for ApiPatch Authoritative Migration Knowledge Base
"""

import unittest
from apipatch.knowledge import get_relevant_knowledge, MIGRATION_KNOWLEDGE_BASE


class TestMigrationKnowledge(unittest.TestCase):
    def test_google_genai_knowledge_selected(self):
        guidance = get_relevant_knowledge(
            detected_libraries=["google-genai"],
            file_content="import google.generativeai as genai"
        )
        self.assertIn("Google GenAI", guidance)
        self.assertIn("gemini-3.1-flash-image", guidance)
        self.assertIn("google.genai", guidance)

    def test_openai_knowledge_selected(self):
        guidance = get_relevant_knowledge(
            detected_libraries=["openai"],
            file_content="import openai\nopenai.ChatCompletion.create()"
        )
        self.assertIn("OpenAI v1.0+", guidance)
        self.assertIn("from openai import OpenAI", guidance)

    def test_langchain_knowledge_selected(self):
        guidance = get_relevant_knowledge(
            detected_libraries=["langchain"],
            file_content="from langchain.chat_models import ChatOpenAI"
        )
        self.assertIn("LangChain", guidance)
        self.assertIn("langchain_openai", guidance)
        self.assertIn("LCEL", guidance)

    def test_pydantic_knowledge_selected(self):
        guidance = get_relevant_knowledge(
            detected_libraries=["pydantic"],
            file_content="class Config:\n    orm_mode = True"
        )
        self.assertIn("Pydantic v2", guidance)
        self.assertIn("ConfigDict", guidance)

    def test_clean_file_no_unnecessary_knowledge(self):
        guidance = get_relevant_knowledge(
            detected_libraries=[],
            file_content="def add(a, b):\n    return a + b"
        )
        self.assertEqual(guidance, "")


if __name__ == "__main__":
    unittest.main()
