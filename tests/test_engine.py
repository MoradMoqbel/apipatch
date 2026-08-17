"""
Unit tests for ApiPatchEngine
"""

import unittest
import os
import tempfile
from apipatch.engine import ApiPatchEngine


class TestApiPatchEngine(unittest.TestCase):
    def setUp(self):
        self.engine = ApiPatchEngine(create_backup=True)
        self.test_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.test_dir.cleanup()

    def test_audit_clean_code(self):
        clean_code = """
def add(a: int, b: int) -> int:
    return a + b
"""
        res = self.engine.audit_code("clean.py", clean_code)
        self.assertFalse(res["has_breaking_changes"])

    def test_audit_deprecated_code(self):
        dep_code = """
import stripe

def pay(token):
    return stripe.Charge.create(amount=1000, source=token)
"""
        res = self.engine.audit_code("stripe_service.py", dep_code)
        self.assertTrue(res["has_breaking_changes"])
        self.assertGreater(len(res["detected_issues"]), 0)

    def test_process_file_with_write_and_backup(self):
        file_path = os.path.join(self.test_dir.name, "target.py")
        dep_code = """import openai

def ask(q):
    res = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": q}])
    return res['choices'][0]['message']['content']
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(dep_code)

        result = self.engine.process_file(file_path, write_in_place=True)
        self.assertEqual(result["status"], "refactored")

        # Check that target file was updated
        with open(file_path, "r", encoding="utf-8") as f:
            new_content = f.read()
        self.assertIn("client.chat.completions.create", new_content)

        # Check that .bak backup was created
        backup_file = f"{file_path}.bak"
        self.assertTrue(os.path.exists(backup_file))
        with open(backup_file, "r", encoding="utf-8") as f:
            bak_content = f.read()
        self.assertEqual(bak_content, dep_code)


if __name__ == "__main__":
    unittest.main()
