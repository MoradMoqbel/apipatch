"""
Unit tests for ApiPatchEngine — LLM-free (offline) mode.
Tests the engine's behaviour when no AI provider is configured,
plus file I/O, diff generation, and directory scanning mechanics.
"""

import os
import unittest
import tempfile
from apipatch.engine import ApiPatchEngine


class TestApiPatchEngineOffline(unittest.TestCase):
    """Tests that do NOT require an LLM API key."""

    def setUp(self):
        # Engine with no provider configured (offline mode)
        self.engine = ApiPatchEngine(create_backup=True)
        self.test_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.test_dir.cleanup()

    # ── Offline audit returns a well-formed empty result ──────────────────────

    def test_audit_offline_returns_no_changes(self):
        """Without a provider the engine should return a clean result gracefully."""
        code = "def add(a, b):\n    return a + b\n"
        res = self.engine.audit_code("math.py", code)
        self.assertFalse(res["has_breaking_changes"])
        self.assertEqual(res["detected_issues"], [])
        # refactored_code is the original when no changes
        self.assertEqual(res["refactored_code"], code)

    # ── Diff generation ───────────────────────────────────────────────────────

    def test_generate_diff_identical_code(self):
        code = "x = 1\n"
        diff = self.engine.generate_diff(code, code, "test.py")
        self.assertEqual(diff, [])

    def test_generate_diff_changed_code(self):
        old = "x = 1\n"
        new = "x = 2\n"
        diff = self.engine.generate_diff(old, new, "test.py")
        self.assertTrue(any("-x = 1" in line for line in diff))
        self.assertTrue(any("+x = 2" in line for line in diff))

    # ── File I/O mechanics ────────────────────────────────────────────────────

    def test_process_file_clean_code_offline(self):
        """A clean file should be reported as 'clean' even offline."""
        file_path = os.path.join(self.test_dir.name, "clean.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("def greet(name):\n    return f'Hello, {name}'\n")

        result = self.engine.process_file(file_path, write_in_place=False)
        self.assertEqual(result["status"], "clean")

    def test_backup_created_on_write(self):
        """Backup file must be created when write_in_place=True and changes exist."""
        file_path = os.path.join(self.test_dir.name, "target.py")
        original = "x = 1\n"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(original)

        # Manually inject a fake audit result to bypass LLM
        def fake_audit(fp, code, detected_libraries=None):
            return {
                "has_breaking_changes": True,
                "detected_issues": [{
                    "library": "TestLib",
                    "deprecated_symbol": "x = 1",
                    "replacement_symbol": "x = 2",
                    "description": "Fake deprecation for backup test",
                    "line_hint": "line 1"
                }],
                "refactored_code": "x = 2\n"
            }

        self.engine.audit_code = fake_audit
        self.engine.process_file(file_path, write_in_place=True)

        backup = f"{file_path}.bak"
        self.assertTrue(os.path.exists(backup))
        with open(backup, "r") as f:
            self.assertEqual(f.read(), original)

    # ── Directory scanning mechanics ──────────────────────────────────────────

    def test_directory_scan_counts_files(self):
        """process_directory should count .py and .js files correctly."""
        for name, content in [
            ("a.py", "x = 1\n"),
            ("b.js", "const x = 1;\n"),
            ("c.ts", "let x: number = 1;\n"),
            ("skip.txt", "not a source file"),
        ]:
            with open(os.path.join(self.test_dir.name, name), "w") as f:
                f.write(content)

        result = self.engine.process_directory(self.test_dir.name, write_in_place=False)
        # 3 supported files (.py, .js, .ts); .txt should be ignored
        self.assertEqual(result["total_scanned"], 3)


if __name__ == "__main__":
    unittest.main()
