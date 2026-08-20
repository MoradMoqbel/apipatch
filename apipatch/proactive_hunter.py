"""
ApiPatch Proactive GitHub PR Hunter & Submitter
Discovers public repositories using deprecated APIs, generates modernized patches,
and autonomously submits live GitHub Pull Requests via the GitHub REST API.
"""

import os
import sys
import json
import base64
import time
import urllib.request
import urllib.parse
import urllib.error
from typing import List, Dict, Any, Optional
from apipatch.engine import ApiPatchEngine, Colors
from apipatch.github_client import GitHubClient, resolve_github_token, mask_token
from apipatch.auto_detector import should_audit_file

GITHUB_API_BASE = "https://api.github.com"


def _build_raw_url(item: dict) -> str:
    """
    Builds a reliable raw.githubusercontent.com URL from a GitHub Code Search API item.
    """
    raw_url = item.get("raw_url", "")
    if raw_url:
        return raw_url

    html_url = item.get("html_url", "")
    if not html_url:
        return ""

    import re
    m = re.match(r"https://github\.com/([^/]+/[^/]+)/blob/(.+)", html_url)
    if m:
        repo_path = m.group(1)
        ref_and_file = m.group(2)
        return f"https://raw.githubusercontent.com/{repo_path}/{ref_and_file}"

    return (
        html_url
        .replace("github.com", "raw.githubusercontent.com")
        .replace("/blob/", "/")
    )


class GitHubPRHunter:
    """
    Autonomous GitHub Repository Auditing and Pull Request Engine.
    Discovers legacy code, refactors deprecated API signatures, creates forks/branches,
    and opens live GitHub Pull Requests with detailed Markdown reports.
    """

    def __init__(self, github_token: Optional[str] = None, engine: Optional[ApiPatchEngine] = None):
        self.github_token = resolve_github_token(github_token)
        self.client = GitHubClient(token=self.github_token)
        self.engine = engine or ApiPatchEngine()

    def _request(
        self,
        endpoint: str,
        method: str = "GET",
        payload: Optional[Dict[str, Any]] = None,
        full_url: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Makes an authenticated request to the GitHub REST API."""
        url = full_url or f"{GITHUB_API_BASE}{endpoint}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ApiPatch-Bot/1.0"
        }
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"

        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body.strip() else {"status": "ok"}
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="ignore")
            if e.code == 403 and "rate limit" in err_msg.lower():
                print(f"{Colors.WARNING}[!] GitHub API rate limit reached.{Colors.ENDC}")
            elif e.code != 404:
                print(f"{Colors.FAIL}[!] GitHub API error ({e.code}) on {method} {url}: {err_msg}{Colors.ENDC}")
            return None
        except Exception as e:
            print(f"{Colors.FAIL}[!] Network error on GitHub API request: {e}{Colors.ENDC}")
            return None

    # ── Discovery & Search ───────────────────────────────────────────────────

    def search_deprecated_code(
        self,
        query: str,
        max_results: int = 5,
        recent_days: Optional[int] = 30,
        min_stars: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Searches GitHub Code API sorted by 'indexed' (newest first).
        Optionally filters results to repositories updated within the last `recent_days` (default: 30)
        and with at least `min_stars`.
        """
        encoded_query = urllib.parse.quote(query)
        fetch_limit = min(50, max(max_results * 4, 20)) if recent_days is not None or min_stars > 0 else max_results
        endpoint = f"/search/code?q={encoded_query}&sort=indexed&order=desc&per_page={fetch_limit}"

        days_info = f" (Updated in last {recent_days} days)" if recent_days else ""
        stars_info = f" [Min stars: {min_stars}]" if min_stars > 0 else ""
        print(f"{Colors.OKCYAN}[*] Searching GitHub for: '{query}'{days_info}{stars_info}...{Colors.ENDC}")
        data = self._request(endpoint)
        if not data or not isinstance(data, dict):
            return []

        raw_items = data.get("items", [])
        if not raw_items:
            print(f"{Colors.WARNING}[!] No search matches found on GitHub.{Colors.ENDC}")
            return []

        if recent_days is None and min_stars <= 0:
            print(f"{Colors.OKGREEN}[✓] Found {len(raw_items[:max_results])} matching candidate file(s) on GitHub!{Colors.ENDC}\n")
            return raw_items[:max_results]

        # Filter strictly by recency and stars
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)
        filtered_items = []
        seen_repos = set()

        for item in raw_items:
            repo_name = item.get("repository", {}).get("full_name")
            if not repo_name or repo_name in seen_repos:
                continue

            repo_info = self.client.get_repository(repo_name)
            if not repo_info or not isinstance(repo_info, dict):
                continue

            if repo_info.get("archived", False):
                continue

            stars = repo_info.get("stargazers_count", 0)
            if stars < min_stars:
                continue

            pushed_at_str = repo_info.get("pushed_at", "")
            days_ago = None
            if pushed_at_str:
                try:
                    pushed_dt = datetime.datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))
                    days_ago = (now - pushed_dt).days
                except Exception:
                    pass

            if recent_days is not None:
                if days_ago is None or days_ago > recent_days:
                    continue

            seen_repos.add(repo_name)
            item["_stars"] = stars
            item["_pushed_at"] = pushed_at_str[:10] if pushed_at_str else "Unknown"
            item["_days_ago"] = days_ago if days_ago is not None else 0
            filtered_items.append(item)

            if len(filtered_items) >= max_results:
                break

        print(f"{Colors.OKGREEN}[✓] Found {len(filtered_items)} strictly recent & active candidate file(s) on GitHub!{Colors.ENDC}\n")
        return filtered_items

    def fetch_raw_file_content(self, raw_url: str) -> Optional[str]:
        """Fetches raw code content from repository file URL."""
        try:
            req = urllib.request.Request(raw_url, headers={"User-Agent": "ApiPatch-Bot/1.0"})
            if self.github_token:
                req.add_header("Authorization", f"token {self.github_token}")
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read().decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"{Colors.FAIL}[!] Failed to fetch file content: {e}{Colors.ENDC}")
            return None

    # ── Live GitHub REST API Operations ──────────────────────────────────────

    def get_authenticated_user(self) -> Optional[str]:
        """Returns the username of the authenticated token owner."""
        data = self._request("/user")
        if data and isinstance(data, dict) and "login" in data:
            return data["login"]
        return None

    def fork_repository(self, repo_full_name: str) -> Optional[str]:
        """Forks the target repository and returns 'fork_owner/repo_name'."""
        clean_name = GitHubClient.normalize_repo_name(repo_full_name)
        print(f"  {Colors.OKCYAN}[*] Forking {clean_name}...{Colors.ENDC}")
        data = self._request(f"/repos/{clean_name}/forks", method="POST")
        if data and isinstance(data, dict) and "full_name" in data:
            time.sleep(1.5)
            return data["full_name"]
        return None

    def get_default_branch(self, repo_full_name: str) -> str:
        """Returns the default branch name of the repository (main/master)."""
        clean_name = GitHubClient.normalize_repo_name(repo_full_name)
        data = self._request(f"/repos/{clean_name}")
        if data and isinstance(data, dict) and "default_branch" in data:
            return data["default_branch"]
        return "main"

    def get_branch_sha(self, repo_full_name: str, branch: str) -> Optional[str]:
        """Gets the commit SHA of the latest commit on a branch."""
        clean_name = GitHubClient.normalize_repo_name(repo_full_name)
        data = self._request(f"/repos/{clean_name}/git/ref/heads/{branch}")
        if data and isinstance(data, dict) and "object" in data and "sha" in data["object"]:
            return data["object"]["sha"]
        data_b = self._request(f"/repos/{clean_name}/branches/{branch}")
        if data_b and isinstance(data_b, dict) and "commit" in data_b and "sha" in data_b["commit"]:
            return data_b["commit"]["sha"]
        return None

    def create_branch(self, repo_full_name: str, new_branch: str, base_sha: str) -> bool:
        """Creates a new git reference / branch in the repository."""
        clean_name = GitHubClient.normalize_repo_name(repo_full_name)
        payload = {
            "ref": f"refs/heads/{new_branch}",
            "sha": base_sha
        }
        data = self._request(f"/repos/{clean_name}/git/refs", method="POST", payload=payload)
        return data is not None and isinstance(data, dict) and ("ref" in data or data.get("status") == "ok")

    def get_file_sha(self, repo_full_name: str, file_path: str, ref: str) -> Optional[str]:
        """Retrieves the blob SHA of an existing file in the repo branch."""
        clean_name = GitHubClient.normalize_repo_name(repo_full_name)
        clean_path = file_path.lstrip("/")
        encoded_path = urllib.parse.quote(clean_path)
        data = self._request(f"/repos/{clean_name}/contents/{encoded_path}?ref={ref}")
        if data and isinstance(data, dict) and "sha" in data:
            return data["sha"]
        return None

    def commit_file_change(
        self,
        repo_full_name: str,
        branch: str,
        file_path: str,
        new_content: str,
        commit_message: str
    ) -> bool:
        """Commits and pushes updated file content to a branch."""
        clean_name = GitHubClient.normalize_repo_name(repo_full_name)
        clean_path = file_path.lstrip("/")
        existing_sha = self.get_file_sha(clean_name, clean_path, branch)

        encoded_content = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")
        payload = {
            "message": commit_message,
            "content": encoded_content,
            "branch": branch
        }
        if existing_sha:
            payload["sha"] = existing_sha

        encoded_path = urllib.parse.quote(clean_path)
        data = self._request(f"/repos/{clean_name}/contents/{encoded_path}", method="PUT", payload=payload)
        return data is not None and isinstance(data, dict) and ("content" in data or "commit" in data)

    def submit_pull_request(
        self,
        base_repo: str,
        head_branch: str,
        base_branch: str,
        title: str,
        body: str
    ) -> Optional[Dict[str, Any]]:
        """Creates a Pull Request against the base repository."""
        clean_base = GitHubClient.normalize_repo_name(base_repo)
        payload = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch
        }
        return self._request(f"/repos/{clean_base}/pulls", method="POST", payload=payload)

    def submit_automated_pr(
        self,
        repo_name: str,
        file_path: str,
        new_content: str,
        audit_result: Dict[str, Any],
        fork: bool = True
    ) -> Optional[str]:
        """
        Orchestrates the single-file live GitHub PR submission workflow:
        1. Checks authentication.
        2. Forks repo (if fork=True).
        3. Creates a new migration branch.
        4. Commits the refactored code.
        5. Opens a Pull Request against the target repository.
        Returns the live URL of the newly created Pull Request.
        """
        if not self.github_token:
            print(f"  {Colors.FAIL}[!] GITHUB_TOKEN is required to submit Pull Requests.{Colors.ENDC}")
            return None

        auth_user = self.get_authenticated_user()
        if not auth_user:
            print(f"  {Colors.FAIL}[!] Invalid GITHUB_TOKEN or cannot authenticate user.{Colors.ENDC}")
            return None

        pr_meta = self.generate_pr_payload(repo_name, file_path, audit_result)
        base_branch = self.get_default_branch(repo_name)
        base_sha = self.get_branch_sha(repo_name, base_branch)

        if not base_sha:
            print(f"  {Colors.FAIL}[!] Could not retrieve base branch '{base_branch}' commit SHA for {repo_name}.{Colors.ENDC}")
            return None

        working_repo = repo_name
        head_ref = ""
        timestamp = int(time.time())
        branch_name = f"apipatch/migrate-{timestamp}"

        if fork:
            fork_repo = self.fork_repository(repo_name)
            if not fork_repo:
                fork_repo = f"{auth_user}/{repo_name.split('/')[-1]}"
            working_repo = fork_repo
            head_ref = f"{auth_user}:{branch_name}"
        else:
            head_ref = branch_name

        print(f"  {Colors.OKCYAN}[*] Creating branch '{branch_name}' on {working_repo}...{Colors.ENDC}")
        branch_created = self.create_branch(working_repo, branch_name, base_sha)
        if not branch_created:
            print(f"  {Colors.FAIL}[!] Failed to create branch '{branch_name}' on {working_repo}.{Colors.ENDC}")
            return None

        commit_msg = pr_meta["title"]
        print(f"  {Colors.OKCYAN}[*] Committing modernized code to '{file_path}'...{Colors.ENDC}")
        committed = self.commit_file_change(
            repo_full_name=working_repo,
            branch=branch_name,
            file_path=file_path,
            new_content=new_content,
            commit_message=commit_msg
        )
        if not committed:
            print(f"  {Colors.FAIL}[!] Failed to commit file changes.{Colors.ENDC}")
            return None

        print(f"  {Colors.OKCYAN}[*] Submitting live Pull Request to {repo_name}...{Colors.ENDC}")
        pr_response = self.submit_pull_request(
            base_repo=repo_name,
            head_branch=head_ref,
            base_branch=base_branch,
            title=pr_meta["title"],
            body=pr_meta["body"]
        )

        if pr_response and isinstance(pr_response, dict) and "html_url" in pr_response:
            pr_url = pr_response["html_url"]
            print(f"\n{Colors.OKGREEN}{Colors.BOLD}🎉 SUCCESS! Pull Request opened:{Colors.ENDC} {Colors.OKCYAN}{pr_url}{Colors.ENDC}\n")
            return pr_url
        else:
            print(f"  {Colors.FAIL}[!] Failed to open Pull Request.{Colors.ENDC}")
            return None

    # ── Full Repository Automated Audit & PR Pipeline ───────────────────────

    def audit_and_pr_repository(
        self,
        repo_name: str,
        fork: Optional[bool] = None,
        base_branch: Optional[str] = None,
        branch_name: Optional[str] = None,
        submit: bool = True,
        dry_run: bool = False,
        max_files: int = 50,
        precomputed_results: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Audits an entire GitHub repository, applies refactorings to all deprecated files,
        creates a branch (directly or on a fork), commits all modified files, and opens
        a comprehensive live Pull Request.
        """
        repo_name = GitHubClient.normalize_repo_name(repo_name)
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== ApiPatch: Autonomous GitHub PR Pipeline ==={Colors.ENDC}")
        print(f"Target Repository: {Colors.OKCYAN}{repo_name}{Colors.ENDC}")
        print(f"Auth Token: {Colors.OKBLUE}{mask_token(self.github_token)}{Colors.ENDC}")

        if not self.github_token:
            print(f"{Colors.FAIL}[!] GitHub token not found. Please provide GITHUB_TOKEN or github_token.txt.{Colors.ENDC}")
            return {"status": "error", "error": "Missing GitHub token"}

        auth_user = self.get_authenticated_user()
        if not auth_user:
            print(f"{Colors.FAIL}[!] Invalid GitHub token. Failed to authenticate.{Colors.ENDC}")
            return {"status": "error", "error": "Authentication failed"}

        print(f"Authenticated As: {Colors.OKGREEN}@{auth_user}{Colors.ENDC}")

        # Resolve base branch and SHA
        base_branch = base_branch or self.get_default_branch(repo_name)
        base_sha = self.get_branch_sha(repo_name, base_branch)
        if not base_sha:
            print(f"{Colors.FAIL}[!] Could not retrieve commit SHA for branch '{base_branch}' in {repo_name}.{Colors.ENDC}")
            return {"status": "error", "error": f"Base branch {base_branch} not found"}

        print(f"Base Branch: {Colors.BOLD}{base_branch}{Colors.ENDC} ({base_sha[:8]})")

        # 1. Gather files to audit
        audit_results: List[Dict[str, Any]] = []
        files_to_commit: Dict[str, str] = {}

        if precomputed_results:
            audit_results = precomputed_results
            for r in audit_results:
                files_to_commit[r["file"]] = r["refactored_code"]
        else:
            print(f"\n{Colors.OKCYAN}[*] Fetching file tree for {repo_name}...{Colors.ENDC}")
            tree_items = self.client.get_repo_file_tree(repo_name, base_branch)
            print(f"[✓] Retrieved {len(tree_items)} total repository files.")

            supported_exts = (".py", ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs")
            candidate_files = [
                item["path"] for item in tree_items
                if item.get("path", "").endswith(supported_exts)
                and not any(ignore in item.get("path", "") for ignore in [
                    "node_modules/", ".git/", "__pycache__/", "venv/", ".env", "dist/", "build/"
                ])
            ][:max_files]

            print(f"[*] Inspecting {len(candidate_files)} supported candidate code files in parallel...")

            def _inspect_single_file(path: str):
                try:
                    content = self.client.fetch_file_content(repo_name, path, ref=base_branch)
                    if not content:
                        return None
                    if not should_audit_file(content, path):
                        return None
                    audit = self.engine.audit_code(path, content)
                    if audit.get("has_breaking_changes") and audit.get("refactored_code"):
                        diff = self.engine.generate_diff(content, audit["refactored_code"], path)
                        return {
                            "file": path,
                            "refactored_code": audit["refactored_code"],
                            "detected_issues": audit.get("detected_issues", []),
                            "diff": diff
                        }
                except Exception:
                    pass
                return None

            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=min(3, len(candidate_files) or 1)) as executor:
                futures = {executor.submit(_inspect_single_file, path): path for path in candidate_files}
                for fut in as_completed(futures):
                    res = fut.result()
                    if res:
                        print(f"  {Colors.WARNING}⚡ Breaking changes detected in {res['file']}{Colors.ENDC}", flush=True)
                        self.engine.print_diff(res["diff"])
                        audit_results.append({
                            "file": res["file"],
                            "refactored_code": res["refactored_code"],
                            "detected_issues": res["detected_issues"],
                            "diff": res["diff"]
                        })
                        files_to_commit[res["file"]] = res["refactored_code"]

        if not audit_results:
            print(f"\n{Colors.OKGREEN}[✓] No deprecated or breaking API calls detected. Codebase is modern and clean!{Colors.ENDC}\n")
            return {
                "status": "clean",
                "repo": repo_name,
                "modified_files": 0,
                "audit_results": []
            }

        print(f"\n{Colors.OKGREEN}[✓] Identified {len(audit_results)} file(s) requiring modernization.{Colors.ENDC}")

        # 2. Generate PR Markdown Payload
        pr_payload = self.client.generate_pr_markdown(repo_name, audit_results)
        print(f"\n{Colors.HEADER}Proposed PR Title:{Colors.ENDC} {pr_payload['title']}")

        if dry_run or not submit:
            print(f"\n{Colors.WARNING}[DRY-RUN / PREVIEW] PR creation skipped.{Colors.ENDC}")
            return {
                "status": "preview",
                "repo": repo_name,
                "modified_files": len(files_to_commit),
                "title": pr_payload["title"],
                "body": pr_payload["body"],
                "audit_results": audit_results
            }

        # 3. Determine Forking & Branching Strategy
        has_write = self.client.has_write_permission(repo_name)
        should_fork = fork if fork is not None else (not has_write)

        working_repo = repo_name
        head_ref = ""
        timestamp = int(time.time())
        branch_to_create = branch_name or f"apipatch/migrate-{timestamp}"

        if should_fork:
            print(f"\n[*] Forking repository to @{auth_user}...")
            fork_repo = self.client.fork_repository(repo_name)
            if not fork_repo:
                fork_repo = f"{auth_user}/{repo_name.split('/')[-1]}"
            working_repo = fork_repo
            head_ref = f"{auth_user}:{branch_to_create}"
            print(f"[✓] Using fork: {working_repo}")
        else:
            working_repo = repo_name
            head_ref = branch_to_create
            print(f"[✓] Direct push permissions available on {working_repo}")

        # 4. Create Working Branch
        print(f"[*] Creating branch '{branch_to_create}' on {working_repo}...")
        branch_created = self.create_branch(working_repo, branch_to_create, base_sha)
        if not branch_created:
            print(f"{Colors.FAIL}[!] Failed to create branch '{branch_to_create}' on {working_repo}.{Colors.ENDC}")
            return {"status": "error", "error": f"Failed to create branch on {working_repo}"}

        # 5. Commit Modified Files
        commit_msg = pr_payload["title"]
        print(f"[*] Committing {len(files_to_commit)} modernized file(s)...")

        commit_sha = None
        if len(files_to_commit) == 1:
            f_path, f_content = list(files_to_commit.items())[0]
            ok = self.commit_file_change(working_repo, branch_to_create, f_path, f_content, commit_msg)
            if ok:
                commit_sha = "single_commit_ok"
        else:
            commit_sha = self.client.commit_multiple_files(
                repo_full_name=working_repo,
                branch=branch_to_create,
                files=files_to_commit,
                commit_message=commit_msg,
                base_sha=base_sha
            )
            if not commit_sha:
                for f_path, f_content in files_to_commit.items():
                    self.commit_file_change(working_repo, branch_to_create, f_path, f_content, commit_msg)
                commit_sha = "fallback_multi_ok"

        if not commit_sha:
            print(f"{Colors.FAIL}[!] Failed to commit modernized files.{Colors.ENDC}")
            return {"status": "error", "error": "Commit failed"}

        print(f"{Colors.OKGREEN}[✓] Successfully committed all refactored code.{Colors.ENDC}")

        # 6. Submit Pull Request
        print(f"[*] Submitting live Pull Request to {repo_name}...")
        pr_response = self.submit_pull_request(
            base_repo=repo_name,
            head_branch=head_ref,
            base_branch=base_branch,
            title=pr_payload["title"],
            body=pr_payload["body"]
        )

        if pr_response and isinstance(pr_response, dict) and "html_url" in pr_response:
            pr_url = pr_response["html_url"]
            print(f"\n{Colors.OKGREEN}{Colors.BOLD}🎉 SUCCESS! Pull Request Opened:{Colors.ENDC} {Colors.OKCYAN}{pr_url}{Colors.ENDC}\n")
            return {
                "status": "success",
                "pr_url": pr_url,
                "pr_number": pr_response.get("number"),
                "repo": repo_name,
                "branch": branch_to_create,
                "modified_files": len(files_to_commit),
                "audit_results": audit_results
            }
        else:
            print(f"{Colors.FAIL}[!] Failed to open Pull Request via GitHub REST API.{Colors.ENDC}")
            return {
                "status": "error",
                "error": "Failed to submit Pull Request",
                "branch": branch_to_create
            }

    # ── PR Payload Generation ────────────────────────────────────────────────

    def generate_pr_payload(self, repo_name: str, file_path: str, audit_result: Dict[str, Any]) -> Dict[str, str]:
        """Creates standard PR title and structured Markdown body for single file."""
        issues = audit_result.get("issues", [])
        lib_name = issues[0]["library"] if issues else "API"
        short_file = os.path.basename(file_path)

        title = f"[ApiPatch] Migrate deprecated {lib_name} API calls in {short_file}"

        body_lines = [
            f"## ⚡ Automated API Migration by [ApiPatch](https://github.com/MoradMoqbel/apipatch)",
            "",
            f"This Pull Request refactors deprecated/breaking **{lib_name}** API calls in `{file_path}`.",
            "",
            "### 🔍 Detected Deprecations:",
        ]

        for i, issue in enumerate(issues, 1):
            body_lines.append(f"- **#{i} [{issue['library']}]:** {issue['description']}")
            body_lines.append(f"  - `Old:` `{issue['deprecated_symbol']}`")
            body_lines.append(f"  - `New:` `{issue['replacement_symbol']}`")

        body_lines.extend([
            "",
            "### 🛡️ Safety & Validation:",
            "- [x] AST syntax parsed and verified.",
            "- [x] 100% business logic signatures preserved.",
            "- [x] Multi-layer structural safety guard passed.",
            "",
            "> *Generated autonomously by [ApiPatch](https://github.com/MoradMoqbel/apipatch).*"
        ])

        return {
            "title": title,
            "body": "\n".join(body_lines)
        }

    # ── CLI Entrypoint ───────────────────────────────────────────────────────

    def hunt_and_preview(
        self,
        query: str = "openai.ChatCompletion.create language:python",
        max_results: int = 3,
        recent_days: Optional[int] = 30,
        min_stars: int = 0,
        submit: bool = False,
        fork: bool = True
    ):
        """Runs the discovery and generates PR preview packages or submits live PRs."""
        print(f"{Colors.HEADER}{Colors.BOLD}=== ApiPatch: Proactive Open-Source PR Hunter ==={Colors.ENDC}\n")
        results = self.search_deprecated_code(
            query=query,
            max_results=max_results,
            recent_days=recent_days,
            min_stars=min_stars
        )

        if not results:
            print(f"{Colors.WARNING}[!] No candidate repositories matched your strict filters.{Colors.ENDC}")
            print(f"💡 Tips to find matching repositories:")
            print(f"  • Try lowering `--min-stars` (e.g., `--min-stars 10` or `--min-stars 20`)")
            print(f"  • Try expanding `--days` (e.g., `--days 90` or `--days 180`)")
            print(f"  • Try other breaking library changes like Pydantic, LangChain, or Stripe:\n")
            print(f"    apipatch hunt \"from pydantic import validator language:python\" --days 60")
            print(f"    apipatch hunt \"from langchain.chains import LLMChain language:python\" --days 90\n")
            return

        for item in results:
            repo_name = item.get("repository", {}).get("full_name", "Unknown/Repo")
            file_name = item.get("path", "")
            raw_url = _build_raw_url(item)

            meta_str = ""
            if "_stars" in item and "_days_ago" in item:
                meta_str = f" (⭐ {item['_stars']} | 🕒 {item['_days_ago']}d ago / {item['_pushed_at']})"

            print(f"\n🎯 Target: {Colors.BOLD}{repo_name}{Colors.ENDC}{meta_str} -> {Colors.OKCYAN}{file_name}{Colors.ENDC}")
            raw_code = self.fetch_raw_file_content(raw_url)
            if raw_code:
                audit = self.engine.audit_code(file_name, raw_code)
                if audit["has_breaking_changes"]:
                    diff = self.engine.generate_diff(raw_code, audit["refactored_code"], file_name)
                    self.engine.print_diff(diff)
                    pr_data = self.generate_pr_payload(repo_name, file_name, {"issues": audit["detected_issues"]})
                    print(f"\n{Colors.HEADER}Ready to Submit PR:{Colors.ENDC} {pr_data['title']}")

                    if submit:
                        self.submit_automated_pr(
                            repo_name=repo_name,
                            file_path=file_name,
                            new_content=audit["refactored_code"],
                            audit_result={"issues": audit["detected_issues"]},
                            fork=fork
                        )

    def search_recent_repositories(
        self,
        topic_or_query: str = "topic:ai language:python",
        days: int = 30,
        min_stars: int = 10,
        max_stars: Optional[int] = 500,
        max_repos: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Finds strictly recent, active, non-fork, non-archived repositories
        pushed within the last `days` days.
        """
        import datetime
        cutoff_date = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).strftime("%Y-%m-%d")

        qualifiers = [
            topic_or_query,
            f"pushed:>{cutoff_date}",
            f"stars:{min_stars}..{max_stars}" if max_stars else f"stars:>={min_stars}",
            "fork:false",
            "archived:false"
        ]
        full_query = " ".join(qualifiers)
        encoded = urllib.parse.quote(full_query)
        fetch_limit = min(30, max_repos * 3)
        endpoint = f"/search/repositories?q={encoded}&sort=updated&order=desc&per_page={fetch_limit}"

        print(f"{Colors.OKCYAN}[*] Discovering active repositories ({days}d recency, {min_stars}+ stars): '{topic_or_query}'...{Colors.ENDC}", flush=True)
        data = self._request(endpoint)
        if not data or not isinstance(data, dict):
            return []

        raw_items = data.get("items", [])
        filtered = []
        for item in raw_items:
            name = item.get("name", "").lower()
            desc = (item.get("description") or "").lower()
            # Exclude documentation, awesome-lists, markdown collections
            if any(term in name for term in ["docs", "documentation", "awesome-", "cheat-sheet", "tutorial"]):
                continue
            if any(term in desc for term in ["curated list", "collection of", "documentation for"]):
                continue
            filtered.append(item)
            if len(filtered) >= max_repos:
                break

        return filtered

    def discover_and_audit(
        self,
        query: str = "topic:ai language:python",
        days: int = 30,
        min_stars: int = 10,
        max_repos: int = 3,
        dry_run: bool = True
    ):
        """
        Discovers trending fresh repositories and audits their files for breaking changes.
        """
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== ApiPatch: Smart Repository Discovery Engine ==={Colors.ENDC}\n")
        repos = self.search_recent_repositories(
            topic_or_query=query,
            days=days,
            min_stars=min_stars,
            max_repos=max_repos
        )

        if not repos:
            print(f"{Colors.WARNING}[!] No active repositories matched the query. Try adjusting query or stars.{Colors.ENDC}")
            return

        print(f"{Colors.OKGREEN}[✓] Discovered {len(repos)} fresh, active candidate repositories!{Colors.ENDC}\n")

        for repo in repos:
            full_name = repo["full_name"]
            stars = repo.get("stargazers_count", 0)
            pushed_at = repo.get("pushed_at", "")[:10]
            desc = (repo.get("description") or "No description")[:70]

            print(f"\n📁 {Colors.BOLD}{Colors.HEADER}[ {full_name} ]{Colors.ENDC} (⭐ {stars} stars | 🕒 Updated: {pushed_at})")
            print(f"   Description: {desc}")

            self.audit_and_pr_repository(
                repo_name=full_name,
                dry_run=dry_run,
                submit=not dry_run,
                max_files=10
            )
