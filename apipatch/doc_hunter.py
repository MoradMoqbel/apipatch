"""
ApiPatch Live Documentation & Official Grounding Hunter (DocHunter)
Dynamically fetches verified package metadata, official documentation URLs,
and changelog summaries from PyPI and npm registries to ground the LLM
with authoritative release information and eliminate false positives.
"""

import json
import urllib.request
import urllib.error
import re
from typing import Dict, Any, Optional, List, Set


# In-memory cache to prevent redundant HTTP requests across multi-file audits
_PACKAGE_METADATA_CACHE: Dict[str, Dict[str, Any]] = {}


class DocHunter:
    """
    Autonomous Package Inspector and Live Documentation Hunter.
    Resolves official documentation, repositories, and release status
    for any third-party library in Python or JavaScript/TypeScript.
    """

    @classmethod
    def fetch_pypi_metadata(cls, pkg_name: str, timeout: float = 3.0) -> Optional[Dict[str, Any]]:
        """
        Fetches official package metadata from the official PyPI JSON API.
        Returns package summary, latest version, documentation URL, and repo links.
        """
        clean_name = pkg_name.strip().lower()
        if not clean_name:
            return None

        # Check in-memory cache first
        cache_key = f"pypi:{clean_name}"
        if cache_key in _PACKAGE_METADATA_CACHE:
            return _PACKAGE_METADATA_CACHE[cache_key]

        url = f"https://pypi.org/pypi/{clean_name}/json"
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
                    "name": info.get("name", clean_name),
                    "version": info.get("version", "unknown"),
                    "summary": info.get("summary", ""),
                    "documentation_url": doc_url,
                    "repository_url": repo_url,
                    "changelog_url": changelog_url,
                    "is_active": True,
                }
                _PACKAGE_METADATA_CACHE[cache_key] = result
                return result

        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Not found on PyPI
                _PACKAGE_METADATA_CACHE[cache_key] = {}
                return None
        except Exception:
            pass

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
                    # Truncate summary if too long
                    short_sum = summary[:120] + "..." if len(summary) > 120 else summary
                    line += f" {short_sum}."
                if doc or repo:
                    target_url = doc or repo
                    line += f" [Official Docs/Source: {target_url}]"
                grounding_lines.append(line)

        if not grounding_lines:
            return ""

        return (
            "\n[Authoritative Live Package Grounding & Documentation]\n"
            + "\n".join(grounding_lines)
            + "\nCRITICAL: These packages are verified active third-party dependencies. "
            "Do NOT replace them with competing frameworks (e.g. do not replace agno with LangChain), "
            "and only refactor methods that are officially deprecated.\n"
        )
