"""
ApiPatch Core Orchestration Engine
Integrates AST rule execution, dynamic LLM provider reasoning, AST safety validation,
and unified diff generation with safe file modification.
"""

import os
import sys
import shutil
import difflib
from typing import Dict, Any, List, Optional, Set
from apipatch.validator import CodeValidator, ValidationResult
from apipatch.rules import RulesEngine
from apipatch.providers.factory import ProviderFactory
from apipatch.auto_detector import AutoDeprecationDetector

# Reconfigure stdout/stderr for safe Unicode / Windows cp1256 encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def safe_print(text: str):
    """Safely prints to stdout without dying on encoding mismatches."""
    try:
        print(text)
    except UnicodeEncodeError:
        try:
            print(text.encode("ascii", errors="replace").decode("ascii"))
        except Exception:
            pass


class ApiPatchEngine:
    def __init__(
        self,
        provider_name: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        create_backup: bool = True
    ):
        self.provider = ProviderFactory.get_provider(
            provider_name=provider_name,
            api_key=api_key,
            model=model
        )
        self.create_backup = create_backup
        self.detector = AutoDeprecationDetector()

    def audit_code(
        self,
        file_path: str,
        code: str,
        detected_libraries: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Multi-tier dynamic audit:
        1. Fast deterministic RulesEngine (AST/regex)
        2. Dynamic LLM Provider (for ANY 3rd-party library)
        3. AST & Safety validation
        """
        file_name = os.path.basename(file_path)
        _, ext = os.path.splitext(file_path)

        # 1. Tier 1: Fast deterministic rules
        rule_res = RulesEngine.apply_rules(code, file_path=file_path)
        if rule_res["has_breaking_changes"]:
            # Validate rule output
            val = CodeValidator.validate(code, rule_res["refactored_code"], file_extension=ext)
            if val.is_valid:
                return rule_res

        # 2. Tier 2: Dynamic LLM provider audit (if provider configured)
        if self.provider:
            try:
                libs = detected_libraries or list(self.detector.extract_imports_from_file(file_path))
                llm_res = self.provider.audit_code(file_name, code, detected_libraries=libs)
                if llm_res.get("has_breaking_changes") and llm_res.get("refactored_code"):
                    refactored = llm_res["refactored_code"]
                    val = CodeValidator.validate(code, refactored, file_extension=ext)
                    if val.is_valid:
                        return llm_res
                    else:
                        safe_print(f"  {Colors.WARNING}[!] LLM refactored code failed validation ({val.error_message}). Falling back.{Colors.ENDC}")
            except Exception as e:
                safe_print(f"  {Colors.WARNING}[!] LLM provider call notice: {e}{Colors.ENDC}")

        # Fallback to rule result (even if empty)
        return rule_res

    def generate_diff(self, old_code: str, new_code: str, file_name: str) -> List[str]:
        """Generates unified diff lines between old and new code."""
        old_lines = old_code.splitlines(keepends=True)
        new_lines = new_code.splitlines(keepends=True)
        return list(difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{file_name}",
            tofile=f"b/{file_name}"
        ))

    def print_diff(self, diff: List[str]):
        """Prints colorized unified diff to stdout."""
        if not diff:
            safe_print("  (No changes needed)")
            return

        for line in diff:
            if line.startswith('+') and not line.startswith('+++'):
                safe_print(f"{Colors.OKGREEN}{line.rstrip()}{Colors.ENDC}")
            elif line.startswith('-') and not line.startswith('---'):
                safe_print(f"{Colors.FAIL}{line.rstrip()}{Colors.ENDC}")
            elif line.startswith('@'):
                safe_print(f"{Colors.OKCYAN}{line.rstrip()}{Colors.ENDC}")
            else:
                safe_print(f" {line.rstrip()}")

    def process_file(
        self,
        file_path: str,
        write_in_place: bool = False,
        detected_libraries: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Audits, refactors, previews diff, and optionally writes fixed code to disk."""
        file_path = os.path.abspath(file_path)
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            original_code = f.read()

        audit = self.audit_code(file_path, original_code, detected_libraries=detected_libraries)
        file_name = os.path.basename(file_path)

        if not audit["has_breaking_changes"]:
            safe_print(f"{Colors.OKGREEN}[V] {file_name}: Clean (No breaking changes detected){Colors.ENDC}")
            return {"file": file_path, "status": "clean", "issues": []}

        issues = audit["detected_issues"]
        safe_print(f"\n{Colors.FAIL}[!] [{len(issues)} DEPRECATION(S) DETECTED] {file_path}{Colors.ENDC}")
        for idx, issue in enumerate(issues, 1):
            safe_print(f"  {Colors.BOLD}#{idx} [{issue['library']}]:{Colors.ENDC} {issue['description']}")
            safe_print(f"     Deprecated:  {Colors.FAIL}{issue['deprecated_symbol']}{Colors.ENDC}")
            safe_print(f"     Replacement: {Colors.OKGREEN}{issue['replacement_symbol']}{Colors.ENDC}")

        refactored = audit.get("refactored_code", original_code)
        diff = self.generate_diff(original_code, refactored, file_name)

        safe_print(f"\n{Colors.OKBLUE}>> Refactored Diff Preview:{Colors.ENDC}")
        self.print_diff(diff)

        # Write in place if requested
        if write_in_place and refactored != original_code:
            if self.create_backup:
                backup_path = f"{file_path}.bak"
                shutil.copy2(file_path, backup_path)
                safe_print(f"  {Colors.OKCYAN}[*] Backup saved to: {backup_path}{Colors.ENDC}")

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(refactored)
            safe_print(f"  {Colors.OKGREEN}[V] Successfully updated {file_name} in place!{Colors.ENDC}")

        first_lib = issues[0]['library'] if issues else "API"
        safe_print(f"\n{Colors.HEADER}[PR Ready]:{Colors.ENDC} [ApiPatch] Migrate deprecated {first_lib} calls in {file_name}")

        return {
            "file": file_path,
            "status": "refactored" if write_in_place else "detected",
            "issues": issues,
            "refactored_code": refactored
        }

    def process_directory(
        self,
        target_dir: str,
        write_in_place: bool = False
    ) -> Dict[str, Any]:
        """Recursively audits all supported source files in target directory."""
        target_dir = os.path.abspath(target_dir)
        safe_print(f"{Colors.HEADER}{Colors.BOLD}=== ApiPatch: Autonomous AI Codebase Auditor ==={Colors.ENDC}")
        safe_print(f"Target Directory: {Colors.OKCYAN}{target_dir}{Colors.ENDC}")
        provider_name = self.provider.__class__.__name__ if self.provider else "Offline Rules Engine"
        safe_print(f"Active Engine:    {Colors.OKGREEN}{provider_name}{Colors.ENDC}\n")

        # Discover project-wide dependencies
        detector = AutoDeprecationDetector(target_dir)
        deps = detector.detect_dependencies()
        if deps:
            safe_print(f"[*] Detected {len(deps)} project dependencies: {', '.join(deps[:10])}{'...' if len(deps) > 10 else ''}\n")

        total_scanned = 0
        affected_files = 0
        results = []

        ignore_dirs = {".git", "node_modules", "venv", ".venv", "__pycache__", ".gemini", "dist", "build"}
        ignore_files = {"api_fixer_agent.py", "auto_detector.py", "github_proactive_hunter.py"}
        supported_exts = {".py", ".pyw", ".js", ".jsx", ".ts", ".tsx"}

        for root, dirs, files in os.walk(target_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                _, ext = os.path.splitext(file)
                if ext in supported_exts and file not in ignore_files:
                    total_scanned += 1
                    full_path = os.path.join(root, file)
                    res = self.process_file(
                        full_path,
                        write_in_place=write_in_place,
                        detected_libraries=deps
                    )
                    if res["status"] in {"detected", "refactored"}:
                        affected_files += 1
                    results.append(res)

        safe_print(f"\n[Audit Summary]: {total_scanned} files inspected, {affected_files} file(s) with deprecated APIs.")
        return {
            "total_scanned": total_scanned,
            "affected_files": affected_files,
            "results": results
        }
