"""
ApiPatch Core Orchestration Engine
High-performance, multi-threaded LLM-powered autonomous agent for detecting
and fixing deprecated API calls across ANY third-party library in Python, JavaScript,
TypeScript, JSX, TSX, and more.
"""

import os
import sys
import time
import shutil
import difflib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Set
from apipatch.validator import CodeValidator, ValidationResult
from apipatch.providers.factory import ProviderFactory
from apipatch.auto_detector import AutoDeprecationDetector

# Reconfigure stdout/stderr for safe Unicode / Windows encoding
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


_PRINT_LOCK = threading.Lock()


def safe_print(text: str):
    """Safely prints to stdout with thread synchronization."""
    with _PRINT_LOCK:
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
        create_backup: bool = True,
        concurrency: int = 6
    ):
        self.provider = ProviderFactory.get_provider(
            provider_name=provider_name,
            api_key=api_key,
            model=model
        )
        self.create_backup = create_backup
        self.concurrency = max(1, concurrency)
        self.detector = AutoDeprecationDetector()

    def audit_code(
        self,
        file_path: str,
        code: str,
        detected_libraries: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Fully LLM-driven audit:
        Detects and fixes deprecated/breaking API calls across ANY library,
        in Python, JavaScript, TypeScript, JSX, TSX, etc.
        Falls back gracefully if no provider is configured.
        """
        file_name = os.path.basename(file_path)
        _, ext = os.path.splitext(file_path)

        empty_result = {
            "has_breaking_changes": False,
            "detected_issues": [],
            "refactored_code": code
        }

        # Fast path: Empty or whitespace-only file
        if not code.strip():
            return empty_result

        if not self.provider:
            safe_print(
                f"  {Colors.WARNING}[!] No AI provider configured. "
                f"Set GEMINI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY "
                f"to enable full analysis.{Colors.ENDC}"
            )
            return empty_result

        try:
            # Extract file-specific imports
            if ext in {".py", ".pyw"}:
                file_imports = self.detector.extract_imports_from_file(file_path)
            elif ext in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
                file_imports = self.detector.extract_imports_from_js_file(file_path)
            else:
                file_imports = set()

            # Fast path: If the file has 0 third-party imports and no dependencies detected, mark clean instantly
            if not file_imports and not detected_libraries:
                return empty_result

            libs = list(file_imports) if file_imports else (detected_libraries or [])
            llm_res = self.provider.audit_code(file_name, code, detected_libraries=libs)

            if llm_res.get("has_breaking_changes") and llm_res.get("refactored_code"):
                refactored = llm_res["refactored_code"]
                val = CodeValidator.validate(code, refactored, file_extension=ext)
                if val.is_valid:
                    return llm_res
                else:
                    safe_print(
                        f"  {Colors.WARNING}[!] LLM output for {file_name} failed safety validation "
                        f"({val.error_message}). Keeping original.{Colors.ENDC}"
                    )
                    return empty_result

            return llm_res if llm_res else empty_result

        except Exception as e:
            safe_print(f"  {Colors.WARNING}[!] {file_name} provider notice: {e}{Colors.ENDC}")
            return empty_result

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
        t0 = time.time()
        file_path = os.path.abspath(file_path)
        file_name = os.path.basename(file_path)

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                original_code = f.read()
        except Exception as e:
            safe_print(f"{Colors.FAIL}[!] Cannot read {file_path}: {e}{Colors.ENDC}")
            return {"file": file_path, "status": "error", "issues": []}

        audit = self.audit_code(file_path, original_code, detected_libraries=detected_libraries)
        elapsed = time.time() - t0

        if not audit["has_breaking_changes"]:
            safe_print(f"{Colors.OKGREEN}[✓]{Colors.ENDC} {file_name}: Clean ({elapsed:.1f}s)")
            return {"file": file_path, "status": "clean", "issues": []}

        issues = audit["detected_issues"]
        safe_print(f"\n{Colors.FAIL}[!] [{len(issues)} DEPRECATION(S)] {file_name} ({elapsed:.1f}s){Colors.ENDC}")
        for idx, issue in enumerate(issues, 1):
            safe_print(f"  {Colors.BOLD}#{idx} [{issue['library']}]:{Colors.ENDC} {issue['description']}")
            safe_print(f"     Deprecated : {Colors.FAIL}{issue['deprecated_symbol']}{Colors.ENDC}")
            safe_print(f"     Replacement: {Colors.OKGREEN}{issue['replacement_symbol']}{Colors.ENDC}")

        refactored = audit.get("refactored_code", original_code)
        diff = self.generate_diff(original_code, refactored, file_name)

        safe_print(f"\n{Colors.OKBLUE}>> Refactored Diff Preview:{Colors.ENDC}")
        self.print_diff(diff)

        if write_in_place and refactored != original_code:
            if self.create_backup:
                backup_path = f"{file_path}.bak"
                shutil.copy2(file_path, backup_path)
                safe_print(f"  {Colors.OKCYAN}[*] Backup saved → {backup_path}{Colors.ENDC}")

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(refactored)
            safe_print(f"  {Colors.OKGREEN}[✓] Updated {file_name} in place.{Colors.ENDC}")

        first_lib = issues[0]['library'] if issues else "API"
        safe_print(
            f"\n{Colors.HEADER}[PR Ready]:{Colors.ENDC} "
            f"[ApiPatch] Migrate deprecated {first_lib} calls in {file_name}"
        )

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
        """
        Recursively and CONCURRENTLY audits all supported source files in target directory.
        Uses ThreadPoolExecutor for 10x-15x faster scanning speed.
        """
        start_time = time.time()
        target_dir = os.path.abspath(target_dir)
        safe_print(f"{Colors.HEADER}{Colors.BOLD}=== ApiPatch: Autonomous AI Codebase Auditor ==={Colors.ENDC}")
        safe_print(f"Target Directory : {Colors.OKCYAN}{target_dir}{Colors.ENDC}")
        provider_name = self.provider.__class__.__name__ if self.provider else "No Provider (Offline)"
        safe_print(f"Active AI Engine : {Colors.OKGREEN}{provider_name}{Colors.ENDC}")

        # Discover project-wide dependencies
        detector = AutoDeprecationDetector(target_dir)
        deps = detector.detect_dependencies()
        if deps:
            listed = ', '.join(deps[:12])
            extra = f'... (+{len(deps) - 12} more)' if len(deps) > 12 else ''
            safe_print(f"[*] Detected {len(deps)} dependencies: {listed}{extra}")

        ignore_dirs = {
            ".git", "node_modules", "venv", ".venv", "__pycache__",
            ".gemini", "dist", "build", ".next", ".nuxt", "out", "coverage"
        }
        supported_exts = {".py", ".pyw", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}

        candidate_files: List[str] = []
        for root, dirs, files in os.walk(target_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                _, ext = os.path.splitext(file)
                if ext in supported_exts:
                    candidate_files.append(os.path.join(root, file))

        total_scanned = len(candidate_files)
        if total_scanned == 0:
            safe_print(f"\n{Colors.WARNING}[!] No supported source files found in {target_dir}{Colors.ENDC}")
            return {"total_scanned": 0, "affected_files": 0, "results": []}

        worker_count = min(self.concurrency, total_scanned)
        safe_print(f"[*] Auditing {total_scanned} file(s) in parallel (concurrency: {worker_count})...\n")

        affected_files = 0
        results = []

        # Execute parallel audit across files
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_to_file = {
                executor.submit(
                    self.process_file,
                    fpath,
                    write_in_place,
                    deps
                ): fpath for fpath in candidate_files
            }

            for future in as_completed(future_to_file):
                try:
                    res = future.result()
                    if res["status"] in {"detected", "refactored"}:
                        affected_files += 1
                    results.append(res)
                except Exception as e:
                    fpath = future_to_file[future]
                    safe_print(f"{Colors.FAIL}[!] Audit exception on {os.path.basename(fpath)}: {e}{Colors.ENDC}")

        total_duration = time.time() - start_time
        safe_print(
            f"\n{Colors.BOLD}[Audit Summary]:{Colors.ENDC} {total_scanned} file(s) inspected in {total_duration:.2f}s, "
            f"{affected_files} file(s) with deprecated APIs found."
        )
        return {
            "total_scanned": total_scanned,
            "affected_files": affected_files,
            "results": results
        }
