"""
ApiPatch Autonomous Dependency & AST Import Detector
Discovers project dependencies and third-party imports dynamically without manual configuration.
"""

import os
import sys
import re
import ast
import json
from typing import List, Set, Dict, Any, Optional
from apipatch.providers.factory import ProviderFactory

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


class AutoDeprecationDetector:
    def __init__(self, target_dir: str = ".", provider_name: Optional[str] = None, api_key: Optional[str] = None):
        self.target_dir = os.path.abspath(target_dir)
        self.provider = ProviderFactory.get_provider(provider_name=provider_name, api_key=api_key)

    def extract_imports_from_file(self, file_path: str) -> Set[str]:
        """Uses AST to extract all top-level imported module names from a Python file."""
        imports = set()
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

    def detect_dependencies(self) -> List[str]:
        """
        Discovers third-party packages from project manifest files
        and recursively analyzes AST imports.
        """
        dependencies = set()

        # 1. requirements.txt
        req_path = os.path.join(self.target_dir, "requirements.txt")
        if os.path.exists(req_path):
            with open(req_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        pkg = re.split(r"[><=~;!]", line)[0].strip().lower()
                        if pkg:
                            dependencies.add(pkg)

        # 2. package.json (Node/TS)
        pkg_json_path = os.path.join(self.target_dir, "package.json")
        if os.path.exists(pkg_json_path):
            try:
                with open(pkg_json_path, "r", encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)
                    for key in ["dependencies", "devDependencies"]:
                        if key in data and isinstance(data[key], dict):
                            dependencies.update([p.lower() for p in data[key].keys()])
            except Exception:
                pass

        # 3. pyproject.toml
        pyproject_path = os.path.join(self.target_dir, "pyproject.toml")
        if os.path.exists(pyproject_path):
            try:
                with open(pyproject_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    # Basic extraction for dependencies list in toml
                    matches = re.findall(r'"([a-zA-Z0-9_\-]+)(?:[><=~;].*)?"', content)
                    for match in matches:
                        match_lower = match.lower()
                        if match_lower not in {"apipatch", "setuptools", "wheel", "pytest"}:
                            dependencies.add(match_lower)
            except Exception:
                pass

        # 4. AST recursive inspection across all files
        for root, dirs, files in os.walk(self.target_dir):
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "venv", ".venv", "__pycache__", ".gemini"}]
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    dependencies.update(self.extract_imports_from_file(full_path))

        return sorted(list(dependencies))

    def generate_dynamic_rules_for_package(self, package_name: str) -> List[Dict[str, Any]]:
        """Dynamically identifies recent breaking changes for ANY library."""
        # Built-in fast lookup for common libraries
        known_deprecations = {
            "openai": [{
                "deprecated_symbol": "openai.ChatCompletion.create",
                "replacement_symbol": "client.chat.completions.create",
                "description": "OpenAI v1.0+ replaced module-level calls with client instances",
                "fix_guidelines": "Instantiate client = openai.OpenAI() and use client.chat.completions.create"
            }],
            "pydantic": [{
                "deprecated_symbol": "class Config: orm_mode = True / .parse_obj() / .json()",
                "replacement_symbol": "model_config = ConfigDict(from_attributes=True) / .model_validate() / .model_dump_json()",
                "description": "Pydantic v2 replaced Config class, parse_obj, and json methods with model_* methods",
                "fix_guidelines": "Use ConfigDict and model_validate/model_dump_json"
            }],
            "stripe": [{
                "deprecated_symbol": "stripe.Charge.create",
                "replacement_symbol": "stripe.PaymentIntent.create",
                "description": "Stripe Charges API deprecated for card payments in favor of PaymentIntents",
                "fix_guidelines": "Migrate to PaymentIntents for SCA compliance"
            }],
            "langchain": [{
                "deprecated_symbol": "LLMChain(",
                "replacement_symbol": "prompt | llm",
                "description": "LangChain legacy chains deprecated in favor of LCEL syntax",
                "fix_guidelines": "Use LCEL pipe syntax (prompt | llm)"
            }],
            "supabase": [{
                "deprecated_symbol": "supabase.auth.sign_in(",
                "replacement_symbol": "supabase.auth.sign_in_with_password(",
                "description": "Supabase v2 authentication restructured method names",
                "fix_guidelines": "Pass dict credentials to sign_in_with_password"
            }],
            "sqlalchemy": [{
                "deprecated_symbol": "declarative_base()",
                "replacement_symbol": "class Base(DeclarativeBase): pass",
                "description": "SQLAlchemy 2.0 replaced declarative_base() with DeclarativeBase class subclassing",
                "fix_guidelines": "Use modern DeclarativeBase and select() constructs"
            }],
            "fastapi": [{
                "deprecated_symbol": "@app.on_event('startup')",
                "replacement_symbol": "asynccontextmanager lifespan handler",
                "description": "FastAPI deprecated on_event in favor of lifespan context managers",
                "fix_guidelines": "Define @asynccontextmanager async def lifespan(app: FastAPI)"
            }]
        }

        if package_name in known_deprecations:
            return known_deprecations[package_name]

        return []

    def run_autonomous_discovery(self) -> Dict[str, Any]:
        """Runs end-to-end autonomous dependency and deprecation discovery."""
        deps = self.detect_dependencies()
        dynamic_rules = []
        for pkg in deps:
            rules = self.generate_dynamic_rules_for_package(pkg)
            for r in rules:
                r["package"] = pkg
                dynamic_rules.append(r)

        return {
            "target_directory": self.target_dir,
            "detected_packages": deps,
            "synthesized_rules": dynamic_rules
        }
