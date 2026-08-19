"""
Unit tests for JavaScript/TypeScript structural validation in CodeValidator
"""

import unittest
from apipatch.validator import CodeValidator


class TestJSValidator(unittest.TestCase):
    def test_valid_js_with_template_literal(self):
        js = """
const user = "Alice";
const greeting = `Hello, ${user}! Value: ${1 + 2}`;
console.log(greeting);
"""
        res = CodeValidator.validate_generic_integrity(js, js)
        self.assertTrue(res.is_valid)

    def test_valid_js_with_nested_template_literals(self):
        js = """
const message = `Outer ${`Inner ${[1, 2, 3].map(x => x * 2).join(',')}`} End`;
"""
        res = CodeValidator.validate_generic_integrity(js, js)
        self.assertTrue(res.is_valid)

    def test_valid_js_with_regex_literal(self):
        js = """
const pattern = /[a-z0-9_]+/gi;
const matched = text.match(/https?:\\/\\/[^\\s]+/);
if (matched) {
    console.log(matched[0]);
}
"""
        res = CodeValidator.validate_generic_integrity(js, js)
        self.assertTrue(res.is_valid)

    def test_valid_js_with_comments_containing_brackets(self):
        js = """
// Unmatched ( bracket in line comment
/* Unmatched { bracket in multi-line
   comment */
function test() {
    return true;
}
"""
        res = CodeValidator.validate_generic_integrity(js, js)
        self.assertTrue(res.is_valid)

    def test_invalid_js_unmatched_brace(self):
        js = """
function broken() {
    if (true) {
        console.log("missing closing brace");
}
"""
        res = CodeValidator.validate_generic_integrity(js, js)
        self.assertFalse(res.is_valid)
        self.assertIn("unclosed '{'", res.error_message.lower())

    def test_invalid_js_mismatched_brackets(self):
        js = """
const list = [1, 2, 3);
"""
        res = CodeValidator.validate_generic_integrity(js, js)
        self.assertFalse(res.is_valid)
        self.assertIn("mismatched bracket", res.error_message.lower())

    def test_invalid_js_unclosed_template_literal(self):
        js = """
const unclosed = `This template never ends...
console.log("oops");
"""
        res = CodeValidator.validate_generic_integrity(js, js)
        self.assertFalse(res.is_valid)
        self.assertIn("unclosed template literal", res.error_message.lower())


if __name__ == "__main__":
    unittest.main()
