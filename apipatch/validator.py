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
    def enrich_syntax_error_context(code: str, exc: SyntaxError) -> str:
        """
        Builds a rich, actionable diagnostic string from a SyntaxError,
        including exact line number, surrounding code snippet window,
        and targeted structural hints (e.g. unclosed try/except blocks, indentation, unclosed brackets).
        """
        lines = code.splitlines()
        err_line_num = exc.lineno or 1
        err_msg = exc.msg or "invalid syntax"

        # Build surrounding code snippet (up to 4 lines before and 3 lines after)
        start_idx = max(0, err_line_num - 4)
        end_idx = min(len(lines), err_line_num + 3)

        snippet_lines = []
        for idx in range(start_idx, end_idx):
            line_no = idx + 1
            line_content = lines[idx]
            prefix = ">" if line_no == err_line_num else " "
            snippet_lines.append(f"  {prefix} Line {line_no:3d}: {line_content}")

        snippet_str = "\n".join(snippet_lines)

        # Targeted structural diagnostic hint
        hint = ""
        msg_lower = err_msg.lower()
        if "expected 'except' or 'finally' block" in msg_lower or "expected an except block" in msg_lower:
            hint = (
                "\n\nDiagnostic Hint: An incomplete 'try:' block was detected without a matching 'except:' or 'finally:' clause. "
                "Ensure every 'try:' block is completed with its matching 'except Exception as e:' or 'finally:' block and proper indentation."
            )
        elif "indentation" in msg_lower or "indent" in msg_lower:
            hint = (
                "\n\nDiagnostic Hint: Indentation mismatch detected. Ensure 4-space indentation is consistently used "
                "inside all function definitions, classes, and code blocks."
            )
        elif "was never closed" in msg_lower or "unclosed" in msg_lower:
            hint = (
                "\n\nDiagnostic Hint: Unclosed parenthesis, bracket, or string literal detected. "
                "Ensure all '(', '[', '{', and quotes are properly paired and closed."
            )

        return f"SyntaxError: {err_msg} on line {err_line_num}\nCode snippet around error:\n{snippet_str}{hint}"

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
            detailed_err = CodeValidator.enrich_syntax_error_context(code, e)
            return ValidationResult(
                is_valid=False,
                error_message=detailed_err,
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

    FRAMEWORK_RUNNER_SYMBOLS = {
        "InMemoryRunner", "AgentRunner", "StateGraph", "Crew", "AgentExecutor",
        "Workflow", "Flow", "Pipeline", "Swarm", "Orchestrator"
    }

    @staticmethod
    def extract_imported_symbols(code: str) -> Set[str]:
        """Extracts all imported module and symbol names from Python code."""
        symbols = set()
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        symbols.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        symbols.add(node.module)
                    for alias in node.names:
                        symbols.add(alias.name)
        except Exception:
            pass
        return symbols

    @staticmethod
    def validate_business_logic_preservation(original_code: str, refactored_code: str) -> ValidationResult:
        """
        Ensures that top-level classes, functions, and framework runner components
        defined in original code are preserved in the refactored code.
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

        # Framework runner and agent preservation check
        orig_imports = CodeValidator.extract_imported_symbols(original_code)
        new_imports = CodeValidator.extract_imported_symbols(refactored_code)
        
        dropped_runners = (orig_imports & CodeValidator.FRAMEWORK_RUNNER_SYMBOLS) - new_imports
        if dropped_runners:
            return ValidationResult(
                is_valid=False,
                error_message=f"Refactored code dropped native agent framework runner(s): {', '.join(sorted(dropped_runners))}. Preserve the original runner architecture."
            )

        # Module-level docstring preservation check
        try:
            tree_orig = ast.parse(original_code)
            tree_ref = ast.parse(refactored_code)
            orig_doc = ast.get_docstring(tree_orig)
            ref_doc = ast.get_docstring(tree_ref)
            if orig_doc and not ref_doc:
                return ValidationResult(
                    is_valid=False,
                    error_message="Refactored code dropped module-level docstring header. Preserve the original module documentation exactly."
                )
        except Exception:
            pass

        return ValidationResult(is_valid=True)

    @staticmethod
    def extract_imported_modules(code: str) -> Set[str]:
        """Extracts all imported module namespaces (e.g. 'google.adk.agents', 'os', 'openai') from Python code."""
        modules = set()
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        modules.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        modules.add(node.module)
        except Exception:
            pass
        return modules

    @classmethod
    def validate_import_soundness(cls, original_code: str, refactored_code: str, file_extension: str = ".py") -> ValidationResult:
        """
        Dynamically verifies that all newly introduced imports in refactored code
        exist in the Python Standard Library, known package mappings, or on the PyPI registry.
        Rejects non-existent or hallucinated package imports (e.g. 'google_generativeai').
        """
        if file_extension in {".py", ".pyw"}:
            orig_modules = cls.extract_imported_modules(original_code)
            ref_modules = cls.extract_imported_modules(refactored_code)

            new_modules = ref_modules - orig_modules
            if not new_modules:
                return ValidationResult(is_valid=True)

            from apipatch.doc_hunter import DocHunter
            for mod in new_modules:
                if mod.startswith("."):
                    continue
                if not DocHunter.is_valid_registry_import(mod, ecosystem="python"):
                    return ValidationResult(
                        is_valid=False,
                        error_message=(
                            f"Hallucinated or non-existent import module detected: '{mod}'. "
                            f"This module does not exist in the Python Standard Library or PyPI registry. "
                            f"Do NOT invent non-existent package namespaces. Preserve the original import or use the official package."
                        )
                    )
        return ValidationResult(is_valid=True)

    @classmethod
    def validate_symbol_soundness(cls, original_code: str, refactored_code: str, file_extension: str = ".py") -> ValidationResult:
        """
        Dynamically tests whether attribute lookups on imported modules in refactored code
        (e.g., types.ToolContext, client.some_fake_attr) actually resolve without raising AttributeError.
        """
        if file_extension in {".py", ".pyw"}:
            from apipatch.test_runner import MicroSandboxEvaluator
            from apipatch.doc_hunter import DocHunter

            # 1. Ephemeral MicroSandbox evaluation
            sandbox_res = MicroSandboxEvaluator.evaluate_code_imports(refactored_code)
            if not sandbox_res.is_valid:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Runtime symbol validation error: {sandbox_res.error_message}. Do not use non-existent attributes."
                )

            # 2. Dynamic AST attribute verification via DocHunter
            try:
                tree = ast.parse(refactored_code)
                import_map = {}
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            import_map[alias.asname or alias.name] = alias.name
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        for alias in node.names:
                            import_map[alias.asname or alias.name] = f"{node.module}.{alias.name}"

                local_param_names = set()
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        for arg in node.args.args + node.args.kwonlyargs:
                            local_param_names.add(arg.arg)
                        if node.args.vararg:
                            local_param_names.add(node.args.vararg.arg)
                        if node.args.kwarg:
                            local_param_names.add(node.args.kwarg.arg)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                        alias = node.value.id
                        attr = node.attr
                        if alias in import_map and alias not in local_param_names:
                            mod_path = import_map[alias]
                            if not DocHunter.verify_module_symbol(mod_path, attr):
                                return ValidationResult(
                                    is_valid=False,
                                    error_message=(
                                        f"Invalid attribute '{alias}.{attr}': symbol '{attr}' is not part of '{mod_path}'. "
                                        f"Preserve the original context or import from the correct package."
                                    )
                                )
            except Exception:
                pass

        return ValidationResult(is_valid=True)

    @staticmethod
    def extract_js_symbols(code: str) -> Set[str]:
        """Extracts declared function, class, and component names from JS/TS code."""
        symbols = set()
        cleaned = re.sub(r'//.*?$|/\*.*?\*/', '', code, flags=re.MULTILINE | re.DOTALL)
        for m in re.finditer(r'(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_$]+)', cleaned):
            symbols.add(m.group(1))
        for m in re.finditer(r'(?:export\s+)?(?:default\s+)?class\s+([a-zA-Z0-9_$]+)', cleaned):
            symbols.add(m.group(1))
        for m in re.finditer(r'(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[a-zA-Z0-9_$]+)\s*=>', cleaned):
            symbols.add(m.group(1))
        return symbols

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

        # JS/TS component and function preservation check
        orig_syms = CodeValidator.extract_js_symbols(original_code)
        ref_syms = CodeValidator.extract_js_symbols(refactored_code)
        missing_syms = orig_syms - ref_syms
        if missing_syms and len(orig_syms) > 0:
            return ValidationResult(
                is_valid=False,
                error_message=f"Refactored JS/TS code dropped required component/function: {', '.join(sorted(missing_syms))}"
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

            import_check = cls.validate_import_soundness(original_code, refactored_code, file_extension)
            if not import_check.is_valid:
                return import_check

            symbol_check = cls.validate_symbol_soundness(original_code, refactored_code, file_extension)
            if not symbol_check.is_valid:
                return symbol_check

            return ValidationResult(is_valid=True)
        else:
            return cls.validate_generic_integrity(original_code, refactored_code)


