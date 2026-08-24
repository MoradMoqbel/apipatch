"""
ApiPatch Authoritative Migration Knowledge Base
Provides exact, up-to-date SDK migration rules, official code patterns, and modern replacements
for major third-party libraries across Python, JavaScript, TypeScript, and more.
This ensures the AI agent always migrates to 100% working, modern official SDK implementations
without hallucinations or placeholder exceptions.
"""

from typing import List, Dict, Set, Optional, Any


# Authoritative, verified migration knowledge for major ecosystems
MIGRATION_KNOWLEDGE_BASE: Dict[str, Dict[str, Any]] = {
    "google": {
        "aliases": ["google", "google-genai", "google.genai", "google-generativeai", "gemini", "generativelanguage"],
        "description": "Google GenAI SDK (google.genai) and Gemini 3 / Nano Banana Image Generation",
        "guidance": """\
• Google GenAI Migration Guidelines (Latest Official 2025/2026 SDK):
  - Package: 'google-genai' (Import: 'from google import genai', 'from google.genai import types')
  - Initialization: client = genai.Client(api_key=...)
  - Synchronous Calls:
      response = client.models.generate_content(
          model="gemini-2.5-flash",
          contents=["..."]
      )
  - Asynchronous Calls (inside `async def` with `await`):
      response = await client.aio.models.generate_content(
          model="gemini-2.5-flash",
          contents=["..."]
      )
  - Image Generation & Editing (Nano Banana / Gemini 3 Image):
      Official Models: 'gemini-3.1-flash-image', 'gemini-3-pro-image', 'gemini-3.1-flash-lite-image', 'gemini-2.5-flash-image'
      Usage:
          response = client.models.generate_content(
              model="gemini-3.1-flash-image",
              contents=[prompt],
              config=types.GenerateContentConfig(
                  response_modalities=["IMAGE"],
                  response_format={"image": {"aspect_ratio": "16:9"}}
              )
          )
          for part in response.parts:
              if part.inline_data is not None:
                  image = part.as_image()
                  image.save("output.png")
  - NEVER use raw deprecated REST endpoints or raise NotImplementedError when updating Gemini code; migrate directly to google.genai Client.
"""
    },

    "openai": {
        "aliases": ["openai"],
        "description": "OpenAI Python & TypeScript v1.0+ SDK",
        "guidance": """\
• OpenAI v1.0+ Migration Guidelines:
  - Python Initialization: from openai import OpenAI; client = OpenAI(api_key=...)
  - Chat: client.chat.completions.create(model="gpt-4o", messages=[...])
  - Embeddings: client.embeddings.create(model="text-embedding-3-small", input=...)
  - Response parsing: Access via attributes (e.g. response.choices[0].message.content) instead of dict subscripting (response['choices']).
  - TS/JS Initialization: import OpenAI from 'openai'; const client = new OpenAI({ apiKey: ... });
"""
    },

    "langchain": {
        "aliases": ["langchain", "langchain-core", "langchain-community", "langchain-openai"],
        "description": "LangChain v0.2 / v0.3+ and LCEL Migration",
        "guidance": """\
• LangChain Modern Guidelines (v0.2/v0.3+ LCEL):
  - Model Imports: Use partner packages (e.g. 'from langchain_openai import ChatOpenAI' instead of 'from langchain.chat_models import ChatOpenAI').
  - Core Schemas: 'from langchain_core.messages import SystemMessage, HumanMessage, AIMessage'
  - Prompts: 'from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder'
  - Chains: Migrate 'LLMChain' to LCEL pipe syntax: chain = prompt | llm | StrOutputParser()
  - Execution: Use 'chain.invoke({...})' or 'agent_executor.invoke({...})' instead of deprecated '.run(...)'.
  - Tools: Import community tools from 'langchain_community.tools' (e.g. from langchain_community.tools.ddg import DuckDuckGoSearchRun).
"""
    },

    "pydantic": {
        "aliases": ["pydantic"],
        "description": "Pydantic v2.0+ Modernization",
        "guidance": """\
• Pydantic v2 Migration Guidelines:
  - Configuration: Replace inner 'class Config:' with 'model_config = ConfigDict(from_attributes=True, ...)'
  - Exports: Replace '.dict()' with '.model_dump()', and '.json()' with '.model_dump_json()'
  - Validators: Replace '@validator' with '@field_validator' or '@model_validator(mode="after")'
  - BaseSettings: Import from 'pydantic_settings import BaseSettings, SettingsConfigDict'
"""
    },

    "stripe": {
        "aliases": ["stripe"],
        "description": "Stripe Python SDK Modernization",
        "guidance": """\
• Stripe Modern Guidelines:
  - Initialization: stripe_client = stripe.StripeClient(api_key=...)
  - Charges/Payments: stripe_client.charges.create(...) or stripe_client.payment_intents.create(...)
"""
    },

    "supabase": {
        "aliases": ["supabase", "@supabase/supabase-js"],
        "description": "Supabase v2 Auth & Database SDK",
        "guidance": """\
• Supabase v2 Migration Guidelines:
  - JS Auth: supabase.auth.signInWithPassword({ email, password }) instead of supabase.auth.signIn()
  - JS User: supabase.auth.getUser() instead of supabase.auth.user()
  - Python: from supabase import create_client, Client; supabase = create_client(url, key)
"""
    },

    "anthropic": {
        "aliases": ["anthropic", "@anthropic-ai/sdk"],
        "description": "Anthropic Claude Messages API",
        "guidance": """\
• Anthropic Claude Modern Guidelines:
  - Python: from anthropic import Anthropic; client = Anthropic()
  - Messages API: client.messages.create(model="claude-3-5-sonnet-20241022", max_tokens=1024, messages=[{"role": "user", "content": ...}])
"""
    },

    "dotenv": {
        "aliases": ["dotenv", "python-dotenv", "python_dotenv"],
        "description": "Python Dotenv (python-dotenv)",
        "guidance": """\
• Python-Dotenv Guidelines:
  - Import: 'from dotenv import load_dotenv' or 'import dotenv'
  - Standard Usage: 'load_dotenv()' is the official, fully supported method.
  - DO NOT replace 'load_dotenv()' with 'dotenv_values()' or manual os.environ dictionary loops.
  - Leave 'load_dotenv()' untouched if it is already present.
"""
    },

    "fastapi": {
        "aliases": ["fastapi"],
        "description": "FastAPI Lifespan Events Modernization",
        "guidance": """\
• FastAPI Modern Guidelines:
  - Replace deprecated '@app.on_event("startup")' and '@app.on_event("shutdown")' with lifespan context manager:
      @asynccontextmanager
      async def lifespan(app: FastAPI):
          # startup logic
          yield
          # shutdown logic
      app = FastAPI(lifespan=lifespan)
"""
    }
}


from apipatch.doc_hunter import DocHunter


def get_relevant_knowledge(
    detected_libraries: Optional[List[str]] = None,
    file_content: Optional[str] = None
) -> str:
    """
    Extracts authoritative, focused migration instructions and live package documentation
    for the libraries actively detected in the target file or project.
    """
    selected_guidance: List[str] = []
    matched_keys: Set[str] = set()

    # Collect search tokens
    tokens: Set[str] = set()
    raw_libs: List[str] = list(detected_libraries or [])
    if detected_libraries:
        for lib in detected_libraries:
            tokens.add(lib.lower().strip())
            if '/' in lib:
                tokens.add(lib.split('/')[1].lower().strip())

    if file_content:
        lower_code = file_content.lower()
        for key, entry in MIGRATION_KNOWLEDGE_BASE.items():
            for alias in entry["aliases"]:
                if alias in lower_code or alias.replace('-', '_') in lower_code:
                    tokens.add(key)
                    break

    for key, entry in MIGRATION_KNOWLEDGE_BASE.items():
        if key in tokens or any(alias in tokens for alias in entry["aliases"]):
            if key not in matched_keys:
                matched_keys.add(key)
                selected_guidance.append(entry["guidance"])

    knowledge_text = ""
    if selected_guidance:
        knowledge_text = "### 📚 Authoritative Modern SDK Migration Rules:\n" + "\n".join(selected_guidance)

    # Append live package grounding from DocHunter
    if raw_libs:
        live_grounding = DocHunter.build_grounded_context(raw_libs)
        if live_grounding:
            if knowledge_text:
                knowledge_text += "\n\n" + live_grounding
            else:
                knowledge_text = live_grounding

    return knowledge_text
