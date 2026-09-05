"""
ApiPatch Live Documentation & Official Grounding Hunter (DocHunter)
Dynamically fetches verified package metadata, official documentation URLs,
and changelog summaries from PyPI, npm, and GitHub registries to ground the LLM
with authoritative real-time release information and eliminate false positives.
"""

import json
import urllib.request
import urllib.error
import re
import sys
from typing import Dict, Any, Optional, List, Set


# In-memory cache to prevent redundant HTTP requests across multi-file audits
_PACKAGE_METADATA_CACHE: Dict[str, Dict[str, Any]] = {}
_GITHUB_RELEASE_CACHE: Dict[str, str] = {}
_LLMS_TXT_CACHE: Dict[str, str] = {}
_CHANGELOG_CACHE: Dict[str, str] = {}


class DocHunter:
    """
    Autonomous Package Inspector and Live Documentation Hunter.
    Resolves official documentation, repositories, and release status
    for any third-party library dynamically without hardcoded static rules.
    """

    @classmethod
    def fetch_llms_txt(cls, doc_url: str, timeout: float = 2.5) -> str:
        """
        Discovers and fetches official /llms.txt or /llms-full.txt from documentation websites.
        Returns concise AI-ready documentation markdown if available.
        """
        if not doc_url or not doc_url.startswith("http"):
            return ""

        from urllib.parse import urlparse
        try:
            parsed = urlparse(doc_url)
            if not parsed.netloc:
                return ""
            base_origin = f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            return ""

        cache_key = base_origin.lower()
        if cache_key in _LLMS_TXT_CACHE:
            return _LLMS_TXT_CACHE[cache_key]

        candidate_urls = [
            f"{base_origin}/llms.txt",
            f"{base_origin}/llms-full.txt",
        ]

        for u in candidate_urls:
            req = urllib.request.Request(
                u,
                headers={"User-Agent": "ApiPatch-DocHunter/1.0 (llms.txt scanner)"}
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    content_type = response.headers.get("Content-Type", "").lower()
                    if "html" in content_type:
                        continue
                    raw_text = response.read().decode("utf-8", errors="ignore")
                    if raw_text and ("# " in raw_text or "docs" in raw_text.lower() or "api" in raw_text.lower()):
                        # Extract concise overview up to 1000 characters
                        clean = "\n".join([line for line in raw_text.splitlines() if line.strip() and not line.startswith("<!--")])[:1000]
                        _LLMS_TXT_CACHE[cache_key] = clean
                        return clean
            except Exception:
                continue

        _LLMS_TXT_CACHE[cache_key] = ""
        return ""

    @classmethod
    def fetch_github_changelog(cls, repo_url: str, timeout: float = 2.5) -> str:
        """
        Fetches raw CHANGELOG.md / HISTORY.md directly from GitHub to capture breaking change notes.
        """
        if not repo_url or "github.com" not in repo_url:
            return ""

        m = re.search(r"github\.com/([^/]+)/([^/#?]+)", repo_url)
        if not m:
            return ""

        owner, repo = m.group(1), m.group(2).replace(".git", "")
        cache_key = f"{owner}/{repo}/changelog".lower()
        if cache_key in _CHANGELOG_CACHE:
            return _CHANGELOG_CACHE[cache_key]

        candidates = [
            f"https://raw.githubusercontent.com/{owner}/{repo}/main/CHANGELOG.md",
            f"https://raw.githubusercontent.com/{owner}/{repo}/master/CHANGELOG.md",
            f"https://raw.githubusercontent.com/{owner}/{repo}/main/HISTORY.md",
            f"https://raw.githubusercontent.com/{owner}/{repo}/master/HISTORY.md",
        ]

        for url in candidates:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "ApiPatch-DocHunter/1.0"}
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    text = response.read().decode("utf-8", errors="ignore")
                    if text and len(text) > 50:
                        lines = [l for l in text.splitlines() if l.strip()]
                        # Grab top 15 lines of latest release
                        snippet = "\n".join(lines[:15])[:600]
                        _CHANGELOG_CACHE[cache_key] = snippet
                        return snippet
            except Exception:
                continue

        _CHANGELOG_CACHE[cache_key] = ""
        return ""

    @classmethod
    def fetch_github_release_summary(cls, repo_url: str, timeout: float = 3.0) -> str:
        """
        Fetches the latest official release notes and changelog from GitHub Releases.
        """
        if not repo_url or "github.com" not in repo_url:
            return ""

        # Extract owner/repo
        m = re.search(r"github\.com/([^/]+)/([^/#?]+)", repo_url)
        if not m:
            return ""

        owner, repo = m.group(1), m.group(2).replace(".git", "")
        cache_key = f"{owner}/{repo}".lower()
        if cache_key in _GITHUB_RELEASE_CACHE:
            return _GITHUB_RELEASE_CACHE[cache_key]

        from apipatch.github_client import resolve_github_token
        token = resolve_github_token()
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ApiPatch-DocHunter/1.0"
        }
        if token:
            headers["Authorization"] = f"token {token}"

        api_url = f"https://api.github.com/repos/{owner}/{repo}/releases?per_page=1"
        req = urllib.request.Request(api_url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                releases = json.loads(response.read().decode("utf-8"))
                if releases and isinstance(releases, list):
                    rel = releases[0]
                    tag = rel.get("tag_name", "")
                    body = rel.get("body", "") or ""
                    # Keep first 200 characters of release notes
                    short_body = body.split("\n")[0][:150] if body else ""
                    res = f"Latest Release {tag}: {short_body}"
                    _GITHUB_RELEASE_CACHE[cache_key] = res
                    return res
        except Exception:
            pass

        return ""

    @classmethod
    def get_package_grounding(cls, pkg_name: str) -> Optional[Dict[str, Any]]:
        """
        Tries PyPI first, then npm. Returns unified metadata.
        """
        meta = cls.fetch_pypi_metadata(pkg_name)
        if meta and meta.get("name"):
            return meta
        
        meta_npm = cls.fetch_npm_metadata(pkg_name)
        if meta_npm and meta_npm.get("name"):
            return meta_npm

        return None

    @classmethod
    def build_grounded_context(cls, libraries: List[str]) -> str:
        """
        Generates an authoritative grounding section for the LLM prompt
        containing verified package identities, latest versions, official URLs,
        llms.txt index, and latest release changelogs.
        """
        if not libraries:
            return ""

        grounding_lines: List[str] = []
        extra_docs_sections: List[str] = []

        for lib in libraries:
            clean_lib = lib.strip()
            if not clean_lib or clean_lib.startswith(".") or clean_lib.startswith("/"):
                continue

            meta = cls.get_package_grounding(clean_lib)
            if meta and meta.get("name"):
                name = meta["name"]
                ver = meta.get("version", "")
                summary = meta.get("summary", "")
                doc = meta.get("documentation_url", "")
                repo = meta.get("repository_url", "")

                line = f"  • Package '{name}' (Latest Official Release: v{ver}):"
                if summary:
                    short_sum = summary[:120] + "..." if len(summary) > 120 else summary
                    line += f" {short_sum}."
                if doc or repo:
                    target_url = doc or repo
                    line += f" [Official Docs/Source: {target_url}]"

                # Check latest GitHub release notes live
                if repo:
                    rel_summary = cls.fetch_github_release_summary(repo)
                    if rel_summary:
                        line += f" ({rel_summary})"

                grounding_lines.append(line)

                # Attempt live JIT llms.txt retrieval
                if doc:
                    llms_info = cls.fetch_llms_txt(doc)
                    if llms_info:
                        extra_docs_sections.append(f"--- Live Documentation Summary for {name} ({doc}/llms.txt) ---\n{llms_info}")
                
                # If no llms.txt, try raw GitHub changelog snippet
                elif repo:
                    ch_info = cls.fetch_github_changelog(repo)
                    if ch_info:
                        extra_docs_sections.append(f"--- Latest Changelog Snippet for {name} ---\n{ch_info}")

        if not grounding_lines:
            return ""

        result = (
            "\n[Authoritative Live Package Grounding & Documentation]\n"
            + "\n".join(grounding_lines)
            + "\nCRITICAL: These packages are verified active third-party dependencies. "
            "Do NOT replace them with competing frameworks (e.g. do not replace agno with LangChain), "
            "do NOT downgrade modern model names (e.g. do NOT change Claude 4.5/3.7, Gemini 3/2.5 to older models), "
            "do NOT downgrade modern clients (e.g. keep cohere.ClientV2 intact), "
            "and only refactor methods that are officially deprecated.\n"
        )

        if extra_docs_sections:
            result += "\n" + "\n\n".join(extra_docs_sections[:2]) + "\n"

        return result

    @classmethod
    def fetch_pypi_metadata(cls, pkg_name: str, timeout: float = 3.0) -> Optional[Dict[str, Any]]:
        """
        Fetches official package metadata from the official PyPI JSON API
        using smart hierarchical resolution (raw, hyphenated, dot-split).
        """
        clean_name = pkg_name.strip().lower()
        if not clean_name:
            return None

        # Check in-memory cache first
        cache_key = f"pypi:{clean_name}"
        if cache_key in _PACKAGE_METADATA_CACHE:
            return _PACKAGE_METADATA_CACHE[cache_key]

        # Generate candidates: [clean_name, hyphenated, underscore, dot-prefixes]
        candidates = [clean_name, clean_name.replace(".", "-"), clean_name.replace("_", "-")]
        if "." in clean_name:
            parts = clean_name.split(".")
            if len(parts) >= 2:
                candidates.append(f"{parts[0]}-{parts[1]}")
            candidates.append(parts[0])

        seen = set()
        for cand in candidates:
            if cand in seen:
                continue
            seen.add(cand)

            url = f"https://pypi.org/pypi/{cand}/json"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "ApiPatch-DocHunter/1.0 (https://github.com/MoradMoqbel/apipatch)"}
            )

            try:
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    info = data.get("info", {})
                    
                    project_urls = info.get("project_urls") or {}
                    doc_url = (
                        project_urls.get("Documentation")
                        or project_urls.get("Docs")
                        or project_urls.get("Changelog")
                        or info.get("home_page")
                        or ""
                    )
                    repo_url = (
                        project_urls.get("Source")
                        or project_urls.get("Repository")
                        or project_urls.get("GitHub")
                        or info.get("home_page")
                        or ""
                    )
                    changelog_url = project_urls.get("Changelog") or project_urls.get("Changes") or ""

                    result = {
                        "name": info.get("name", cand),
                        "version": info.get("version", "unknown"),
                        "summary": info.get("summary", ""),
                        "documentation_url": doc_url,
                        "repository_url": repo_url,
                        "changelog_url": changelog_url,
                        "is_active": True,
                    }
                    _PACKAGE_METADATA_CACHE[cache_key] = result
                    return result
            except Exception:
                continue

        _PACKAGE_METADATA_CACHE[cache_key] = {}
        return None

    @classmethod
    def fetch_npm_metadata(cls, pkg_name: str, timeout: float = 3.0) -> Optional[Dict[str, Any]]:
        """
        Fetches official package metadata from the npm registry.
        """
        clean_name = pkg_name.strip().lower()
        if not clean_name:
            return None

        cache_key = f"npm:{clean_name}"
        if cache_key in _PACKAGE_METADATA_CACHE:
            return _PACKAGE_METADATA_CACHE[cache_key]

        url = f"https://registry.npmjs.org/{clean_name}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ApiPatch-DocHunter/1.0"}
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
                dist_tags = data.get("dist-tags", {})
                latest_ver = dist_tags.get("latest", "unknown")
                summary = data.get("description", "")
                homepage = data.get("homepage", "")
                repo_dict = data.get("repository", {})
                repo_url = repo_dict.get("url", "") if isinstance(repo_dict, dict) else str(repo_dict)

                result = {
                    "name": clean_name,
                    "version": latest_ver,
                    "summary": summary,
                    "documentation_url": homepage,
                    "repository_url": repo_url,
                    "is_active": True,
                }
                _PACKAGE_METADATA_CACHE[cache_key] = result
                return result
        except Exception:
            pass

        return None

    @classmethod
    def fetch_github_release_summary(cls, repo_url: str, timeout: float = 3.0) -> str:
        """
        Fetches the latest official release notes and changelog from GitHub Releases.
        """
        if not repo_url or "github.com" not in repo_url:
            return ""

        # Extract owner/repo
        m = re.search(r"github\.com/([^/]+)/([^/#?]+)", repo_url)
        if not m:
            return ""

        owner, repo = m.group(1), m.group(2).replace(".git", "")
        cache_key = f"{owner}/{repo}".lower()
        if cache_key in _GITHUB_RELEASE_CACHE:
            return _GITHUB_RELEASE_CACHE[cache_key]

        from apipatch.github_client import resolve_github_token
        token = resolve_github_token()
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ApiPatch-DocHunter/1.0"
        }
        if token:
            headers["Authorization"] = f"token {token}"

        api_url = f"https://api.github.com/repos/{owner}/{repo}/releases?per_page=1"
        req = urllib.request.Request(api_url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                releases = json.loads(response.read().decode("utf-8"))
                if releases and isinstance(releases, list):
                    rel = releases[0]
                    tag = rel.get("tag_name", "")
                    body = rel.get("body", "") or ""
                    # Keep first 200 characters of release notes
                    short_body = body.split("\n")[0][:150] if body else ""
                    res = f"Latest Release {tag}: {short_body}"
                    _GITHUB_RELEASE_CACHE[cache_key] = res
                    return res
        except Exception:
            pass

        return ""

    @classmethod
    def get_package_grounding(cls, pkg_name: str) -> Optional[Dict[str, Any]]:
        """
        Tries PyPI first, then npm. Returns unified metadata.
        """
        meta = cls.fetch_pypi_metadata(pkg_name)
        if meta and meta.get("name"):
            return meta
        
        meta_npm = cls.fetch_npm_metadata(pkg_name)
        if meta_npm and meta_npm.get("name"):
            return meta_npm

        return None

    @classmethod
    def build_grounded_context(cls, libraries: List[str]) -> str:
        """
        Generates an authoritative grounding section for the LLM prompt
        containing verified package identities, latest versions, and official URLs.
        """
        if not libraries:
            return ""

        grounding_lines: List[str] = []
        for lib in libraries:
            clean_lib = lib.strip()
            if not clean_lib or clean_lib.startswith(".") or clean_lib.startswith("/"):
                continue

            meta = cls.get_package_grounding(clean_lib)
            if meta and meta.get("name"):
                name = meta["name"]
                ver = meta.get("version", "")
                summary = meta.get("summary", "")
                doc = meta.get("documentation_url", "")
                repo = meta.get("repository_url", "")

                line = f"  • Package '{name}' (Latest Official Release: v{ver}):"
                if summary:
                    short_sum = summary[:120] + "..." if len(summary) > 120 else summary
                    line += f" {short_sum}."
                if doc or repo:
                    target_url = doc or repo
                    line += f" [Official Docs/Source: {target_url}]"

                # Check latest GitHub release notes live
                if repo:
                    rel_summary = cls.fetch_github_release_summary(repo)
                    if rel_summary:
                        line += f" ({rel_summary})"

                grounding_lines.append(line)

        if not grounding_lines:
            return ""

        return (
            "\n[Authoritative Live Package Grounding & Documentation]\n"
            + "\n".join(grounding_lines)
            + "\nCRITICAL: These packages are verified active third-party dependencies. "
            "Do NOT replace them with competing frameworks (e.g. do not replace agno with LangChain), "
            "do NOT downgrade modern model names (e.g. do NOT change Gemini 3 or 2.5 to 1.5), "
            "and only refactor methods that are officially deprecated.\n"
        )

    # ── Autonomous Dynamic Registry & Import Fact-Checking ──────────────────────
    PYTHON_STDLIB_MODULES: Set[str] = (
        set(getattr(sys, "stdlib_module_names", set()))
        if hasattr(sys, "stdlib_module_names")
        else {
            "abc", "argparse", "array", "ast", "asyncio", "base64", "bisect", "builtins",
            "calendar", "collections", "concurrent", "configparser", "contextlib", "copy",
            "csv", "ctypes", "dataclasses", "datetime", "decimal", "difflib", "dis",
            "email", "enum", "errno", "exceptions", "faulthandler", "filecmp", "fileinput",
            "fnmatch", "fractions", "functools", "gc", "getopt", "getpass", "glob",
            "gzip", "hashlib", "heapq", "hmac", "html", "http", "imaplib", "imghdr",
            "importlib", "inspect", "io", "ipaddress", "itertools", "json", "keyword",
            "linecache", "locale", "logging", "lzma", "math", "mimetypes", "mmap",
            "modulefinder", "multiprocessing", "netrc", "numbers", "operator", "os",
            "pathlib", "pickle", "pkgutil", "platform", "plistlib", "poplib", "posix",
            "pprint", "profile", "pstats", "pty", "pwd", "py_compile", "pyclbr", "pydoc",
            "queue", "quopri", "random", "re", "readline", "reprlib", "resource", "rlcompleter",
            "sched", "secrets", "select", "selectors", "shelve", "shlex", "shutil", "signal",
            "site", "smtpd", "smtplib", "sndhdr", "socket", "socketserver", "sqlite3", "ssl",
            "stat", "statistics", "string", "stringprep", "struct", "subprocess", "symtable",
            "sys", "sysconfig", "tabnanny", "tarfile", "telnetlib", "tempfile", "termios",
            "test", "textwrap", "threading", "time", "timeit", "tkinter", "token", "tokenize",
            "trace", "traceback", "tracemalloc", "tty", "turtle", "turtledemo", "types",
            "typing", "unicodedata", "unittest", "urllib", "uu", "uuid", "venv", "warnings",
            "wave", "weakref", "webbrowser", "winreg", "winsound", "wsgiref", "xdrlib",
            "xml", "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib", "_thread", "typing_extensions"
        }
    )

    # Common well-known top-level namespace mappings (module_import -> pypi_package)
    KNOWN_IMPORT_TO_PACKAGE_MAP: Dict[str, str] = {
        "dotenv": "python-dotenv",
        "yaml": "pyyaml",
        "PIL": "pillow",
        "cv2": "opencv-python",
        "bs4": "beautifulsoup4",
        "sklearn": "scikit-learn",
        "dateutil": "python-dateutil",
        "jwt": "pyjwt",
        "serial": "pyserial",
        "magic": "python-magic",
        "fitz": "pymupdf",
        "docx": "python-docx",
        "pptx": "python-pptx",
        "google.genai": "google-genai",
        "google.adk": "google-adk",
        "google.generativeai": "google-generativeai",
        "google.cloud": "google-cloud-core",
        "azure.storage": "azure-storage-blob",
        "azure.identity": "azure-identity",
    }

    # Known invalid / hallucinated root import names (e.g. underscore hallucinations for dotted or hyphens)
    KNOWN_HALLUCINATED_ROOT_MODULES: Set[str] = {
        "google_generativeai", "google_genai", "langchain_openai_client", "openai_client"
    }

    @classmethod
    def is_valid_registry_import(cls, module_name: str, ecosystem: str = "python", timeout: float = 2.0) -> bool:
        """
        Dynamically verifies whether an imported root or sub-module exists
        in the standard library, known package mappings, or is a registered PyPI/npm package.
        Returns False if the module name is an ungrounded hallucination.
        """
        clean = module_name.strip()
        if not clean:
            return True

        # Extract root module
        root = clean.split(".")[0]

        # 1. Reject explicit hallucinated root modules
        if root in cls.KNOWN_HALLUCINATED_ROOT_MODULES:
            return False

        # 2. Check Standard Library
        if ecosystem == "python" and (root in cls.PYTHON_STDLIB_MODULES or clean in cls.PYTHON_STDLIB_MODULES):
            return True

        # 3. Check known valid mappings and recognized enterprise namespace roots
        recognized_namespace_roots = {
            "google", "azure", "aws", "langchain", "llama_index", "openai",
            "pydantic", "anthropic", "stripe", "fastapi", "flask", "django", "pytest"
        }
        if root in recognized_namespace_roots:
            return True

        if clean in cls.KNOWN_IMPORT_TO_PACKAGE_MAP or root in cls.KNOWN_IMPORT_TO_PACKAGE_MAP:
            return True

        # 4. Check locally installed spec
        if ecosystem == "python":
            try:
                import importlib.util
                if importlib.util.find_spec(root) is not None or importlib.util.find_spec(clean) is not None:
                    return True
            except Exception:
                pass

        # 5. Check PyPI / npm Registry
        cache_key = f"valid_import:{ecosystem}:{clean}"
        if cache_key in _PACKAGE_METADATA_CACHE:
            return bool(_PACKAGE_METADATA_CACHE[cache_key].get("exists", False))

        # Check candidate package names
        candidates = [root, clean, root.replace("_", "-"), clean.replace("_", "-")]
        if "." in clean:
            dotted_parts = clean.split(".")
            candidates.append(f"{dotted_parts[0]}-{dotted_parts[1]}")

        for cand in candidates:
            if ecosystem == "python":
                meta = cls.fetch_pypi_metadata(cand, timeout=timeout)
                if meta and meta.get("name"):
                    _PACKAGE_METADATA_CACHE[cache_key] = {"exists": True}
                    return True
            else:
                meta = cls.fetch_npm_metadata(cand, timeout=timeout)
                if meta and meta.get("name"):
                    _PACKAGE_METADATA_CACHE[cache_key] = {"exists": True}
                    return True

        # If not found in standard library, mappings, or PyPI -> module does not exist
        _PACKAGE_METADATA_CACHE[cache_key] = {"exists": False}
        return False

    @classmethod
    def verify_module_symbol(cls, module_path: str, symbol_name: str) -> bool:
        """
        Dynamically verifies whether a specific symbol/attribute exists within a module namespace.
        Prevents hallucinated cross-package attribute lookups (e.g. types.ToolContext in google.genai.types).
        """
        clean_mod = module_path.strip()
        clean_sym = symbol_name.strip()

        # Specific known cross-framework symbol mixups:
        # ToolContext belongs to google.adk.tools, NOT google.genai.types
        if clean_mod.endswith("google.genai.types") or clean_mod == "google.genai.types":
            if clean_sym in {"ToolContext", "SessionContext", "AgentContext", "InMemorySessionService"}:
                return False

        # Try dynamic runtime inspection if installed in local env
        try:
            import importlib
            mod = importlib.import_module(clean_mod)
            return hasattr(mod, clean_sym)
        except Exception:
            # If not locally installed, accept standard symbols unless explicitly invalid
            return True


