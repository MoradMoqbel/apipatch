# ⚡ ApiPatch
> **Autonomous AI Agent for API Breaking Changes & Self-Maintaining Codebases**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/badge/pypi-v0.6.0-brightgreen.svg)](https://pypi.org/project/apipatch/)
[![Open Source](https://img.shields.io/badge/Open%20Source-Yes-brightgreen.svg)](https://github.com/MoradMoqbel/apipatch)
[![Tests: Passing](https://img.shields.io/badge/Tests-76%2F76%20Passing-brightgreen.svg)](https://github.com/MoradMoqbel/apipatch)

---

## 🛑 The Problem

Over **30% of cloud outages and broken builds** are caused by silent, third-party API breaking changes. When vendors release major SDK updates (OpenAI v1.0+, Pydantic v2, Stripe SCA/PaymentIntents, LangChain LCEL, React hooks, Next.js App Router…), engineering teams spend days hunting broken calls and rewriting legacy code.

Tools like **Dependabot** and **Renovate** only bump version numbers in `requirements.txt` or `package.json`—they **do not fix actual code logic**.

```
[ Traditional Dependency Bumper ]
  requirements.txt: openai==0.28.0 ──► openai==1.50.0 ──❌ (Code breaks at runtime!)

[ ApiPatch Autonomous Agent ]
  1. Detects breaking API calls across ANY library — Python, JS, TS, JSX, TSX…
  2. Refactors code via LLM reasoning (Gemini 2.5 Flash Lite, Claude, GPT-4o)
  3. Validates safety & self-heals syntax/structure via AST feedback loop
  4. Generates ready-to-merge Pull Requests ───────────────────────✅ (Build passes!)
```

---

## 🚀 Key Features

* 🌟 **Smart 2026 Repository Discovery (`apipatch discover`):** Automatically finds trending, active, non-archived repositories updated in the last 30 days and audits them for breaking changes.
* 🤖 **Autonomous GitHub PR Pipeline (`apipatch pr`):** Scans an entire remote repository, auto-forks/branches, commits refactorings via atomic Git Database API, and opens live Pull Requests.
* ⚡ **10x Faster Parallel Auditing:** Inspects multiple candidate files concurrently using multi-threaded asynchronous workers (`ThreadPoolExecutor`).
* 🩺 **AST Self-Healing Feedback Loop:** Automatically catches any LLM syntax errors or dropped functions and directs the AI to self-heal before outputting code.
* 💡 **Optimized `gemini-2.5-flash-lite` Engine:** Sub-second dynamic reasoning with smooth quota pacing and automated fallbacks.
* ⚡ **GitHub App & Webhook Daemon (`apipatch webhook`):** Listens for repository `push` events, verifies HMAC signatures, and autonomously runs the audit & PR pipeline in the background.
* 🔑 **Smart Token Discovery:** Automatically resolves GitHub tokens from CLI flags, `GITHUB_TOKEN` / `GH_TOKEN` env, `github_token.txt` file, or `.env`.
* 🧠 **Universal LLM Engine:** Audits **ANY** third-party library in **any language** dynamically — no hardcoded rules required.
* 🌐 **Multi-Language Support:** Full support for `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.mjs`, `.cjs` files.
* 🛡️ **AST & Safety Guard:** Validates every refactored Python file through AST syntax parsing. JS/TS files checked for truncation and brace/bracket balance.
* 📦 **Flexible CLI:** Rich terminal interface with `discover`, `pr`, `scan`, `fix --write`, `detect`, `hunt`, `webhook`, and **`--output report.json`**.
* 🔄 **Safe In-Place Refactoring:** Automatically generates `.bak` backups before modifying local files.

---

## 🌍 Universal Coverage — Any Library, Any Language

ApiPatch is not limited to a fixed list of rules. The LLM engine can detect and fix breaking changes in **any** third-party library it has been trained on, including:

| Language | Libraries / Frameworks |
| :--- | :--- |
| **Python** | OpenAI (v0.x → v1.x), Pydantic (v1 → v2 `@field_validator`), Stripe (Charge → PaymentIntent), LangChain (LLMChain → LCEL), Supabase, SQLAlchemy, FastAPI, Boto3/AWS, Celery, HuggingFace, and more |
| **JavaScript / TypeScript** | React (class → hooks), Next.js (Pages → App Router), Axios, Stripe.js, Supabase JS, OpenAI Node SDK, Express, and more |
| **Any Language** | If the LLM knows about a library's breaking change, ApiPatch can fix it |

---

## ⚡ Quickstart

### 1. Installation

```bash
pip install apipatch
```

#### Or install from Git:
```bash
pip install git+https://github.com/MoradMoqbel/apipatch.git
```

---

## 🔑 Setting Up AI & GitHub Tokens

### AI Provider Keys
Create a `.env` file in your directory or export variables:
```bash
# Google Gemini (Fastest & Free Tier Available)
GEMINI_API_KEY="AIzaSy..."

# OpenAI
OPENAI_API_KEY="sk-..."

# Anthropic Claude
ANTHROPIC_API_KEY="sk-ant-..."
```

### GitHub Token Setup
ApiPatch automatically resolves your GitHub token in this priority:
1. `--token <ghp_...>` CLI option
2. `GITHUB_TOKEN` or `GH_TOKEN` environment variable
3. `github_token.txt` in your working directory or project root
4. `.env` file

---

## 💻 CLI Commands & Usage

### 1. 🌟 Smart Active Repository Discovery (New in v0.6.0)
Discovers trending, modern 2026 repositories and audits them for breaking changes:
```bash
# Discover AI repositories updated in the last 30 days with 10+ stars
apipatch discover "topic:ai language:python" --days 30 --min-stars 10

# Discover FastAPI & LLM projects
apipatch discover "fastapi topic:ai" --days 30 --min-stars 10

# Submit live Pull Requests automatically on discovered repositories
apipatch discover "topic:llm language:python" --days 30 --submit
```

### 2. 🚀 Autonomous Live GitHub Pull Request
Audits an entire GitHub repository, forks if needed, commits modernized files, and opens a real live PR:
```bash
# Dry run / preview changes without opening PR
apipatch pr owner/repo --dry-run

# Open live PR on repository
apipatch pr owner/repo
```

### 3. 🎯 Proactive GitHub Code Hunter
Searches GitHub for legacy patterns with strict recency and star filters:
```bash
# Search for Pydantic v1 @validator in repositories updated in last 30 days
apipatch hunt "from pydantic import validator language:python" --days 30 --min-stars 10

# Search for OpenAI v0.x legacy calls
apipatch hunt "openai.ChatCompletion.create language:python" --days 60 --min-stars 10
```

### 4. ⚡ GitHub App Webhook Daemon
Runs the continuous webhook server to trigger autonomous PRs on every repository `push`:
```bash
apipatch webhook --port 8080 --secret "my_webhook_secret"
```

### 5. 🔍 Scan a Codebase Locally (Dry Run)
Audits local files recursively, detects deprecated calls, and outputs colorized diff previews:
```bash
apipatch scan /path/to/project
apipatch scan /path/to/project --provider gemini
```

### 6. ⚡ Refactor and Apply Fixes In-Place
Automatically updates local code with `.bak` safety backups:
```bash
apipatch fix /path/to/project --write
```

---

## 🧪 Testing

```bash
pytest
```

All 76 tests are offline-safe and mocked (no external network or live LLM required for the test suite).

---

## 🗺️ Roadmap

- [x] Universal LLM engine — no hardcoded rules, ANY library supported
- [x] Multi-language support: Python, JavaScript, TypeScript, JSX, TSX
- [x] AST Syntax & Safety Validator
- [x] Multi-LLM Provider (Gemini 2.5 Flash Lite, OpenAI, Claude) with auto-discovery
- [x] In-place refactoring with automatic backup (`--write`)
- [x] Automated test suite (76/76 tests passing)
- [x] **v0.5.0: Autonomous GitHub PR Engine (`apipatch pr`)**
- [x] **v0.5.0: GitHub App Webhook Daemon (`apipatch webhook`)**
- [x] **v0.6.0: Smart 2026 Repository Discovery Engine (`apipatch discover`)**
- [x] **v0.6.0: Multi-threaded parallel file auditing (10x performance boost)**
- [x] **v0.6.0: AST Self-Healing feedback loop**
- [x] PyPI Release (`pip install apipatch`)

---

## 📄 License

MIT License. Built by [Morad Moqbel](https://github.com/MoradMoqbel).
