"""
ApiPatch Rules & High-Precision Pattern Transformers
Provides zero-latency, offline, deterministic refactoring for high-frequency breaking changes.
"""

import re
from typing import Dict, Any, List, Optional
from apipatch.validator import CodeValidator


class RuleTransform:
    def __init__(
        self,
        library: str,
        name: str,
        deprecated_symbol: str,
        replacement_symbol: str,
        description: str,
        detection_pattern: re.Pattern,
        transform_func
    ):
        self.library = library
        self.name = name
        self.deprecated_symbol = deprecated_symbol
        self.replacement_symbol = replacement_symbol
        self.description = description
        self.detection_pattern = detection_pattern
        self.transform_func = transform_func


def transform_pydantic_v2(code: str) -> str:
    """Refactors Pydantic v1 Config, parse_obj, and json methods to Pydantic v2."""
    updated = code

    # 1. Update imports
    if "from pydantic import" in updated and "ConfigDict" not in updated:
        updated = re.sub(
            r"from\s+pydantic\s+import\s+([^#\n]+)",
            lambda m: f"from pydantic import {m.group(1).strip()}, ConfigDict" if "BaseModel" in m.group(1) else m.group(0),
            updated,
            count=1
        )

    # 2. Indentation-aware transform for class Config:
    lines = updated.splitlines(keepends=True)
    out_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^(\s*)class\s+Config\s*:\s*$", line)
        if m:
            indent = m.group(1)
            config_lines = []
            i += 1
            while i < len(lines):
                sub_line = lines[i]
                if not sub_line.strip():
                    if config_lines:
                        break
                    i += 1
                    continue
                sub_indent = len(sub_line) - len(sub_line.lstrip())
                if sub_indent > len(indent):
                    config_lines.append(sub_line)
                    i += 1
                else:
                    break

            body = "".join(config_lines)
            from_attr = "orm_mode" in body or "from_attributes" in body
            pop_name = "allow_population_by_field_name" in body or "populate_by_name" in body
            args = []
            if from_attr:
                args.append("from_attributes=True")
            if pop_name:
                args.append("populate_by_name=True")
            args_str = ", ".join(args) if args else ""
            out_lines.append(f"{indent}model_config = ConfigDict({args_str})\n")
        else:
            out_lines.append(line)
            i += 1

    updated = "".join(out_lines)

    # 3. parse_obj -> model_validate
    updated = re.sub(r"\.parse_obj\(", ".model_validate(", updated)

    # 4. .json() -> .model_dump_json()
    updated = re.sub(r"(\b[a-zA-Z0-9_]+)\.json\(\)", r"\1.model_dump_json()", updated)

    # 5. .dict() -> .model_dump()
    updated = re.sub(r"(\b[a-zA-Z0-9_]+)\.dict\(\)", r"\1.model_dump()", updated)

    return updated


def transform_openai_v1(code: str) -> str:
    """Refactors OpenAI v0.x module-level calls to OpenAI v1.0+ client instances."""
    updated = code

    # Check if client initialization already exists
    has_client = "client = openai.OpenAI()" in updated or "client = OpenAI(" in updated

    # Replace ChatCompletion
    if "openai.ChatCompletion.create(" in updated:
        if not has_client:
            # Inject client before call
            updated = re.sub(
                r"(\s*)([a-zA-Z0-9_]+\s*=\s*)openai\.ChatCompletion\.create\(",
                r"\1client = openai.OpenAI()\n\1\2client.chat.completions.create(",
                updated,
                count=1
            )
            # Subsequent calls use client
            updated = re.sub(r"openai\.ChatCompletion\.create\(", "client.chat.completions.create(", updated)
        else:
            updated = re.sub(r"openai\.ChatCompletion\.create\(", "client.chat.completions.create(", updated)

    # Replace dictionary subscript response with dot notation
    updated = re.sub(
        r"([a-zA-Z0-9_]+)\['choices'\]\[0\]\['message'\]\['content'\]",
        r"\1.choices[0].message.content",
        updated
    )

    return updated


def transform_stripe_payment_intents(code: str) -> str:
    """Refactors Stripe Charge.create to PaymentIntent.create."""
    updated = code
    # stripe.Charge.create -> stripe.PaymentIntent.create
    updated = re.sub(r"stripe\.Charge\.create\(", "stripe.PaymentIntent.create(", updated)
    updated = re.sub(r"source=([a-zA-Z0-9_]+)", r"payment_method_types=['card']", updated)
    return updated


def transform_langchain_lcel(code: str) -> str:
    """Refactors legacy LangChain LLMChain to LCEL pipe syntax."""
    updated = code
    # Remove LLMChain import
    updated = re.sub(r"from\s+langchain\.chains\s+import\s+LLMChain\s*\n?", "", updated)
    # chain = LLMChain(llm=llm, prompt=prompt) -> chain = prompt | llm
    updated = re.sub(
        r"([a-zA-Z0-9_]+)\s*=\s*LLMChain\s*\(\s*llm=([a-zA-Z0-9_]+),\s*prompt=([a-zA-Z0-9_]+)\s*\)",
        r"\1 = \3 | \2",
        updated
    )
    # chain.predict(key=val) -> chain.invoke({'key': val})
    updated = re.sub(
        r"([a-zA-Z0-9_]+)\.predict\(([a-zA-Z0-9_]+)=([^\)]+)\)",
        r"\1.invoke({'\2': \3})",
        updated
    )
    return updated


def transform_supabase_v2(code: str) -> str:
    """Refactors Supabase v1 auth methods to v2 dict credentials."""
    updated = code
    # supabase.auth.sign_in(email=..., password=...) -> supabase.auth.sign_in_with_password({'email': ..., 'password': ...})
    updated = re.sub(
        r"(\b[a-zA-Z0-9_]+\.auth)\.sign_in\(\s*email=([^,]+),\s*password=([^)]+)\)",
        r"\1.sign_in_with_password({'email': \2, 'password': \3})",
        updated
    )
    return updated


RULES_REGISTRY: List[RuleTransform] = [
    RuleTransform(
        library="Pydantic",
        name="pydantic_v2_migration",
        deprecated_symbol="class Config / parse_obj() / .json()",
        replacement_symbol="model_config = ConfigDict() / model_validate() / model_dump_json()",
        description="Pydantic v2 replaced Config class, parse_obj, and json with modern model_* methods",
        detection_pattern=re.compile(r"class\s+Config\s*:|\.parse_obj\(|\.dict\(\)"),
        transform_func=transform_pydantic_v2
    ),
    RuleTransform(
        library="OpenAI",
        name="openai_v1_migration",
        deprecated_symbol="openai.ChatCompletion.create",
        replacement_symbol="client.chat.completions.create",
        description="OpenAI v1.0+ module-level methods replaced by client instances",
        detection_pattern=re.compile(r"openai\.ChatCompletion\.create"),
        transform_func=transform_openai_v1
    ),
    RuleTransform(
        library="Stripe",
        name="stripe_payment_intents",
        deprecated_symbol="stripe.Charge.create",
        replacement_symbol="stripe.PaymentIntent.create",
        description="Stripe Charges API deprecated for card payments in favor of PaymentIntents (SCA/3DS standard)",
        detection_pattern=re.compile(r"stripe\.Charge\.create"),
        transform_func=transform_stripe_payment_intents
    ),
    RuleTransform(
        library="LangChain",
        name="langchain_lcel",
        deprecated_symbol="LLMChain(llm, prompt) & .predict()",
        replacement_symbol="prompt | llm & .invoke()",
        description="LangChain legacy chains deprecated in favor of LangChain Expression Language (LCEL)",
        detection_pattern=re.compile(r"LLMChain\("),
        transform_func=transform_langchain_lcel
    ),
    RuleTransform(
        library="Supabase",
        name="supabase_v2_auth",
        deprecated_symbol="supabase.auth.sign_in(email, password)",
        replacement_symbol="supabase.auth.sign_in_with_password({'email': ..., 'password': ...})",
        description="Supabase v2 restructured authentication methods to accept dictionary payloads",
        detection_pattern=re.compile(r"\.auth\.sign_in\("),
        transform_func=transform_supabase_v2
    ),
]


class RulesEngine:
    @staticmethod
    def apply_rules(code: str, file_path: str = "temp.py") -> Dict[str, Any]:
        """Applies deterministic pattern transforms and validates the outcome."""
        detected_issues = []
        refactored = code

        for rule in RULES_REGISTRY:
            if rule.detection_pattern.search(refactored):
                detected_issues.append({
                    "library": rule.library,
                    "deprecated_symbol": rule.deprecated_symbol,
                    "replacement_symbol": rule.replacement_symbol,
                    "description": rule.description,
                    "line_hint": rule.name
                })
                try:
                    transformed = rule.transform_func(refactored)
                    # Validate syntax before adopting transformed code
                    if file_path.endswith(".py"):
                        val = CodeValidator.validate_python_syntax(transformed)
                        if val.is_valid:
                            refactored = transformed
                    else:
                        refactored = transformed
                except Exception:
                    pass

        return {
            "has_breaking_changes": len(detected_issues) > 0,
            "detected_issues": detected_issues,
            "refactored_code": refactored
        }
