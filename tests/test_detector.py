"""
Unit tests for AutoDeprecationDetector
Covers Python AST import extraction, JS/TS regex import extraction,
and all manifest-based dependency discovery.
"""

import os
import json
import unittest
import tempfile
from apipatch.auto_detector import AutoDeprecationDetector


class TestAutoDetector(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.test_dir.cleanup()

    # ── Python AST import extraction ──────────────────────────────────────────

    def test_python_ast_import_detection(self):
        py_file = os.path.join(self.test_dir.name, "main.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write("import langchain\nfrom supabase import create_client\nimport os\n")

        detector = AutoDeprecationDetector(target_dir=self.test_dir.name)
        deps = detector.detect_dependencies()
        self.assertIn("langchain", deps)
        self.assertIn("supabase", deps)
        self.assertNotIn("os", deps)  # stdlib → must be excluded

    def test_python_stdlib_excluded(self):
        py_file = os.path.join(self.test_dir.name, "stdlib.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write("import os\nimport sys\nimport json\nfrom pathlib import Path\n")

        detector = AutoDeprecationDetector(target_dir=self.test_dir.name)
        deps = detector.detect_dependencies()
        for stdlib_mod in ("os", "sys", "json", "pathlib"):
            self.assertNotIn(stdlib_mod, deps)

    # ── JS/TS import extraction ───────────────────────────────────────────────

    def test_js_esm_imports(self):
        js_file = os.path.join(self.test_dir.name, "app.js")
        with open(js_file, "w", encoding="utf-8") as f:
            f.write(
                "import axios from 'axios';\n"
                "import { createClient } from '@supabase/supabase-js';\n"
                "import './styles.css';\n"  # relative → should be ignored
            )

        detector = AutoDeprecationDetector(target_dir=self.test_dir.name)
        deps = detector.detect_dependencies()
        self.assertIn("axios", deps)
        self.assertIn("@supabase/supabase-js", deps)

    def test_ts_cjs_require(self):
        ts_file = os.path.join(self.test_dir.name, "server.ts")
        with open(ts_file, "w", encoding="utf-8") as f:
            f.write(
                "const express = require('express');\n"
                "const stripe = require('stripe');\n"
                "const path = require('path');\n"  # Node built-in → should be ignored
            )

        detector = AutoDeprecationDetector(target_dir=self.test_dir.name)
        deps = detector.detect_dependencies()
        self.assertIn("express", deps)
        self.assertIn("stripe", deps)
        self.assertNotIn("path", deps)  # Node built-in

    def test_tsx_scoped_package(self):
        tsx_file = os.path.join(self.test_dir.name, "Page.tsx")
        with open(tsx_file, "w", encoding="utf-8") as f:
            f.write(
                "import { useState } from 'react';\n"
                "import { OpenAI } from 'openai';\n"
                "import type { FC } from 'react';\n"
            )

        detector = AutoDeprecationDetector(target_dir=self.test_dir.name)
        deps = detector.detect_dependencies()
        self.assertIn("react", deps)
        self.assertIn("openai", deps)

    # ── Manifest-based detection ──────────────────────────────────────────────

    def test_requirements_txt_detection(self):
        req_file = os.path.join(self.test_dir.name, "requirements.txt")
        with open(req_file, "w", encoding="utf-8") as f:
            f.write("openai>=1.0.0\nstripe==5.0.0\npydantic~=2.0\n# comment\n")

        detector = AutoDeprecationDetector(target_dir=self.test_dir.name)
        deps = detector.detect_dependencies()
        self.assertIn("openai", deps)
        self.assertIn("stripe", deps)
        self.assertIn("pydantic", deps)

    def test_package_json_detection(self):
        pkg_json = os.path.join(self.test_dir.name, "package.json")
        with open(pkg_json, "w", encoding="utf-8") as f:
            json.dump({
                "dependencies": {"react": "^18.0.0", "axios": "^1.0.0"},
                "devDependencies": {"typescript": "^5.0.0"}
            }, f)

        detector = AutoDeprecationDetector(target_dir=self.test_dir.name)
        deps = detector.detect_dependencies()
        self.assertIn("react", deps)
        self.assertIn("axios", deps)
        self.assertIn("typescript", deps)

    # ── run_autonomous_discovery smoke test ───────────────────────────────────

    def test_run_autonomous_discovery_returns_dict(self):
        py_file = os.path.join(self.test_dir.name, "api.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write("import openai\nimport stripe\n")

        detector = AutoDeprecationDetector(target_dir=self.test_dir.name)
        result = detector.run_autonomous_discovery()

        self.assertIn("target_directory", result)
        self.assertIn("detected_packages", result)
        self.assertIn("openai", result["detected_packages"])
        self.assertIn("stripe", result["detected_packages"])


if __name__ == "__main__":
    unittest.main()
