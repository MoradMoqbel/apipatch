"""
Unit tests for CodeValidator
"""

import unittest
from apipatch.validator import CodeValidator


class TestCodeValidator(unittest.TestCase):
    def test_valid_python_syntax(self):
        valid_code = """
import os

def hello(name: str) -> str:
    return f"Hello, {name}!"

class Greeter:
    def __init__(self, greeting: str):
        self.greeting = greeting
"""
        result = CodeValidator.validate_python_syntax(valid_code)
        self.assertTrue(result.is_valid)

    def test_invalid_python_syntax(self):
        invalid_code = """
def broken_function(:
    return 123
"""
        result = CodeValidator.validate_python_syntax(invalid_code)
        self.assertFalse(result.is_valid)
        self.assertIsNotNone(result.error_line)

    def test_business_logic_preservation(self):
        orig = """
def calculate_tax(amount):
    return amount * 0.15

class UserAccount:
    pass
"""
        refactored_good = """
def calculate_tax(amount):
    return amount * 0.15

class UserAccount:
    pass
"""
        refactored_bad = """
def different_func():
    pass
"""
        res_good = CodeValidator.validate_business_logic_preservation(orig, refactored_good)
        self.assertTrue(res_good.is_valid)

        res_bad = CodeValidator.validate_business_logic_preservation(orig, refactored_bad)
        self.assertFalse(res_bad.is_valid)
        self.assertIn("calculate_tax", res_bad.error_message)

    def test_bracket_balance(self):
        good_js = "function add(a, b) { return [a, b]; }"
        bad_js = "function add(a, b) { return [a, b; }"

        self.assertTrue(CodeValidator.validate_bracket_balance(good_js).is_valid)
        self.assertFalse(CodeValidator.validate_bracket_balance(bad_js).is_valid)


if __name__ == "__main__":
    unittest.main()
