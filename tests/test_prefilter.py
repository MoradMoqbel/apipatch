"""
Unit tests for Smart Local Pre-filtering (should_audit_file)
"""

import unittest
from apipatch.auto_detector import should_audit_file


class TestPreFilter(unittest.TestCase):
    def test_clean_python_file_skipped(self):
        code = """
import os
import sys

def calculate_sum(a, b):
    return a + b
"""
        detected_libs = ["openai", "stripe", "langchain"]
        should_audit = should_audit_file(code, "utils.py", detected_libs)
        self.assertFalse(should_audit, "Clean Python file without target libraries should be skipped")

    def test_matched_python_file_audited(self):
        code = """
import openai

def ask(prompt):
    return openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[])
"""
        detected_libs = ["openai", "stripe"]
        should_audit = should_audit_file(code, "services/ai.py", detected_libs)
        self.assertTrue(should_audit, "Python file with matching import must be audited")

    def test_python_file_hyphen_underscore_match(self):
        code = """
from langchain_core.prompts import PromptTemplate
"""
        detected_libs = ["langchain-core"]
        should_audit = should_audit_file(code, "agent.py", detected_libs)
        self.assertTrue(should_audit, "langchain_core should match langchain-core")

    def test_clean_js_file_skipped(self):
        code = """
const fs = require('fs');
const path = require('path');

function readConfig() {
    return fs.readFileSync('config.json');
}
module.exports = { readConfig };
"""
        detected_libs = ["axios", "lodash", "@supabase/supabase-js"]
        should_audit = should_audit_file(code, "helper.js", detected_libs)
        self.assertFalse(should_audit, "Clean JS file without target libraries should be skipped")

    def test_matched_js_scoped_package_audited(self):
        code = """
import { createClient } from '@supabase/supabase-js';

const client = createClient('url', 'key');
"""
        detected_libs = ["@supabase/supabase-js", "react"]
        should_audit = should_audit_file(code, "supabaseClient.ts", detected_libs)
        self.assertTrue(should_audit, "TS file importing scoped package must be audited")

    def test_empty_file_skipped(self):
        self.assertFalse(should_audit_file("", "empty.py", ["openai"]))
        self.assertFalse(should_audit_file("   \n\t  ", "empty.js", ["openai"]))

    def test_no_detected_libs_audits_by_default(self):
        code = "import something"
        self.assertTrue(should_audit_file(code, "file.py", []))
        self.assertTrue(should_audit_file(code, "file.py", None))


if __name__ == "__main__":
    unittest.main()
