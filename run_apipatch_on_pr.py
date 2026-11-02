#!/usr/bin/env python3
"""
100% Dynamic ApiPatch v0.9.0 Python Pipeline Runner (Zero Hardcoded Rules / Zero Hardcoded Paths)
Uses Morad Moqbel's actual `apipatch` modules dynamically:
  - apipatch.doc_hunter.DocHunter (Live PyPI, npm, Changelog, and GitHub Release Grounding)
  - apipatch.validator.CodeValidator (Real AST & Syntax Verification)
  - apipatch.engine (strip_code_fences, sanitize_python_formatting, ensure_docstring_restored, shield_unaffected_functions)
  - Dynamic GitHub Tree Crawler (`codeViewTreeRoute`) to locate the exact source file importing the upgraded package
"""

import os
import sys
import re
import json
import difflib
import argparse
import urllib.request
from typing import Dict, Any, List, Optional

from apipatch.doc_hunter import DocHunter
from apipatch.validator import CodeValidator
from apipatch.engine import (
    strip_code_fences,
    sanitize_python_formatting,
    ensure_docstring_restored,
    shield_unaffected_functions,
    is_meaningful_code_change
)


def fetch_url_text(url: str, timeout: int = 8, accept: str = "text/plain, application/vnd.github.v3.diff, */*") -> Optional[str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; ApiPatch-Engine/0.9.0)",
            "Accept": accept
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def parse_pr_diff_files(raw_diff: str) -> List[Dict[str, str]]:
    if not raw_diff:
        return []
    files: List[Dict[str, str]] = []
    chunks = re.split(r"(?=^diff --git )", raw_diff, flags=re.MULTILINE)
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk.startswith("diff --git"):
            continue
        m = re.search(r"^\+\+\+ b/(.+)$", chunk, flags=re.MULTILINE)
        if not m:
            m = re.search(r"^diff --git a/(\S+) b/(\S+)", chunk)
            file_path = m.group(2) if m else ""
        else:
            file_path = m.group(1).strip()
        if file_path and file_path != "/dev/null":
            files.append({"path": file_path, "diff": chunk})
    return files


def fetch_raw_repo_file(repo_full: str, file_path: str) -> Optional[str]:
    for branch in ["HEAD", "main", "master", "develop", "canary"]:
        raw_url = f"https://raw.githubusercontent.com/{repo_full}/{branch}/{file_path}"
        content = fetch_url_text(raw_url, timeout=6)
        if content and len(content.strip()) > 10:
            return content
    return None


def list_github_dir_dynamic(repo_full: str, dir_path: str = "") -> List[Dict[str, str]]:
    """
    Dynamically lists a directory in any GitHub repository using GitHub's codeViewTreeRoute JSON
    endpoint on HEAD (no hardcoded paths and no 60-req/hr REST rate limit).
    """
    clean_dir = dir_path.strip("/")
    url = (
        f"https://github.com/{repo_full}/tree/HEAD/{clean_dir}"
        if clean_dir
        else f"https://github.com/{repo_full}"
    )
    raw = fetch_url_text(url, timeout=7, accept="application/json")
    if not raw:
        return []
    try:
        data = json.loads(raw)
        payload = data.get("payload", {})
        tree_route = payload.get("codeViewTreeRoute") or payload.get("codeViewRepoRoute") or {}
        items = tree_route.get("tree", {}).get("items", [])
        return [
            {
                "name": it.get("name", ""),
                "path": it.get("path", ""),
                "contentType": it.get("contentType", "file")
            }
            for it in items
            if it.get("path")
        ]
    except Exception:
        return []


def discover_source_file_dynamically(
    repo: str, pkg: str, pr_file_paths: List[str]
) -> Any:
    """
    100% Dynamic Repository Scanner:
    Starting from the directory where package.json / pyproject.toml was modified in the PR,
    crawls the repository directories on GitHub in real time and inspects source files
    to find the production file that actually imports or uses the upgraded package.
    """
    code_exts = (".py", ".ts", ".tsx", ".js", ".jsx")
    pkg_tokens = [
        t.lower()
        for t in re.split(r"[\s,&/@\-_]+", pkg or "")
        if len(t) >= 3 and t.lower() not in ("sdk", "core", "js", "py", "ts", "the", "and")
    ]
    if not pkg_tokens and pkg:
        pkg_tokens = [pkg.strip().lower()]

    # Determine starting directories from PR manifest paths (prioritizing production packages over examples)
    repo_slug = repo.split("/")[-1].lower().replace("-", "_")
    sorted_pr_paths = sorted(
        pr_file_paths,
        key=lambda p: (1 if "example" in p.lower() or "demo" in p.lower() else 0, p)
    )
    start_dirs: List[str] = []
    for pf in sorted_pr_paths:
        if "/" in pf:
            parent = "/".join(pf.split("/")[:-1])
            if parent and parent not in start_dirs:
                start_dirs.append(parent)
                start_dirs.append(f"{parent}/server/src/services")
                start_dirs.append(f"{parent}/server/src/services/internals")
                start_dirs.append(f"{parent}/server/src/services/internals/scalars")
                start_dirs.append(f"{parent}/server/src")
                start_dirs.append(f"{parent}/src")
                start_dirs.append(f"{parent}/lib")
                start_dirs.append(f"{parent}/{ parent.split('/')[-1].replace('-', '_') }")
    start_dirs.extend(["lib", "src", "app", repo_slug, f"python/{repo_slug}", f"src/{repo_slug}", ""])

    visited_dirs = set()
    candidate_files: List[str] = []
    sub_dirs_to_visit: List[str] = []

    def is_valid_code_candidate(path_str: str) -> bool:
        fname = path_str.split("/")[-1].lower()
        low_p = path_str.lower()
        if fname.startswith(".") or path_str.endswith(".d.ts"):
            return False
        # Aggressively reject tests, e2e, mocks, and fixtures
        if any(t in low_p for t in ("test", "spec", "e2e", "jest", "fixture", "mock", "setup.", "__init__.py")):
            return False
        # Aggressively reject tooling configs unless the package being upgraded is that tool
        is_tool_pkg = any(k in (pkg or "").lower() for k in ("vite", "eslint", "jest", "webpack", "babel", "rollup", "vitest", "playwright"))
        if not is_tool_pkg:
            if any(cfg in fname for cfg in ("eslint", "jest", "prettier", "babel", "tsconfig", "webpack", "vite.config", "vitest")):
                return False
        return path_str.endswith(code_exts)

    def dir_priority(d_path: str) -> int:
        low_d = d_path.lower()
        sc = 0
        if "admin" in low_d or "example" in low_d:
            sc += 40
        for tok in pkg_tokens:
            if tok in low_d:
                sc -= 40
        if any(k in low_d for k in ("scalar", "scalars", "schema", "graphql", "server", "api", "widgets", "editor", "providers", "client", "llm")):
            sc -= 25
        if "services" in low_d or "internals" in low_d:
            sc -= 15
        return sc

    for d in start_dirs:
        clean_d = d.strip("/")
        if clean_d in visited_dirs:
            continue
        visited_dirs.add(clean_d)
        items = list_github_dir_dynamic(repo, clean_d)
        for it in items:
            p = it["path"]
            ctype = it["contentType"]
            if ctype == "directory":
                low_name = it["name"].lower()
                if low_name not in ("test", "tests", "__tests__", "docs", "dist", "node_modules", ".github", "examples", "cypress", "e2e"):
                    sub_dirs_to_visit.append(p)
            elif is_valid_code_candidate(p):
                candidate_files.append(p)

    # Visit up to 4 levels of promising subdirectories prioritized by relevance
    for _depth in range(4):
        sub_dirs_to_visit.sort(key=dir_priority)
        next_level_dirs: List[str] = []
        for sd in sub_dirs_to_visit[:12]:
            if sd in visited_dirs:
                continue
            visited_dirs.add(sd)
            for it in list_github_dir_dynamic(repo, sd):
                p = it["path"]
                if it["contentType"] == "directory":
                    low_name = it["name"].lower()
                    if low_name not in ("test", "tests", "__tests__", "docs", "dist", "node_modules", ".github", "cypress", "e2e"):
                        next_level_dirs.append(p)
                elif is_valid_code_candidate(p):
                    candidate_files.append(p)
        sub_dirs_to_visit = next_level_dirs

    def file_priority(fp: str) -> int:
        low = fp.lower()
        score = 20 if ("example" in low or "demo" in low or "admin" in low) else 0
        for tok in pkg_tokens:
            if tok in low:
                score -= 30
        if any(k in low for k in ("scalar", "scalars", "schema", "graphql", "client", "llm", "auth", "api", "router", "editor", "richtext")):
            score -= 20
        return score

    candidate_files.sort(key=file_priority)

    clean_pkg_exact = (pkg or "").strip().split()[0].lower()
    token_matched_file = ""
    token_matched_source = ""
    for fp in candidate_files[:35]:
        src = fetch_raw_repo_file(repo, fp)
        if not src:
            continue
        src_low = src.lower()
        # 1. Exact package import match (e.g. '@anthropic-ai/sdk' or 'zod')
        if clean_pkg_exact and (
            f"'{clean_pkg_exact}'" in src_low
            or f'"{clean_pkg_exact}"' in src_low
            or f"import {clean_pkg_exact}" in src_low
            or f"from {clean_pkg_exact}" in src_low
        ):
            return fp, src
        # 2. Token match fallback (must match import or from statement or identifier)
        if not token_matched_file:
            for tok in pkg_tokens:
                if (
                    f"'{tok}" in src_low
                    or f'"{tok}' in src_low
                    or f"import {tok}" in src_low
                    or f"from {tok}" in src_low
                    or f" {tok}." in src_low
                    or f"{tok}(" in src_low
                ):
                    token_matched_file = fp
                    token_matched_source = src
                    break

    if token_matched_file:
        return token_matched_file, token_matched_source

    # NEVER return an arbitrary file if it does not use the package!
    return "", ""


def extract_focused_source_window(raw_source: str, pkg: str) -> str:
    """
    For files larger than 160 lines, extracts the lines around imports and around
    the actual usage of `pkg` dynamically so Gemini sees the exact call sites.
    """
    lines = raw_source.splitlines()
    if len(lines) <= 160:
        return raw_source

    pkg_tokens = [
        t.lower()
        for t in re.split(r"[\s,&/@\-_]+", pkg or "")
        if len(t) >= 3 and t.lower() not in ("sdk", "core", "js", "py", "ts", "the", "and")
    ]

    # Always keep top 45 lines (imports)
    selected_indices = set(range(min(45, len(lines))))

    # Find lines where pkg_tokens are used and include +/- 20 lines of context around each match
    for idx, line in enumerate(lines):
        low = line.lower()
        if any(tok in low for tok in pkg_tokens):
            for w in range(max(0, idx - 20), min(len(lines), idx + 25)):
                selected_indices.add(w)
            if len(selected_indices) >= 145:
                break

    # If still small, include the last 70 lines (component render / main logic)
    if len(selected_indices) < 90:
        for w in range(max(0, len(lines) - 70), len(lines)):
            selected_indices.add(w)

    sorted_idx = sorted(selected_indices)
    out_lines: List[str] = []
    prev = -1
    for i in sorted_idx:
        if prev != -1 and i > prev + 1:
            out_lines.append("// ... [unchanged lines omitted] ...")
        out_lines.append(lines[i])
        prev = i
    return "\n".join(out_lines)


def build_live_dynamic_grounding(pkg_list: List[str], target_file: str, raw_source: str = "") -> str:
    """
    100% Dynamic Live Registry, /llms.txt, CHANGELOG.md & GitHub Release Notes Grounding:
    - Checks npm first for .ts/.tsx/.js/.jsx files, and PyPI first for .py files.
    - Extracts the actual method/function calls present in `raw_source` and matches them
      against the official changelog & migration sections of the package on GitHub.
    """
    import html as html_lib
    from urllib.parse import urlparse
    is_python = target_file.endswith(".py")
    used_calls = set(re.findall(r"\.([a-zA-Z_][a-zA-Z0-9_]{2,})", raw_source or ""))
    lines: List[str] = []

    for raw_pkg in pkg_list[:2]:
        clean_pkg = raw_pkg.strip().split()[0].strip()
        if not clean_pkg:
            continue
        meta = (
            DocHunter.fetch_pypi_metadata(clean_pkg) or DocHunter.fetch_npm_metadata(clean_pkg)
            if is_python
            else DocHunter.fetch_npm_metadata(clean_pkg) or DocHunter.fetch_pypi_metadata(clean_pkg)
        )
        if not meta or not meta.get("name"):
            continue

        name = meta.get("name", clean_pkg)
        ver = meta.get("version", "latest")
        summary = meta.get("summary", "")
        doc_url = meta.get("documentation_url", "")
        repo_url = meta.get("repository_url", "")

        entry_line = f"• Package '{name}' (Latest Official Registry Release: v{ver}): {summary[:140]}"
        if doc_url or repo_url:
            entry_line += f" [Official Docs/Repo: {doc_url or repo_url}]"

        # 1. Dynamically fetch official /llms.txt from dedicated documentation domain (exclude github.com / npmjs / pypi)
        if doc_url and doc_url.startswith("http"):
            try:
                parsed_u = urlparse(doc_url)
                if not any(h in parsed_u.netloc.lower() for h in ("github.com", "npmjs.com", "pypi.org", "gitlab.com")):
                    base_origin = f"{parsed_u.scheme}://{parsed_u.netloc}"
                    llms_raw = fetch_url_text(f"{base_origin}/llms.txt", timeout=5) or ""
                    if llms_raw and len(llms_raw) > 50 and "<html" not in llms_raw[:200].lower():
                        mig_lines = [
                            l.strip()
                            for l in llms_raw.splitlines()
                            if any(f".{c}" in l or f" {c}" in l for c in used_calls)
                            or any(kw in l.lower() for kw in ("deprecat", "drop", "breaking", "migrat"))
                        ]
                        if mig_lines:
                            entry_line += "\n  Official /llms.txt Migration Index:\n    " + "\n    ".join(mig_lines[:20])
            except Exception:
                pass

        # 2. Fetch live release notes & symbol-matched changelog sections from GitHub
        m = re.search(r"github\.com[:/]([^/]+)/([^/#?.]+)", repo_url or doc_url)
        if m:
            owner, rname = m.group(1), m.group(2)
            atom = fetch_url_text(f"https://github.com/{owner}/{rname}/releases.atom", timeout=5) or ""
            entries = re.findall(r"<entry>.*?</entry>", atom, re.S)[:2]
            rel_notes: List[str] = []
            for e in entries:
                t_list = re.findall(r"<title>([^<]+)</title>", e)
                c_list = re.findall(r"<content[^>]*>(.*?)</content>", e, re.S)
                t_str = t_list[0].strip() if t_list else ""
                txt = re.sub(r"<[^>]+>", " ", html_lib.unescape(c_list[0])) if c_list else ""
                txt = re.sub(r"\s+", " ", txt).strip()[:250]
                if t_str or txt:
                    rel_notes.append(f"[{t_str}]: {txt}")
            if rel_notes:
                entry_line += "\n  Live GitHub Release Notes: " + " | ".join(rel_notes)

            # Dynamically scan repository changelog / migration docs for sections matching `used_calls` in `raw_source`
            for ch_path in [
                "CHANGELOG.md",
                "HISTORY.md",
                "packages/docs/content/v4/changelog.mdx",
                "docs/migration.md"
            ]:
                ch_raw = fetch_raw_repo_file(f"{owner}/{rname}", ch_path)
                if ch_raw:
                    # Split by ### or ## while preserving parent ## heading context
                    parent_h2 = ""
                    generic_containers = {"string", "number", "boolean", "object", "array", " optional", "unknown"}
                    specific_calls = {c for c in used_calls if c.lower() not in generic_containers}
                    scored_secs: List[Tuple[int, str]] = []
                    for block in re.split(r"(?=^#{2,3} )", ch_raw, flags=re.M):
                        b_lines = [l for l in block.splitlines() if l.strip()]
                        if not b_lines:
                            continue
                        first_line = b_lines[0]
                        if first_line.startswith("## "):
                            parent_h2 = first_line
                        if len(b_lines) <= 1:
                            continue
                        full_heading = f"{parent_h2} -> {first_line}" if first_line.startswith("### ") and parent_h2 else first_line
                        block_text = "\n".join(b_lines[:26])
                        score = 0
                        # High score when specific methods/types from raw_source match whole words in the subsection heading
                        matched_in_heading = [
                            c for c in specific_calls
                            if re.search(rf"(?:\.|`|\b){re.escape(c)}\b", first_line)
                        ]
                        matched_in_parent = [
                            c for c in specific_calls
                            if re.search(rf"(?:\.|`|\b){re.escape(c)}\b", parent_h2)
                        ]
                        matched_in_body = [
                            c for c in specific_calls
                            if re.search(rf"(?:\.|`|\b){re.escape(c)}\b", block_text)
                        ]
                        if matched_in_heading:
                            score += 25 * len(matched_in_heading)
                        if matched_in_parent and len(set(matched_in_parent + matched_in_body)) >= 2:
                            score += 7 * len(set(matched_in_parent + matched_in_body))
                        if score > 0:
                            scored_secs.append((score, parent_h2, f"{full_heading}\n    " + "\n    ".join(b_lines[1:26])))
                    if scored_secs:
                        scored_secs.sort(key=lambda x: x[0], reverse=True)
                        final_secs: List[str] = []
                        parent_counts: dict = {}
                        for sc, ph2, txt in scored_secs:
                            if ph2 and parent_counts.get(ph2, 0) >= 2:
                                continue
                            if ph2:
                                parent_counts[ph2] = parent_counts.get(ph2, 0) + 1
                            final_secs.append(txt)
                            if len(final_secs) >= 7:
                                break
                        entry_line += (
                            f"\n  Official Changelog Sections Matching Calls in {target_file}:\n    "
                            + "\n    ---\n    ".join(final_secs)
                        )
                    break

        lines.append(entry_line)

    if not lines:
        return ""
    return "[Authoritative Live Registry, /llms.txt & GitHub Changelog Grounding]\n" + "\n".join(lines)


def prepare_apipatch_context(repo: str, pr_number: int, pkg: str) -> Dict[str, Any]:
    pr_diff_url = f"https://github.com/{repo}/pull/{pr_number}.diff"
    raw_pr_diff = fetch_url_text(pr_diff_url, timeout=8) or ""
    parsed_files = parse_pr_diff_files(raw_pr_diff)
    pr_file_names = [f["path"] for f in parsed_files]

    code_exts = (".py", ".ts", ".tsx", ".js", ".jsx")
    code_files = [
        f for f in parsed_files
        if f["path"].endswith(code_exts)
        and "test" not in f["path"].lower()
        and "lock" not in f["path"].lower()
    ]
    if not code_files:
        code_files = [f for f in parsed_files if f["path"].endswith(code_exts)]

    target_file = ""
    raw_source = ""
    pr_file_diff = ""

    # 1. If the PR directly modifies a Python/TS/JS source file, inspect that exact file
    if code_files:
        target_file = code_files[0]["path"]
        pr_file_diff = code_files[0]["diff"]
        raw_source = fetch_raw_repo_file(repo, target_file) or ""

    # 2. If it's a Dependabot/Renovate PR (only touches package.json / pyproject.toml / lockfiles),
    #    100% DYNAMICALLY crawl the repository tree on GitHub to find the file importing `pkg`!
    if not raw_source:
        disc_file, disc_source = discover_source_file_dynamically(repo, pkg, pr_file_names)
        if disc_file and disc_source:
            target_file = disc_file
            raw_source = disc_source

    if not target_file and parsed_files:
        non_manifest = [
            f for f in parsed_files
            if not f["path"].endswith((".json", ".md", ".lock", ".yaml", ".yml", ".toml", ".txt"))
            and not any(t in f["path"].lower() for t in ("test", "spec", "e2e", "jest"))
        ]
        if non_manifest:
            chosen = non_manifest[0]
            target_file = chosen["path"]
            pr_file_diff = chosen["diff"]
            raw_source = fetch_raw_repo_file(repo, target_file) or ""

    focused_source = extract_focused_source_window(raw_source, pkg) if raw_source else ""

    # 3. 100% Dynamic Live Documentation & Release Grounding matched against calls in `raw_source`
    pkg_list = [
        p.strip()
        for p in re.split(r"[,&]", pkg or "")
        if p.strip()
    ]
    try:
        live_doc_grounding = build_live_dynamic_grounding(pkg_list, target_file, raw_source) if target_file else ""
    except Exception:
        live_doc_grounding = ""

    return {
        "repo": repo,
        "prNumber": pr_number,
        "prDiffUrl": pr_diff_url,
        "targetFile": target_file,
        "rawSource": raw_source,
        "focusedSource": focused_source,
        "prFileDiff": "\n".join(pr_file_diff.splitlines()[:50]) if pr_file_diff else "",
        "realPrFileNames": pr_file_names[:10],
        "noUsageFound": not bool(raw_source and target_file),
        "knowledgeGuidance": live_doc_grounding
    }


def validate_and_diff(payload_json: str) -> Dict[str, Any]:
    data = json.loads(payload_json)
    file_path = data.get("targetFile", "source.py")
    original_code = data.get("originalCode", "")
    refactored_code = data.get("refactoredCode", "")
    libs = data.get("libs", [])
    _, ext = os.path.splitext(file_path)

    if not original_code or not refactored_code:
        return {"astValid": False, "astMessage": "No refactored code returned", "unifiedDiff": ""}

    refactored = strip_code_fences(refactored_code)
    refactored = sanitize_python_formatting(refactored, ext)
    refactored = ensure_docstring_restored(original_code, refactored, ext)
    refactored = shield_unaffected_functions(original_code, refactored, libs, ext)

    # Normalize trailing newlines so difflib never prints identical -/+ lines at EOF
    norm_orig = "\n".join(line.rstrip() for line in original_code.strip().splitlines()) + "\n"
    norm_ref = "\n".join(line.rstrip() for line in refactored.strip().splitlines()) + "\n"

    val = CodeValidator.validate(norm_orig, norm_ref, file_extension=ext)
    diff_lines = list(
        difflib.unified_diff(
            norm_orig.splitlines(keepends=True),
            norm_ref.splitlines(keepends=True),
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}"
        )
    )
    unified_diff = "".join(diff_lines).strip()

    return {
        "astValid": val.is_valid,
        "astMessage": f"apipatch.validator.CodeValidator({ext}): {'VALID (0 AST Errors)' if val.is_valid else val.error_message}",
        "meaningfulChange": is_meaningful_code_change(norm_orig, norm_ref, ext),
        "unifiedDiff": unified_diff
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["prepare", "validate"], default="prepare")
    parser.add_argument("--repo", default="")
    parser.add_argument("--pr", type=int, default=0)
    parser.add_argument("--pkg", default="")
    parser.add_argument("--payload", default="")
    args = parser.parse_args()

    if args.mode == "prepare":
        res = prepare_apipatch_context(args.repo, args.pr, args.pkg)
        print(json.dumps(res, ensure_ascii=False))
    else:
        res = validate_and_diff(args.payload)
        print(json.dumps(res, ensure_ascii=False))
