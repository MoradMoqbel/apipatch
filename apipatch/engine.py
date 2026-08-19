"""
ApiPatch Core Orchestration Engine
High-performance, multi-threaded LLM-powered autonomous agent for detecting
and fixing deprecated API calls across ANY third-party library in Python, JavaScript,
TypeScript, JSX, TSX, and more.
Includes Smart Local Pre-filtering, Self-Healing Feedback Loop, and Sandbox Test Verification.
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
from apipatch.auto_detector import AutoDeprecationDetector, should_audit_file, build_project_context
from apipatch.test_runner import SandboxTestRunner

# Maximum lines to send to LLM in a single request (prevents token-limit failures)
_MAX_CODE_LINES = 2500
# Retry settings for transient LLM/network errors
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 2.0  # seconds
# Maximum self-healing attempts for syntax / structural / test errors
_MAX_HEALING_ATTEMPTS = 2

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
        concurrency: int = 6,
        verify_tests: bool = False
    ):
        self.provider = ProviderFactory.get_provider(
            provider_name=provider_name,
            api_key=api_key,
            model=model
        )
        self.create_backup = create_backup
        self.concurrency = max(1, concurrency)
        self.verify_tests = verify_tests
        self.detector = AutoDeprecationDetector()

    def _call_with_retry(
        self,
        file_name: str,
        code: str,
        libs: List[str],
        project_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calls the LLM provider with exponential backoff retry on transient errors.
        Raises the last exception if all retries are exhausted.
        """
        last_err: Exception = Exception("Unknown error")
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                return self.provider.audit_code(
                    file_name,
                    code,
                    detected_libraries=libs,
                    project_context=project_context
                )
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                # Do not retry on hard errors (auth, invalid key, bad request)
                if any(kw in err_str for kw in ("401", "403", "invalid", "api key", "400")):
                    raise
                if attempt < _MAX_RETRIES:
                    wait = _RETRY_BACKOFF_BASE ** attempt
                    safe_print(
                        f"  {Colors.WARNING}[~] {file_name} LLM error (attempt {attempt}/{_MAX_RETRIES}), "
                        f"retrying in {wait:.0f}s: {e}{Colors.ENDC}"
                    )
                    time.sleep(wait)
        raise last_err

    def _heal_with_retry(
        self,
        file_name: str,
        original_code: str,
        broken_code: str,
        validation_error: str,
        libs: List[str],
        project_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calls the LLM provider's heal_code method with retry.
        """
        last_err: Exception = Exception("Unknown error")
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                return self.provider.heal_code(
                    file_name=file_name,
                    original_code=original_code,
                    broken_code=broken_code,
                    validation_error=validation_error,
                    detected_libraries=libs,
                    project_context=project_context
                )
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                if any(kw in err_str for kw in ("401", "403", "invalid", "api key", "400")):
                    raise
                if attempt < _MAX_RETRIES:
                    wait = _RETRY_BACKOFF_BASE ** attempt
                    time.sleep(wait)
        raise last_err

    def audit_code(
        self,
        file_path: str,
        code: str,
        detected_libraries: Optional[List[str]] = None,
        project_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fully LLM-driven audit with Smart Pre-filtering and Self-Healing Feedback Loop.
        Detects and fixes deprecated/breaking API calls across ANY library.
        """
        file_name = os.path.basename(file_path)
        _, ext = os.path.splitext(file_path)

        empty_result = {
            "has_breaking_changes": False,
            "detected_issues": [],
            "refactored_code": code
        }

        # Fast path 1: Empty or whitespace-only file
        code = code.lstrip('\ufeff')
        if not code.strip():
            return empty_result

        # Fast path 2: Smart Local Pre-filter (runs in ~0.001s, saves 100% tokens for clean files)
        if detected_libraries and not should_audit_file(code, file_path, detected_libraries):
            return empty_result

        if not self.provider:
            safe_print(
                f"  {Colors.WARNING}[!] No AI provider configured. "
                f"Set GEMINI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY "
                f"to enable full analysis.{Colors.ENDC}"
            )
            return empty_result

        # Truncate very large files to avoid token-limit failures
        code_lines = code.splitlines()
        if len(code_lines) > _MAX_CODE_LINES:
            safe_print(
                f"  {Colors.WARNING}[~] {file_name} is large ({len(code_lines)} lines), "
                f"truncating to {_MAX_CODE_LINES} lines for LLM analysis.{Colors.ENDC}"
            )
            code = "\n".join(code_lines[:_MAX_CODE_LINES])

        try:
            # Extract file-specific imports
            if ext in {".py", ".pyw"}:
                file_imports = self.detector.extract_imports_from_file(file_path)
            elif ext in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
                file_imports = self.detector.extract_imports_from_js_file(file_path)
            else:
                file_imports = set()

            if file_imports:
                libs = list(file_imports)
            elif detected_libraries:
                libs = detected_libraries
            else:
                return empty_result

            # Primary LLM Audit
            llm_res = self._call_with_retry(file_name, code, libs, project_context=project_context)

            if llm_res.get("has_breaking_changes") and llm_res.get("refactored_code"):
                refactored = llm_res["refactored_code"]
                val = CodeValidator.validate(code, refactored, file_extension=ext)

                if val.is_valid:
                    return llm_res

                # ── Self-Healing Loop on validation failure ──────────────────
                safe_print(
                    f"  {Colors.WARNING}[~] LLM output for {file_name} failed safety validation "
                    f"({val.error_message}). Triggering Self-Healing Loop...{Colors.ENDC}"
                )

                current_broken_code = refactored
                current_val_error = val.error_message or "Validation error"

                for heal_attempt in range(1, _MAX_HEALING_ATTEMPTS + 1):
                    safe_print(
                        f"  {Colors.OKCYAN}[*] Self-healing attempt {heal_attempt}/{_MAX_HEALING_ATTEMPTS} for {file_name}...{Colors.ENDC}"
                    )
                    try:
                        healed_res = self._heal_with_retry(
                            file_name=file_name,
                            original_code=code,
                            broken_code=current_broken_code,
                            validation_error=current_val_error,
                            libs=libs,
                            project_context=project_context
                        )
                        if healed_res.get("has_breaking_changes") and healed_res.get("refactored_code"):
                            healed_code = healed_res["refactored_code"]
                            val_healed = CodeValidator.validate(code, healed_code, file_extension=ext)
                            if val_healed.is_valid:
                                safe_print(
                                    f"  {Colors.OKGREEN}[✓] {file_name} successfully self-healed on attempt {heal_attempt}!{Colors.ENDC}"
                                )
                                return healed_res
                            else:
                                current_broken_code = healed_code
                                current_val_error = val_healed.error_message or "Validation error"
                    except Exception as heal_err:
                        safe_print(f"  {Colors.WARNING}[~] Self-healing exception: {heal_err}{Colors.ENDC}")

                # If all healing attempts exhausted
                safe_print(
                    f"  {Colors.FAIL}[!] {file_name} self-healing could not resolve error ({current_val_error}). Keeping original.{Colors.ENDC}"
                )
                return empty_result

            return llm_res if llm_res else empty_result

        except Exception as e:
            safe_print(f"  {Colors.WARNING}[!] {file_name} audit failed: {e}{Colors.ENDC}")
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
        detected_libraries: Optional[List[str]] = None,
        project_context: Optional[str] = None,
        verify_tests: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Audits, refactors, previews diff, verifies tests, and optionally writes fixed code to disk."""
        t0 = time.time()
        file_path = os.path.abspath(file_path)
        file_name = os.path.basename(file_path)
        run_tests_flag = self.verify_tests if verify_tests is None else verify_tests

        try:
            with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                original_code = f.read().lstrip('\ufeff')
        except Exception as e:
            safe_print(f"{Colors.FAIL}[!] Cannot read {file_path}: {e}{Colors.ENDC}")
            return {"file": file_path, "status": "error", "issues": []}

        # ── Smart Pre-filter Check ──
        if detected_libraries and not should_audit_file(original_code, file_path, detected_libraries):
            safe_print(f"{Colors.OKGREEN}[✓]{Colors.ENDC} {file_name}: Clean (pre-filtered in 0.00s)")
            return {"file": file_path, "status": "clean", "issues": []}

        audit = self.audit_code(
            file_path,
            original_code,
            detected_libraries=detected_libraries,
            project_context=project_context
        )
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
            backup_path = f"{file_path}.bak"
            if self.create_backup:
                shutil.copy2(file_path, backup_path)
                safe_print(f"  {Colors.OKCYAN}[*] Backup saved → {backup_path}{Colors.ENDC}")

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(refactored)
            safe_print(f"  {Colors.OKGREEN}[✓] Applied refactor to {file_name}.{Colors.ENDC}")

            # ── Sandbox Test Verification ──
            if run_tests_flag:
                target_dir = os.path.dirname(file_path)
                safe_print(f"  {Colors.OKCYAN}[*] Running sandbox test suite verification...{Colors.ENDC}")
                passed, test_log = SandboxTestRunner.run_tests(target_dir)

                if passed:
                    safe_print(f"  {Colors.OKGREEN}[✓] Sandbox tests PASSED for {file_name}!{Colors.ENDC}")
                else:
                    safe_print(
                        f"  {Colors.WARNING}[!] Sandbox tests FAILED for {file_name}. "
                        f"Attempting self-healing with test traceback...{Colors.ENDC}"
                    )
                    # Attempt self-healing with test failure output
                    try:
                        healed_res = self._heal_with_retry(
                            file_name=file_name,
                            original_code=original_code,
                            broken_code=refactored,
                            validation_error=f"Test Suite Failure:\n{test_log}",
                            libs=[issue['library'] for issue in issues] if issues else detected_libraries or [],
                            project_context=project_context
                        )
                        if healed_res.get("has_breaking_changes") and healed_res.get("refactored_code"):
                            new_healed_code = healed_res["refactored_code"]
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.write(new_healed_code)
                            passed_retry, _ = SandboxTestRunner.run_tests(target_dir)
                            if passed_retry:
                                safe_print(f"  {Colors.OKGREEN}[✓] Tests PASSED after self-healing!{Colors.ENDC}")
                                refactored = new_healed_code
                            else:
                                raise Exception("Tests still failing after self-healing.")
                        else:
                            raise Exception("Self-healing returned empty result.")
                    except Exception as e:
                        safe_print(f"  {Colors.FAIL}[!] Reverting {file_name} to backup due to test failure: {e}{Colors.ENDC}")
                        if os.path.exists(backup_path):
                            shutil.copy2(backup_path, file_path)
                        else:
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.write(original_code)
                        return {
                            "file": file_path,
                            "status": "reverted_test_failure",
                            "issues": issues,
                            "test_log": test_log
                        }

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
        write_in_place: bool = False,
        verify_tests: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Recursively and CONCURRENTLY audits all supported source files in target directory.
        Uses ThreadPoolExecutor, Smart Pre-filtering, Self-Healing, and Test Verification.
        """
        start_time = time.time()
        target_dir = os.path.abspath(target_dir)
        safe_print(f"{Colors.HEADER}{Colors.BOLD}=== ApiPatch: Autonomous AI Codebase Auditor ==={Colors.ENDC}")
        safe_print(f"Target Directory : {Colors.OKCYAN}{target_dir}{Colors.ENDC}")
        provider_name = self.provider.__class__.__name__ if self.provider else "No Provider (Offline)"
        safe_print(f"Active AI Engine : {Colors.OKGREEN}{provider_name}{Colors.ENDC}")

        # Discover project-wide dependencies & architecture context
        detector = AutoDeprecationDetector(target_dir)
        deps = detector.detect_dependencies()
        project_context = detector.get_project_context()

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
                    deps,
                    project_context,
                    verify_tests
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
