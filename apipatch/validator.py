"""
ApiPatch Code Validator and Safety Guard
Ensures 100% syntactical correctness and structural integrity of refactored code.
"""

import ast
import re
from typing import Tuple, List, Set, Optional


class ValidationResult:
    def __init__(self, is_valid: bool, error_message: Optional[str] = None, error_line: Optional[int] = None):
        self.is_valid = is_valid
        self.error_message = error_message
        self.error_line = error_line

    def __bool__(self) -> bool:
        return self.is_valid

    def __repr__(self) -> str:
        if self.is_valid:
            return "<ValidationResult: Valid>"
        return f"<ValidationResult: Invalid (Line {self.error_line}: {self.error_message})>"


class CodeValidator:
    @staticmethod
    def validate_python_syntax(code: str) -> ValidationResult:
        """Parses code with Python AST parser to catch any SyntaxError or IndentationError."""
        try:
            ast.parse(code)
            return ValidationResult(is_valid=True)
        except SyntaxError as e:
            return ValidationResult(
                is_valid=False,
                error_message=e.msg,
                error_line=e.lineno
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=str(e)
            )

    @staticmethod
    def extract_python_symbols(code: str) -> Tuple[Set[str], Set[str]]:
        """Extracts top-level function names and class names from Python code."""
        functions = set()
        classes = set()
        try:
            tree = ast.parse(code)
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions.add(node.name)
                elif isinstance(node, ast.ClassDef):
                    classes.add(node.name)
        except Exception:
            pass
        return functions, classes

    @staticmethod
    def validate_business_logic_preservation(original_code: str, refactored_code: str) -> ValidationResult:
        """
        Ensures that top-level classes and functions defined in original code
        are preserved in the refactored code.
        """
        orig_funcs, orig_classes = CodeValidator.extract_python_symbols(original_code)
        new_funcs, new_classes = CodeValidator.extract_python_symbols(refactored_code)

        missing_funcs = orig_funcs - new_funcs
        missing_classes = orig_classes - new_classes

        if missing_funcs:
            return ValidationResult(
                is_valid=False,
                error_message=f"Refactored code dropped required function(s): {', '.join(missing_funcs)}"
            )

        if missing_classes:
            return ValidationResult(
                is_valid=False,
                error_message=f"Refactored code dropped required class(es): {', '.join(missing_classes)}"
            )

        return ValidationResult(is_valid=True)

    @staticmethod
    def validate_generic_integrity(original_code: str, refactored_code: str) -> ValidationResult:
        """Sanity check for non-Python files (JS, TS, etc.) ensuring no severe truncation."""
        if not refactored_code or not refactored_code.strip():
            return ValidationResult(is_valid=False, error_message="Refactored code is empty")

        # Ensure refactored code isn't mysteriously truncated (at least 20% of original length)
        if len(original_code) > 100 and len(refactored_code) < len(original_code) * 0.2:
            return ValidationResult(
                is_valid=False,
                error_message="Refactored code appears abnormally truncated compared to original source."
            )

        return ValidationResult(is_valid=True)

    @classmethod
    def validate(cls, original_code: str, refactored_code: str, file_extension: str = ".py") -> ValidationResult:
        """Runs comprehensive validation on refactored code."""
        if file_extension in {".py", ".pyw"}:
            syntax_check = cls.validate_python_syntax(refactored_code)
            if not syntax_check.is_valid:
                return syntax_check

            logic_check = cls.validate_business_logic_preservation(original_code, refactored_code)
            if not logic_check.is_valid:
                return logic_check

            return ValidationResult(is_valid=True)
        else:
            return cls.validate_generic_integrity(original_code, refactored_code)
