"""
ApiPatch - Autonomous AI Agent for API Breaking Changes & Self-Maintaining Codebases
Detects and fixes deprecated third-party API calls in Python, JavaScript, TypeScript,
JSX, TSX, and any other language — powered by LLM reasoning.
"""

import warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)

from apipatch._version import __version__, __author__, __license__

from apipatch.engine import ApiPatchEngine
from apipatch.validator import CodeValidator
from apipatch.auto_detector import AutoDeprecationDetector
from apipatch.proactive_hunter import GitHubPRHunter
from apipatch.github_client import GitHubClient, resolve_github_token
from apipatch.webhook import run_webhook_server

__all__ = [
    "ApiPatchEngine",
    "CodeValidator",
    "AutoDeprecationDetector",
    "GitHubPRHunter",
    "GitHubClient",
    "resolve_github_token",
    "run_webhook_server",
    "__version__",
]
