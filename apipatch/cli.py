"""
ApiPatch Command Line Interface (CLI)
Provides modern terminal commands for autonomous API code audits and automated refactoring.
"""

import sys
import argparse
from typing import Optional
from apipatch import __version__
from apipatch.engine import ApiPatchEngine, Colors
from apipatch.auto_detector import AutoDeprecationDetector
from apipatch.proactive_hunter import GitHubPRHunter

# Ensure UTF-8 console output on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        prog="apipatch",
        description=f"{Colors.HEADER}⚡ ApiPatch v{__version__} - Autonomous AI Agent for API Breaking Changes{Colors.ENDC}",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-v", "--version", action="version", version=f"apipatch {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: scan
    scan_parser = subparsers.add_parser("scan", help="Scan a codebase for deprecated API signatures")
    scan_parser.add_argument("path", nargs="?", default=".", help="File or directory path to scan (default: current dir)")
    scan_parser.add_argument("--provider", choices=["openai", "anthropic", "gemini"], help="AI provider for dynamic reasoning")
    scan_parser.add_argument("--api-key", help="API key for chosen provider")
    scan_parser.add_argument("--model", help="Specific model name (e.g., gpt-4o, claude-3-7-sonnet)")

    # Command: fix
    fix_parser = subparsers.add_parser("fix", help="Audit and generate modernized code refactors")
    fix_parser.add_argument("path", nargs="?", default=".", help="File or directory path to refactor")
    fix_parser.add_argument("-w", "--write", action="store_true", help="Apply fixes in-place to files on disk")
    fix_parser.add_argument("--no-backup", action="store_true", help="Disable automatic .bak file creation when writing")
    fix_parser.add_argument("--provider", choices=["openai", "anthropic", "gemini"], help="AI provider for dynamic reasoning")
    fix_parser.add_argument("--api-key", help="API key for chosen provider")
    fix_parser.add_argument("--model", help="Specific model name")

    # Command: detect
    detect_parser = subparsers.add_parser("detect", help="Auto-discover project dependencies and deprecation rules")
    detect_parser.add_argument("path", nargs="?", default=".", help="Project directory path (default: current dir)")

    # Command: hunt
    hunt_parser = subparsers.add_parser("hunt", help="Proactively search GitHub for deprecated code and prepare PRs")
    hunt_parser.add_argument("query", nargs="?", default="openai.ChatCompletion.create language:python", help="GitHub Code Search query")
    hunt_parser.add_argument("--max", type=int, default=3, help="Max candidate repositories to inspect")
    hunt_parser.add_argument("--token", help="GitHub Personal Access Token")

    args = parser.parse_args()

    if not args.command:
        # Default behavior if no subcommand passed: interactive help or scan
        parser.print_help()
        sys.exit(0)

    if args.command == "scan":
        engine = ApiPatchEngine(
            provider_name=args.provider,
            api_key=args.api_key,
            model=args.model,
            create_backup=False
        )
        if os_is_file(args.path):
            engine.process_file(args.path, write_in_place=False)
        else:
            engine.process_directory(args.path, write_in_place=False)

    elif args.command == "fix":
        engine = ApiPatchEngine(
            provider_name=args.provider,
            api_key=args.api_key,
            model=args.model,
            create_backup=not args.no_backup
        )
        if os_is_file(args.path):
            engine.process_file(args.path, write_in_place=args.write)
        else:
            engine.process_directory(args.path, write_in_place=args.write)

    elif args.command == "detect":
        detector = AutoDeprecationDetector(target_dir=args.path)
        detector.run_autonomous_discovery()

    elif args.command == "hunt":
        hunter = GitHubPRHunter(github_token=args.token)
        hunter.hunt_and_preview(query=args.query, max_results=args.max)


def os_is_file(path: str) -> bool:
    import os
    return os.path.isfile(path)


if __name__ == "__main__":
    main()
