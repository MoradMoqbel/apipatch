"""
ApiPatch Autonomous Dependency & Import Detector
Discovers all third-party libraries used in a project (Python, JavaScript, TypeScript)
without any hardcoded rules — enabling the LLM engine to reason about ANY library.
"""

import os
import ast
import json
import re
from typing import List, Set, Dict, Any, Optional
from apipatch.providers.factory import ProviderFactory

# Python standard library module names (excluded from "third-party" list)
STANDARD_LIB_MODULES = {
    "abc", "argparse", "array", "ast", "asyncio", "base64", "binascii", "bisect",
    "builtins", "calendar", "cmath", "collections", "concurrent", "contextlib",
    "copy", "csv", "ctypes", "dataclasses", "datetime", "decimal", "difflib",
    "dis", "doctest", "email", "enum", "errno", "faulthandler", "fcntl", "filecmp",
    "fileinput", "fnmatch", "fractions", "functools", "gc", "getopt", "getpass",
    "gettext", "glob", "graphlib", "gzip", "hashlib", "heapq", "hmac", "html",
    "http", "idlelib", "imaplib", "imghdr", "importlib", "inspect", "io",
    "ipaddress", "itertools", "json", "keyword", "linecache", "locale", "logging",
    "lzma", "mailbox", "mailcap", "marshal", "math", "mimetypes", "mmap",
    "modulefinder", "multiprocessing", "netrc", "nntplib", "numbers", "operator",
    "os", "pathlib", "pdb", "pickle", "pipes", "pkgutil", "platform", "plistlib",
    "poplib", "posix", "pprint", "profile", "pstats", "pty", "pwd", "py_compile",
    "pyclbr", "pydoc", "queue", "quopri", "random", "re", "readline", "reprlib",
    "resource", "rlcompleter", "runpy", "sched", "secrets", "select", "selectors",
    "shelve", "shlex", "shutil", "signal", "site", "smtpd", "smtplib", "sndhdr",
    "socket", "socketserver", "spwd", "sqlite3", "ssl", "stat", "statistics",
    "string", "stringprep", "struct", "subprocess", "sunau", "symtable", "sys",
    "sysconfig", "syslog", "tabnanny", "tarfile", "telnetlib", "tempfile", "termios",
    "test", "textwrap", "threading", "time", "timeit", "tkinter", "token",
    "tokenize", "tomllib", "trace", "traceback", "tracemalloc", "tty", "turtle",
    "turtledemo", "types", "typing", "unicodedata", "unittest", "urllib", "uu",
    "uuid", "venv", "warnings", "wave", "weakref", "webbrowser", "winreg", "winsound",
    "wsgiref", "xdrlib", "xml", "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib",
    "zoneinfo"
}

# Node.js built-in modules (excluded from third-party list for JS/TS projects)
NODE_BUILTIN_MODULES = {
    "fs", "path", "http", "https", "os", "crypto", "stream", "util", "events",
    "child_process", "cluster", "dgram", "dns", "domain", "net", "querystring",
    "readline", "repl", "string_decoder", "timers", "tls", "tty", "url",
    "v8", "vm", "worker_threads", "zlib", "buffer", "assert", "console",
    "module", "process", "inspector", "perf_hooks", "async_hooks"
}


class AutoDeprecationDetector:
    def __init__(
        self,
        target_dir: str = ".",
        provider_name: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        self.target_dir = os.path.abspath(target_dir)
        self.provider = ProviderFactory.get_provider(
            provider_name=provider_name, api_key=api_key
        )

    # ─── Python Import Extraction ─────────────────────────────────────────────

    def extract_imports_from_file(self, file_path: str) -> Set[str]:
        """
        Uses Python AST to extract all third-party imported module names
        from a .py or .pyw source file.
        """
        imports: Set[str] = set()
        if not file_path.endswith((".py", ".pyw")):
            return imports
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top_pkg = alias.name.split('.')[0]
                        if top_pkg not in STANDARD_LIB_MODULES:
                            imports.add(top_pkg)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        top_pkg = node.module.split('.')[0]
                        if top_pkg not in STANDARD_LIB_MODULES:
                            imports.add(top_pkg)
        except Exception:
            pass
        return imports

    # ─── JS/TS Import Extraction ──────────────────────────────────────────────

    def extract_imports_from_js_file(self, file_path: str) -> Set[str]:
        """
        Uses regex to extract third-party package names from
        JS / TS / JSX / TSX / MJS / CJS source files.
        """
        imports: Set[str] = set()
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
            return imports
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # ESM: import ... from 'pkg'  /  import 'pkg'
            esm_patterns = re.findall(
                r"""(?:^|\n)\s*import\s+(?:[^'"]*?from\s+)?['"]([@\w][\w/.-]*)['"]""",
                content
            )
            # CJS: require('pkg')
            cjs_patterns = re.findall(r"""require\s*\(\s*['"]([@\w][\w/.-]*)['"]\s*\)""", content)

            for raw in esm_patterns + cjs_patterns:
                # Normalise scoped packages: @org/pkg -> @org/pkg
                # Strip sub-paths: lodash/merge -> lodash
                if raw.startswith('@'):
                    parts = raw.split('/')
                    pkg = '/'.join(parts[:2]) if len(parts) >= 2 else raw
                else:
                    pkg = raw.split('/')[0]

                if pkg and pkg not in NODE_BUILTIN_MODULES and not pkg.startswith('.'):
                    imports.add(pkg)
        except Exception:
            pass
        return imports

    # ─── Manifest-based Dependency Discovery ─────────────────────────────────

    def _parse_requirements_txt(self) -> Set[str]:
        deps: Set[str] = set()
        req_path = os.path.join(self.target_dir, "requirements.txt")
        if os.path.exists(req_path):
            with open(req_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("-"):
                        pkg = re.split(r"[><=~;!@\[]", line)[0].strip().lower()
                        if pkg:
                            deps.add(pkg)
        return deps

    def _parse_package_json(self) -> Set[str]:
        deps: Set[str] = set()
        pkg_json = os.path.join(self.target_dir, "package.json")
        if os.path.exists(pkg_json):
            try:
                with open(pkg_json, "r", encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)
                for key in ("dependencies", "devDependencies", "peerDependencies"):
                    if key in data and isinstance(data[key], dict):
                        deps.update(p.lower() for p in data[key].keys())
            except Exception:
                pass
        return deps

    def _parse_pyproject_toml(self) -> Set[str]:
        deps: Set[str] = set()
        pyproject = os.path.join(self.target_dir, "pyproject.toml")
        if os.path.exists(pyproject):
            try:
                with open(pyproject, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                # Extract quoted package names from dependency lists
                for match in re.findall(r'"([a-zA-Z0-9_\-]+)(?:[><=~;].*)?[">\s]', content):
                    m = match.strip().lower()
                    if m and m not in {"apipatch", "setuptools", "wheel", "pytest", "python"}:
                        deps.add(m)
            except Exception:
                pass
        return deps

    # ─── Main Detection API ───────────────────────────────────────────────────

    def detect_dependencies(self) -> List[str]:
        """
        Discovers all third-party packages from:
        1. requirements.txt
        2. package.json
        3. pyproject.toml
        4. Recursive AST inspection of Python source files
        5. Regex inspection of JS/TS source files
        """
        dependencies: Set[str] = set()

        dependencies.update(self._parse_requirements_txt())
        dependencies.update(self._parse_package_json())
        dependencies.update(self._parse_pyproject_toml())

        ignore_dirs = {
            ".git", "node_modules", "venv", ".venv", "__pycache__",
            ".gemini", "dist", "build", ".next", ".nuxt", "out", "coverage"
        }

        for root, dirs, files in os.walk(self.target_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                full_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()
                if ext in {".py", ".pyw"}:
                    dependencies.update(self.extract_imports_from_file(full_path))
                elif ext in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
                    dependencies.update(self.extract_imports_from_js_file(full_path))

        return sorted(dependencies)

    def run_autonomous_discovery(self) -> Dict[str, Any]:
        """Runs end-to-end autonomous dependency discovery and prints a summary."""
        deps = self.detect_dependencies()
        print(f"\n[ApiPatch] Detected {len(deps)} third-party package(s) in '{self.target_dir}':")
        for dep in deps:
            print(f"  - {dep}")
        print(
            "\nAll detected packages will be passed to the AI engine "
            "for dynamic deprecation analysis when you run `apipatch scan` or `apipatch fix`.\n"
        )
        return {
            "target_directory": self.target_dir,
            "detected_packages": deps,
        }
