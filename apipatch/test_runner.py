"""
ApiPatch Sandbox Test Runner
Executes local test suites (pytest, unittest, npm test) in an isolated subprocess
to verify that refactored code passes all unit and integration tests.
"""

import os
import sys
import json
import subprocess
from typing import Tuple, Optional


class SandboxTestRunner:
    @staticmethod
    def detect_test_framework(target_dir: str) -> Optional[str]:
        """
        Detects available test suites in the target project directory.
        Returns 'pytest', 'unittest', 'npm', or None.
        """
        target_dir = os.path.abspath(target_dir)

        # 1. Python test suite detection
        has_tests_dir = os.path.isdir(os.path.join(target_dir, "tests")) or os.path.isdir(os.path.join(target_dir, "test"))
        has_pyproject = os.path.isfile(os.path.join(target_dir, "pyproject.toml"))
        has_pytest_ini = os.path.isfile(os.path.join(target_dir, "pytest.ini"))

        # Look for any test_*.py files in target_dir
        has_test_files = False
        for root, _, files in os.walk(target_dir):
            if any(d in root for d in (".git", "node_modules", "venv", ".venv", "__pycache__")):
                continue
            if any(f.startswith("test_") and f.endswith(".py") for f in files):
                has_test_files = True
                break

        if has_pytest_ini or has_tests_dir or has_test_files or has_pyproject:
            return "pytest"

        # 2. Node.js / JS / TS test suite detection
        pkg_path = os.path.join(target_dir, "package.json")
        if os.path.isfile(pkg_path):
            try:
                with open(pkg_path, "r", encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)
                if "scripts" in data and "test" in data["scripts"]:
                    test_cmd = data["scripts"]["test"].strip().lower()
                    if test_cmd and not test_cmd.startswith('echo "error: no test specified"'):
                        return "npm"
            except Exception:
                pass

        return None

    @classmethod
    def run_tests(
        cls,
        target_dir: str,
        timeout: int = 60,
        custom_command: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Runs project tests in a subprocess.
        Returns (passed: bool, output_log: str).
        """
        target_dir = os.path.abspath(target_dir)

        if custom_command:
            cmd = custom_command.split()
        else:
            framework = cls.detect_test_framework(target_dir)
            if not framework:
                return True, "No automated test suite detected in project directory."

            if framework == "pytest":
                cmd = [sys.executable, "-m", "pytest", "-q"]
            elif framework == "npm":
                cmd = ["npm", "test"]
            elif framework == "unittest":
                cmd = [sys.executable, "-m", "unittest", "discover"]
            else:
                return True, f"Unsupported framework '{framework}', skipping automated test run."

        try:
            # On Windows, npm is npm.cmd
            shell_mode = (os.name == "nt" and cmd[0] in ("npm", "npx", "yarn", "pnpm"))
            result = subprocess.run(
                cmd,
                cwd=target_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=shell_mode
            )
            output = (result.stdout + "\n" + result.stderr).strip()
            passed = (result.returncode == 0)
            return passed, output

        except subprocess.TimeoutExpired:
            return False, f"Test execution timed out after {timeout} seconds."
        except FileNotFoundError as e:
            return False, f"Test runner executable not found: {e}"
        except Exception as e:
            return False, f"Error running tests: {str(e)}"
