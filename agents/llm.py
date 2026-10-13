"""One function that talks to the LLM. Everything else in the graph is plain code.

Settings come from .env (never commit it):
    LLM_PROVIDER=openai | anthropic | gemini
    LLM_MODEL=<exact model id from your provider's console>
    LLM_TEMPERATURE=0          # set to "none" if your model rejects a temperature
    OPENAI_API_KEY=... / ANTHROPIC_API_KEY=... / GEMINI_API_KEY=...

call_llm returns the text plus what it cost, so every call can be counted:
    {"text", "input_tokens", "output_tokens", "ms", "model"}
"""
import os
import time

try:                                   # optional: load .env if python-dotenv is installed
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _settings():
    provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
    model = os.environ.get("LLM_MODEL", "").strip()
    if not provider or not model:
        raise RuntimeError("Set LLM_PROVIDER and LLM_MODEL in .env")
    temp = os.environ.get("LLM_TEMPERATURE", "0").strip().lower()
    temperature = None if temp in ("", "none") else float(temp)
    return provider, model, temperature


def call_llm(system: str, user: str) -> dict:
    provider, model, temperature = _settings()
    extra = {} if temperature is None else {"temperature": temperature}
    t0 = time.perf_counter()

    if provider == "openai":
        from openai import OpenAI
        r = OpenAI().chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            **extra)
        text = r.choices[0].message.content or ""
        tin, tout = r.usage.prompt_tokens, r.usage.completion_tokens

    elif provider == "anthropic":
        from anthropic import Anthropic
        r = Anthropic().messages.create(
            model=model, max_tokens=300, system=system,
            messages=[{"role": "user", "content": user}], **extra)
        text = "".join(b.text for b in r.content if b.type == "text")
        tin, tout = r.usage.input_tokens, r.usage.output_tokens

    elif provider == "gemini":
        from google import genai
        cfg = {"system_instruction": system, "response_mime_type": "application/json", **extra}
        r = genai.Client().models.generate_content(model=model, contents=user, config=cfg)
        text = r.text or ""
        tin = r.usage_metadata.prompt_token_count
        tout = r.usage_metadata.candidates_token_count

    else:
        raise RuntimeError(f"Unknown LLM_PROVIDER: {provider!r}")

    return {"text": text, "input_tokens": tin, "output_tokens": tout,
            "ms": round((time.perf_counter() - t0) * 1000), "model": model}
