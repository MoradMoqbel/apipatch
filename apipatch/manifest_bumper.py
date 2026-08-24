"""
ApiPatch Manifest Version Bumper
Automatically bumps package version specifications in requirements.txt,
pyproject.toml, and package.json to match modernized API code logic.
"""

import os
import re
import json
from typing import Dict, Set, Tuple, Optional, List, Any


# Standard minimum modern version constraints for major migrated packages
MODERN_VERSION_TARGETS: Dict[str, str] = {
    # Python ecosystem
    "pydantic": ">=2.0.0",
    "openai": ">=1.0.0",
    "google-genai": ">=0.1.0",
    "google.genai": ">=0.1.0",
    "google-generativeai": ">=0.8.0",
    "langchain": ">=0.2.0",
    "langchain-core": ">=0.2.0",
    "langchain-openai": ">=0.1.0",
    "langchain-community": ">=0.2.0",
    "stripe": ">=10.0.0",
    "supabase": ">=2.0.0",
    "fastapi": ">=0.110.0",
    "anthropic": ">=0.25.0",
    "pydantic-settings": ">=2.0.0",
    "sqlalchemy": ">=2.0.0",
    # JavaScript / TypeScript ecosystem
    "@supabase/supabase-js": "^2.0.0",
    "next": "^14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.0"
}


class ManifestBumper:
    """
    Inspects and updates package manifest files (requirements.txt, pyproject.toml, package.json)
    to align declared dependency versions with the refactored code.
    """

    @classmethod
    def get_target_constraint(cls, lib_name: str) -> Optional[str]:
        """Returns the recommended modern version constraint for a library."""
        clean = lib_name.strip().lower()
        if clean in MODERN_VERSION_TARGETS:
            return MODERN_VERSION_TARGETS[clean]
        hyphenated = clean.replace("_", "-")
        if hyphenated in MODERN_VERSION_TARGETS:
            return MODERN_VERSION_TARGETS[hyphenated]
        underscored = clean.replace("-", "_")
        if underscored in MODERN_VERSION_TARGETS:
            return MODERN_VERSION_TARGETS[underscored]
        return None

    @classmethod
    def bump_requirements_txt(cls, content: str, modernized_libraries: Set[str]) -> Tuple[str, bool]:
        """
        Updates version requirements in requirements.txt content for modernized libraries.
        Returns (new_content, changed).
        """
        if not content or not modernized_libraries:
            return content, False

        lines = content.splitlines(keepends=True)
        new_lines: List[str] = []
        changed = False

        normalized_libs = {lib.strip().lower() for lib in modernized_libraries if lib}
        normalized_libs.update({lib.replace("_", "-") for lib in normalized_libs})
        normalized_libs.update({lib.replace("-", "_") for lib in normalized_libs})

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("-"):
                new_lines.append(line)
                continue

            # Extract pkg name (before any version operators)
            parts = re.split(r"([><=~;!@\[].*)", stripped, maxsplit=1)
            pkg_name = parts[0].strip()
            pkg_lower = pkg_name.lower()

            if pkg_lower in normalized_libs or pkg_lower.replace("_", "-") in normalized_libs or pkg_lower.replace("-", "_") in normalized_libs:
                target_ver = cls.get_target_constraint(pkg_lower)
                if target_ver:
                    # Check existing constraint
                    existing_constraint = parts[1].strip() if len(parts) > 1 else ""
                    new_line_content = f"{pkg_name}{target_ver}"
                    ending = "\n" if line.endswith("\n") else ""
                    if existing_constraint != target_ver:
                        new_lines.append(f"{new_line_content}{ending}")
                        changed = True
                        continue

            new_lines.append(line)

        return "".join(new_lines), changed

    @classmethod
    def bump_package_json(cls, content: str, modernized_libraries: Set[str]) -> Tuple[str, bool]:
        """
        Updates version dependencies in package.json for modernized libraries.
        Returns (new_content, changed).
        """
        if not content or not modernized_libraries:
            return content, False

        try:
            data = json.loads(content)
        except Exception:
            return content, False

        changed = False
        normalized_libs = {lib.strip().lower() for lib in modernized_libraries if lib}

        for section in ("dependencies", "devDependencies"):
            if section in data and isinstance(data[section], dict):
                for pkg in list(data[section].keys()):
                    pkg_lower = pkg.lower()
                    if pkg_lower in normalized_libs:
                        target = cls.get_target_constraint(pkg_lower)
                        if target:
                            clean_target = target if target.startswith(("^", "~")) else f"^{target.lstrip('>=~=')}"
                            if data[section][pkg] != clean_target:
                                data[section][pkg] = clean_target
                                changed = True

        if changed:
            return json.dumps(data, indent=2) + "\n", True

        return content, False

    @classmethod
    def bump_pyproject_toml(cls, content: str, modernized_libraries: Set[str]) -> Tuple[str, bool]:
        """
        Updates dependencies list in pyproject.toml for modernized libraries.
        Returns (new_content, changed).
        """
        if not content or not modernized_libraries:
            return content, False

        lines = content.splitlines(keepends=True)
        new_lines: List[str] = []
        changed = False

        normalized_libs = {lib.strip().lower() for lib in modernized_libraries if lib}
        normalized_libs.update({lib.replace("_", "-") for lib in normalized_libs})

        for line in lines:
            for lib in normalized_libs:
                target_ver = cls.get_target_constraint(lib)
                if not target_ver:
                    continue

                pattern = re.compile(rf'("|\'){re.escape(lib)}([><=~;!@\[].*?)?("|\')', re.IGNORECASE)
                if pattern.search(line):
                    quote = pattern.search(line).group(1)
                    replacement = f"{quote}{lib}{target_ver}{quote}"
                    new_line = pattern.sub(replacement, line)
                    if new_line != line:
                        line = new_line
                        changed = True
                        break

            new_lines.append(line)

        return "".join(new_lines), changed

    @classmethod
    def bump_local_manifests(
        cls,
        target_dir: str,
        modernized_libraries: Set[str],
        write: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Scans target_dir for requirements.txt, pyproject.toml, package.json
        and bumps them if needed. Returns list of modified manifest records.
        """
        target_dir = os.path.abspath(target_dir)
        records = []

        # 1. requirements.txt
        req_path = os.path.join(target_dir, "requirements.txt")
        if os.path.isfile(req_path):
            try:
                with open(req_path, "r", encoding="utf-8") as f:
                    content = f.read()
                new_c, changed = cls.bump_requirements_txt(content, modernized_libraries)
                if changed:
                    if write:
                        with open(req_path, "w", encoding="utf-8") as f:
                            f.write(new_c)
                    records.append({"file": req_path, "manifest": "requirements.txt", "content": new_c})
            except Exception:
                pass

        # 2. pyproject.toml
        pyproj_path = os.path.join(target_dir, "pyproject.toml")
        if os.path.isfile(pyproj_path):
            try:
                with open(pyproj_path, "r", encoding="utf-8") as f:
                    content = f.read()
                new_c, changed = cls.bump_pyproject_toml(content, modernized_libraries)
                if changed:
                    if write:
                        with open(pyproj_path, "w", encoding="utf-8") as f:
                            f.write(new_c)
                    records.append({"file": pyproj_path, "manifest": "pyproject.toml", "content": new_c})
            except Exception:
                pass

        # 3. package.json
        pkg_path = os.path.join(target_dir, "package.json")
        if os.path.isfile(pkg_path):
            try:
                with open(pkg_path, "r", encoding="utf-8") as f:
                    content = f.read()
                new_c, changed = cls.bump_package_json(content, modernized_libraries)
                if changed:
                    if write:
                        with open(pkg_path, "w", encoding="utf-8") as f:
                            f.write(new_c)
                    records.append({"file": pkg_path, "manifest": "package.json", "content": new_c})
            except Exception:
                pass

        return records
