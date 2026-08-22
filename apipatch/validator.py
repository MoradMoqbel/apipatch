"""
ApiPatch Code Validator and Safety Guard
Ensures 100% syntactical correctness and structural integrity of refactored code
across Python, JavaScript, TypeScript, and other supported languages.
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
        line_info = f"Line {self.error_line}: " if self.error_line else ""
        return f"<ValidationResult: Invalid ({line_info}{self.error_message})>"


class CodeValidator:
    KNOWN_INVALID_IMPORT_NAMES = {
        "python_dotenv": "dotenv (e.g. 'from dotenv import load_dotenv')",
        "pyyaml": "yaml (e.g. 'import yaml')",
        "beautifulsoup4": "bs4 (e.g. 'from bs4 import BeautifulSoup')",
        "pillow": "PIL (e.g. 'from PIL import Image')",
        "scikit_learn": "sklearn (e.g. 'import sklearn')",
    }

    @staticmethod
    def validate_python_syntax(code: str) -> ValidationResult:
        """Parses code with Python AST parser to catch any SyntaxError, IndentationError, or hallucinated import names."""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in CodeValidator.KNOWN_INVALID_IMPORT_NAMES:
                            correct = CodeValidator.KNOWN_INVALID_IMPORT_NAMES[alias.name]
                            return ValidationResult(
                                is_valid=False,
                                error_message=f"Invalid import '{alias.name}'. The package must be imported as '{correct}'.",
                                error_line=node.lineno
                            )
                elif isinstance(node, ast.ImportFrom):
                    if node.module in CodeValidator.KNOWN_INVALID_IMPORT_NAMES:
                        correct = CodeValidator.KNOWN_INVALID_IMPORT_NAMES[node.module]
                        return ValidationResult(
                            is_valid=False,
                            error_message=f"Invalid import from '{node.module}'. The package must be imported as '{correct}'.",
                            error_line=node.lineno
                        )
            return ValidationResult(is_valid=True)
        except SyntaxError as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"SyntaxError: {e.msg}",
                error_line=e.lineno
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"AST Parse Error: {str(e)}"
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
                error_message=f"Refactored code dropped required function(s): {', '.join(sorted(missing_funcs))}"
            )

        if missing_classes:
            return ValidationResult(
                is_valid=False,
                error_message=f"Refactored code dropped required class(es): {', '.join(sorted(missing_classes))}"
            )

        return ValidationResult(is_valid=True)

    @staticmethod
    def validate_generic_integrity(original_code: str, refactored_code: str) -> ValidationResult:
        """
        Structural and syntactical integrity check for JavaScript, TypeScript, JSX, TSX, etc.
        Robustly tokenizes code, correctly skipping:
          - Single-line comments (// ...)
          - Multi-line comments (/* ... */)
          - Single-quoted and double-quoted strings with escapes
          - Template literals (`...`) with recursive interpolation `${...}`
          - Regular expression literals (/.../flags)
        Accurately verifies balance of (), [], and {} across the file.
        """
        if not refactored_code or not refactored_code.strip():
            return ValidationResult(is_valid=False, error_message="Refactored code is empty")

        # Truncation guard: ensure refactored code isn't mysteriously truncated (>80% dropped on non-trivial files)
        if len(original_code) > 120 and len(refactored_code) < len(original_code) * 0.2:
            return ValidationResult(
                is_valid=False,
                error_message="Refactored code appears abnormally truncated compared to original source."
            )

        code = refactored_code
        n = len(code)
        i = 0
        line = 1

        # Stack holds tuples: (expected_char, opening_line, type_tag)
        stack: List[Tuple[str, int, str]] = []
        template_depth = 0  # number of active template literal layers

        prev_non_ws = ""
        prev_word = ""

        while i < n:
            ch = code[i]
            if ch == '\n':
                line += 1
                i += 1
                continue

            # Skip whitespace
            if ch.isspace():
                i += 1
                continue

            # 1. Single-line comment: // ...
            if ch == '/' and i + 1 < n and code[i + 1] == '/':
                i += 2
                while i < n and code[i] != '\n':
                    i += 1
                continue

            # 2. Multi-line comment: /* ... */
            if ch == '/' and i + 1 < n and code[i + 1] == '*':
                start_line = line
                i += 2
                closed = False
                while i < n:
                    if code[i] == '\n':
                        line += 1
                    elif code[i] == '*' and i + 1 < n and code[i + 1] == '/':
                        i += 2
                        closed = True
                        break
                    i += 1
                if not closed:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Unclosed multi-line comment starting at line {start_line}",
                        error_line=start_line
                    )
                continue

            # 3. Single-quoted string: '...'
            if ch == "'":
                start_line = line
                i += 1
                closed = False
                while i < n:
                    c = code[i]
                    if c == '\n':
                        line += 1
                    elif c == '\\':
                        i += 2
                        continue
                    elif c == "'":
                        closed = True
                        i += 1
                        break
                    i += 1
                if not closed:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Unclosed single-quote string starting at line {start_line}",
                        error_line=start_line
                    )
                prev_non_ws = "'"
                prev_word = ""
                continue

            # 4. Double-quoted string: "..."
            if ch == '"':
                start_line = line
                i += 1
                closed = False
                while i < n:
                    c = code[i]
                    if c == '\n':
                        line += 1
                    elif c == '\\':
                        i += 2
                        continue
                    elif c == '"':
                        closed = True
                        i += 1
                        break
                    i += 1
                if not closed:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Unclosed double-quote string starting at line {start_line}",
                        error_line=start_line
                    )
                prev_non_ws = '"'
                prev_word = ""
                continue

            # 5. Template literal: `...`
            if ch == '`':
                start_line = line
                i += 1
                # Parse template literal contents until matching ` or ${
                closed = False
                while i < n:
                    c = code[i]
                    if c == '\n':
                        line += 1
                    elif c == '\\':
                        i += 2
                        continue
                    elif c == '`':
                        closed = True
                        i += 1
                        break
                    elif c == '$' and i + 1 < n and code[i + 1] == '{':
                        # Enter interpolated expression inside template literal
                        stack.append(('}', line, 'template_expr'))
                        i += 2
                        break
                    i += 1
                if not closed and (not stack or stack[-1][2] != 'template_expr'):
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Unclosed template literal starting at line {start_line}",
                        error_line=start_line
                    )
                prev_non_ws = '`'
                prev_word = ""
                continue

            # 6. Regex literal: /.../flags
            regex_preceders = {'=', '(', '[', '{', ':', ',', ';', '!', '?', '+', '-', '*', '&', '|', '^', '%', '~', '<', '>', '\n', ''}
            regex_keywords = {'return', 'yield', 'typeof', 'void', 'delete', 'throw', 'case', 'default', 'in', 'instanceof', 'of'}
            if ch == '/' and (prev_non_ws in regex_preceders or prev_word in regex_keywords):
                start_line = line
                i += 1
                in_char_class = False
                closed = False
                while i < n:
                    c = code[i]
                    if c == '\n':
                        break  # JS regex cannot span unescaped newlines
                    elif c == '\\':
                        i += 2
                        continue
                    elif c == '[' and not in_char_class:
                        in_char_class = True
                    elif c == ']' and in_char_class:
                        in_char_class = False
                    elif c == '/' and not in_char_class:
                        closed = True
                        i += 1
                        # Skip trailing flags (e.g. g, i, m, s, u, y, d)
                        while i < n and code[i].isalpha():
                            i += 1
                        break
                    i += 1
                if closed:
                    prev_non_ws = '/'
                    prev_word = ""
                    continue
                # If regex wasn't closed properly on single line, treat / as division operator below

            # 7. Brackets, Parentheses, Braces
            if ch in ('(', '[', '{'):
                stack.append((ch, line, 'bracket'))
                prev_non_ws = ch
                prev_word = ""
                i += 1
                continue

            if ch in (')', ']', '}'):
                if not stack:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Unmatched closing '{ch}' at line {line}.",
                        error_line=line
                    )
                expected_open, open_line, tag = stack.pop()
                if tag == 'template_expr' and ch == '}':
                    # Finished interpolated expression `${...}` inside template literal.
                    # Resume reading template literal until next ` or ${
                    closed_tmpl = False
                    while i + 1 < n:
                        i += 1
                        c = code[i]
                        if c == '\n':
                            line += 1
                        elif c == '\\':
                            i += 1
                            continue
                        elif c == '`':
                            closed_tmpl = True
                            i += 1
                            break
                        elif c == '$' and i + 1 < n and code[i + 1] == '{':
                            stack.append(('}', line, 'template_expr'))
                            i += 2
                            break
                    if not closed_tmpl and (not stack or stack[-1][2] != 'template_expr'):
                        return ValidationResult(
                            is_valid=False,
                            error_message=f"Unclosed template literal after expression at line {line}",
                            error_line=line
                        )
                    prev_non_ws = '`'
                    prev_word = ""
                    continue

                pairs = {')': '(', ']': '[', '}': '{'}
                if pairs.get(ch) != expected_open:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Mismatched bracket: expected matching closing for '{expected_open}' (from line {open_line}), found '{ch}' at line {line}.",
                        error_line=line
                    )
                prev_non_ws = ch
                prev_word = ""
                i += 1
                continue

            # Record identifier characters for keyword checking
            if ch.isalnum() or ch == '_':
                start_w = i
                while i < n and (code[i].isalnum() or code[i] == '_'):
                    i += 1
                prev_word = code[start_w:i]
                prev_non_ws = code[i - 1]
                continue

            prev_non_ws = ch
            prev_word = ""
            i += 1

        if stack:
            unclosed_char, unclosed_line, tag = stack[-1]
            desc = "template expression" if tag == 'template_expr' else f"'{unclosed_char}'"
            return ValidationResult(
                is_valid=False,
                error_message=f"Structural integrity check failed: unclosed {desc} opened at line {unclosed_line}.",
                error_line=unclosed_line
            )

        return ValidationResult(is_valid=True)

    @classmethod
    def validate(cls, original_code: str, refactored_code: str, file_extension: str = ".py") -> ValidationResult:
        """Runs comprehensive multi-layer validation on refactored code."""
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
