# ⚡ ApiPatch
> **Autonomous AI Agent for API Breaking Changes & Self-Maintaining Codebases**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Open Source](https://img.shields.io/badge/Open%20Source-Yes-brightgreen.svg)](https://github.com/MoradMoqbel/apipatch)
[![Tests: Passing](https://img.shields.io/badge/Tests-14%2F14%20Passing-brightgreen.svg)](https://github.com/MoradMoqbel/apipatch)

---

## 🛑 The Problem
Over **30% of cloud outages and broken builds** are caused by silent, third-party API breaking changes. When vendors release major SDK updates (such as OpenAI v1.0+, Pydantic v2, Stripe SCA/PaymentIntents, or LangChain LCEL), engineering teams spend days hunting broken calls and rewriting legacy code.

Tools like **Dependabot** and **Renovate** only bump version numbers in `requirements.txt` or `package.json`—they **do not fix actual code logic**.

```
[ Traditional Dependency Bumper ]
  requirements.txt: openai==0.28.0 ──> openai==1.50.0 ──❌ (Code breaks at runtime!)

[ ApiPatch Autonomous Agent ]
  1. Detects breaking API calls across ANY library
  2. Refactors syntax via AST & LLM reasoning
  3. Verifies syntax via AST Syntax Guard
  4. Generates ready-to-merge Pull Requests ──────────────✅ (Build passes immediately!)
```

---

## 🚀 Key Features

* 🧠 **Universal Dynamic Engine:** Audits **ANY** third-party library dynamically using LLMs (Google Gemini, Anthropic Claude, or OpenAI GPT-4o) without requiring hardcoded rules.
* ⚡ **Fast Deterministic AST Rules:** Includes built-in, zero-latency offline AST transformers for high-frequency migrations (OpenAI, Pydantic v2, Stripe, LangChain, Supabase, SQLAlchemy, etc.).
* 🛡️ **AST Syntax & Safety Guard:** Parses every refactored line through Python AST (`ast.parse`) before accepting it, guaranteeing 0% syntax errors and complete business logic preservation.
* 📦 **Flexible Native CLI Suite:** Rich terminal interface supporting `apipatch scan`, `apipatch fix --write`, `apipatch detect`, and `apipatch hunt`.
* 🔄 **Safe In-Place Refactoring:** Automatically generates `.bak` backups before modifying any files.
* 🤖 **Proactive GitHub Hunter:** Automatically searches public GitHub repositories for deprecated code patterns and drafts complete, structured Pull Requests.

---

## 🛡️ Out-of-the-Box Supported Patterns

| Provider / Library | Deprecated Pattern | Modern Standard |
| :--- | :--- | :--- |
| **OpenAI** | `openai.ChatCompletion.create` | `client.chat.completions.create` (v1.0+) |
| **Pydantic** | `class Config: orm_mode` / `.parse_obj()` | `model_config = ConfigDict` / `.model_validate()` (v2) |
| **Stripe** | `stripe.Charge.create` | `stripe.PaymentIntent.create` (SCA/3DS) |
| **LangChain** | `LLMChain(...)` & `.predict()` | `prompt \| llm` & `.invoke()` (LCEL) |
| **Supabase** | `supabase.auth.sign_in(email, pwd)` | `supabase.auth.sign_in_with_password({...})` |
| **SQLAlchemy** | `declarative_base()` | `class Base(DeclarativeBase): pass` (v2.0) |
| **FastAPI** | `@app.on_event("startup")` | `lifespan` context manager |
| **Universal / Any**| *Any 3rd-party library* | Dynamic LLM reasoning & AST transformation |

---

## ⚡ Quickstart

### 1. Installation

#### Direct install via Git:
```bash
pip install git+https://github.com/MoradMoqbel/apipatch.git
```

#### Or clone and install in editable mode:
```bash
git clone https://github.com/MoradMoqbel/apipatch.git
cd apipatch
pip install -e .
```

---

## 🔑 Setting Up AI Provider Keys (Gemini, OpenAI, Claude)

ApiPatch can run in **offline mode** (using built-in deterministic rules) or in **Dynamic AI Mode** (using an LLM to reason about any arbitrary library).

### 🔹 Option A: Configure Environment Variables (Recommended)

#### 1. Google Gemini (Fast & Free Tier Available):
* **Windows (PowerShell):**
  ```powershell
  $env:GEMINI_API_KEY = "your-gemini-api-key-here"
  ```
* **macOS / Linux (Bash):**
  ```bash
  export GEMINI_API_KEY="your-gemini-api-key-here"
  ```

#### 2. OpenAI:
* **Windows (PowerShell):**
  ```powershell
  $env:OPENAI_API_KEY = "sk-..."
  ```
* **macOS / Linux (Bash):**
  ```bash
  export OPENAI_API_KEY="sk-..."
  ```

#### 3. Anthropic Claude:
* **Windows (PowerShell):**
  ```powershell
  $env:ANTHROPIC_API_KEY = "sk-ant-..."
  ```
* **macOS / Linux (Bash):**
  ```bash
  export ANTHROPIC_API_KEY="sk-ant-..."
  ```

---

### 🔹 Option B: Pass API Keys directly via CLI Flags

You can also provide the key and provider directly in any command without setting environment variables:

```powershell
# Using Gemini
apipatch scan /path/to/project --provider gemini --api-key "your-key-here"

# Using OpenAI
apipatch scan /path/to/project --provider openai --api-key "sk-..."

# Using Anthropic Claude
apipatch scan /path/to/project --provider anthropic --api-key "sk-ant-..."
```

---

## 💻 CLI Commands & Usage

### 1. 🔍 Scan a Codebase (Dry Run)
Audits files recursively, detects deprecated calls, and outputs colorized diff previews without modifying files:
```bash
apipatch scan /path/to/project
```

### 2. ⚡ Refactor and Apply Fixes in-Place (`--write`)
Automatically updates the code in place and generates `.bak` safety backups:
```bash
apipatch fix /path/to/project --write
```
*(To disable automatic `.bak` backup creation, add `--no-backup`)*.

### 3. 📦 Discover Dependencies & Deprecation Rules
Inspects project manifests (`requirements.txt`, `package.json`, `pyproject.toml`) and AST imports:
```bash
apipatch detect /path/to/project
```

### 4. 🎯 Hunt for Deprecated Code on GitHub & Prepare PRs
Searches GitHub for legacy patterns and prepares ready-to-merge Pull Requests:
```bash
apipatch hunt "openai.ChatCompletion.create language:python"
```

---

## 🧪 Testing

Run the automated test suite to verify all engine modules and AST safety checks:
```bash
python -m unittest discover -s tests -p "test_*.py"
```

---

## 🗺️ Roadmap
- [x] Modern CLI package & `pyproject.toml` distribution (`apipatch`)
- [x] Universal Dynamic Zero-Rules LLM reasoning engine
- [x] AST Syntax & Safety Validator (0% syntax errors guarantee)
- [x] Multi-LLM Provider integration (Gemini, OpenAI, Claude)
- [x] In-place file modification with automatic backup (`--write`)
- [x] Automated dependency manifest & AST import extractor
- [x] Automated test suite (14/14 tests passing)
- [ ] 1-Click Autonomous GitHub App Webhook Integration
- [ ] PyPI Global Package Release

---

## 📄 License
MIT License. Built by [Morad Moqbel](https://github.com/MoradMoqbel).
