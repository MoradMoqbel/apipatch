# ⚡ ApiPatch
> **Autonomous AI Agent for API Breaking Changes & Self-Maintaining Codebases**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/badge/pypi-v0.4.0-brightgreen.svg)](https://pypi.org/project/apipatch/)
[![Open Source](https://img.shields.io/badge/Open%20Source-Yes-brightgreen.svg)](https://github.com/MoradMoqbel/apipatch)
[![Tests: Passing](https://img.shields.io/badge/Tests-23%2F23%20Passing-brightgreen.svg)](https://github.com/MoradMoqbel/apipatch)

---

## 🛑 The Problem

Over **30% of cloud outages and broken builds** are caused by silent, third-party API breaking changes. When vendors release major SDK updates (OpenAI v1.0+, Pydantic v2, Stripe SCA/PaymentIntents, LangChain LCEL, React hooks, Next.js App Router…), engineering teams spend days hunting broken calls and rewriting legacy code.

Tools like **Dependabot** and **Renovate** only bump version numbers in `requirements.txt` or `package.json`—they **do not fix actual code logic**.

```
[ Traditional Dependency Bumper ]
  requirements.txt: openai==0.28.0 ──► openai==1.50.0 ──❌ (Code breaks at runtime!)

[ ApiPatch Autonomous Agent ]
  1. Detects breaking API calls across ANY library — Python, JS, TS, JSX, TSX…
  2. Refactors code via LLM reasoning (Gemini, Claude, GPT-4o)
  3. Validates safety before accepting any change
  4. Generates ready-to-merge Pull Requests ───────────────────────✅ (Build passes!)
```

---

## 🚀 Key Features

* 🧠 **Universal LLM Engine:** Audits **ANY** third-party library in **any language** dynamically — no hardcoded rules required.
* 🌐 **Multi-Language Support:** Full support for `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.mjs`, `.cjs` files.
* 🛡️ **AST & Safety Guard:** Validates every refactored Python file through AST syntax parsing. JS/TS files checked for truncation **and brace/bracket balance**.
* 🔁 **Automatic Retry:** Exponential backoff retry (3 attempts) on transient LLM/network errors — no silent failures.
* 📦 **Flexible CLI:** Rich terminal interface with `scan`, `fix --write`, `detect`, `hunt`, and now **`--output report.json`** for CI/CD pipelines.
* 🔄 **Safe In-Place Refactoring:** Automatically generates `.bak` backups before modifying any files.
* 🤖 **Proactive GitHub Hunter:** Searches public GitHub repositories for deprecated code patterns and drafts complete, structured Pull Requests.
* 🔌 **Multi-Provider:** Works with **Google Gemini** (free tier), **OpenAI GPT-4o**, and **Anthropic Claude** — auto-detected from environment variables.
* 📊 **JSON Report Output:** Save scan results with `--output report.json` for CI/CD integration.

---

## 🌍 Universal Coverage — Any Library, Any Language

ApiPatch is not limited to a fixed list of rules. The LLM engine can detect and fix breaking changes in **any** third-party library it has been trained on, including (but not limited to):

| Language | Libraries / Frameworks |
| :--- | :--- |
| **Python** | OpenAI, Pydantic, Stripe, LangChain, Supabase, SQLAlchemy, FastAPI, Boto3/AWS, Celery, HuggingFace, Twilio, and more |
| **JavaScript / TypeScript** | React (class → hooks), Next.js (Pages → App Router), Axios, Stripe.js, Supabase JS, OpenAI Node SDK, Express, and more |
| **Any Language** | If the LLM knows about a library's breaking change, ApiPatch can fix it |

---

## ⚡ Quickstart

### 1. Installation

```bash
pip install apipatch
```

#### Or install from Git (latest dev version):
```bash
pip install git+https://github.com/MoradMoqbel/apipatch.git
```

---

## 🔑 Setting Up AI Provider Keys

ApiPatch requires an LLM provider key for full analysis.

### Option A: Environment Variables (Recommended)

```bash
# Google Gemini (Fast & Free Tier Available)
export GEMINI_API_KEY="your-gemini-api-key-here"

# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic Claude
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY = "your-gemini-api-key-here"
```

### Option B: CLI Flags

```bash
apipatch scan ./project --provider gemini --api-key "your-key"
apipatch scan ./project --provider openai  --api-key "sk-..."
apipatch scan ./project --provider anthropic --api-key "sk-ant-..."
```

---

## 💻 CLI Commands & Usage

### 1. 🔍 Scan a Codebase (Dry Run)
Audits files recursively (`.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.mjs`, `.cjs`),
detects deprecated calls, and outputs colorized diff previews without modifying files:
```bash
apipatch scan /path/to/project
apipatch scan /path/to/project --provider gemini
```

### 2. ⚡ Refactor and Apply Fixes In-Place
Automatically updates the code and generates `.bak` safety backups:
```bash
apipatch fix /path/to/project --write
apipatch fix /path/to/single/file.py --write --provider openai
```
*(Add `--no-backup` to skip automatic `.bak` backup creation.)*

### 3. 📦 Discover All Project Dependencies
Inspects `requirements.txt`, `package.json`, `pyproject.toml`, and all source file
imports (Python AST + JS/TS regex) to list every third-party library in use:
```bash
apipatch detect /path/to/project
```

### 4. 🎯 Hunt for Deprecated Code on GitHub & Prepare PRs
Searches GitHub for legacy patterns and prepares ready-to-merge Pull Requests:
```bash
apipatch hunt "openai.ChatCompletion.create language:python"
apipatch hunt "stripe.Charge.create language:javascript"
```

---

## 🧪 Testing

```bash
python -m pytest tests/ -v
```

All 23 tests are offline-safe (no API key required for the test suite).

---

## 🗺️ Roadmap

- [x] Universal LLM engine — no hardcoded rules, ANY library supported
- [x] Multi-language support: Python, JavaScript, TypeScript, JSX, TSX
- [x] AST Syntax & Safety Validator
- [x] Multi-LLM Provider (Gemini, OpenAI, Claude) with auto-discovery
- [x] In-place refactoring with automatic backup (`--write`)
- [x] Autonomous dependency discovery (requirements.txt / package.json / AST scan)
- [x] Automated test suite (23/23 tests passing)
- [x] **v0.4.0: Retry with exponential backoff on LLM errors**
- [x] **v0.4.0: Token-limit protection (2500 line cap with warning)**
- [x] **v0.4.0: JS/TS brace-balance structural validator**
- [x] **v0.4.0: `--output report.json` for CI/CD pipelines**
- [x] **v0.4.0: Robust GitHub raw URL builder**
- [x] PyPI Release (`pip install apipatch`)
- [ ] 1-Click Autonomous GitHub App Webhook Integration

---

## 📄 License

MIT License. Built by [Morad Moqbel](https://github.com/MoradMoqbel).
