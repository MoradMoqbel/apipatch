# 🧪 ApiPatch Demo & Test Suite

This folder contains isolated real-world code snippets demonstrating deprecated API signatures across popular third-party SDKs.

---

## 📂 Included Test Cases

| File | Library | Deprecated Pattern | Modern Standard |
| :--- | :--- | :--- | :--- |
| **`target_sample.py`** | **OpenAI** | `openai.ChatCompletion.create` | `client.chat.completions.create` (v1.0+) |
| **`target_stripe.py`** | **Stripe** | `stripe.Charge.create` | `stripe.PaymentIntent.create` (SCA standard) |
| **`target_pydantic.py`**| **Pydantic** | `class Config: orm_mode` / `parse_obj` | `model_config = ConfigDict` / `model_validate` (v2) |
| **`target_langchain.py`**| **LangChain**| `LLMChain(...)` & `.predict()` | `prompt \| llm` (LCEL pipe syntax) |
| **`target_supabase.py`** | **Supabase** | `supabase.auth.sign_in(...)` | `supabase.auth.sign_in_with_password(...)` |

---

## ⚡ How to Run the Demos

### 1. Test All Demo Cases at Once
Run from the project root:
```bash
apipatch scan demo/
# Or via python module
python -m apipatch.cli scan demo/
```

### 2. Test an Individual Target File
```bash
apipatch scan demo/target_pydantic.py
apipatch scan demo/target_stripe.py
```

### 3. Or use the demo runner
```bash
python demo/test_demo.py target_stripe.py
```

ApiPatch will analyze the file, detect the deprecated calls, output a colorized unified diff, and generate a ready-to-merge GitHub Pull Request payload.
