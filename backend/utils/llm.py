"""
LLM loader — Ollama first, Claude API fallback.
Supports json_mode for structured outputs, prose mode for reports.
"""

import os
import logging
import httpx
from functools import lru_cache

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")


@lru_cache(maxsize=2)
def get_llm(json_mode: bool = False):
    """
    Return LLM instance.
    json_mode=True  → forces valid JSON output (for Orchestrator, Synthesis, Risk)
    json_mode=False → free-form prose (for Writer, Earnings analysis, Filings summary)
    """
    if _ollama_running():
        from langchain_ollama import ChatOllama
        kwargs = {
            "base_url": OLLAMA_BASE_URL,
            "model": OLLAMA_MODEL,
            "temperature": 0.1,
        }
        if json_mode:
            kwargs["format"] = "json"
        logger.info(f"[LLM] Using Ollama: {OLLAMA_MODEL} (json_mode={json_mode})")
        return ChatOllama(**kwargs)

    if ANTHROPIC_KEY:
        from langchain_anthropic import ChatAnthropic
        logger.info("[LLM] Using Claude API")
        return ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=ANTHROPIC_KEY,
            max_tokens=2048,
        )

    raise RuntimeError(
        "No LLM available. Start Ollama (`ollama serve`) or set ANTHROPIC_API_KEY."
    )


def _ollama_running() -> bool:
    try:
        r = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            return any(m.startswith(OLLAMA_MODEL) for m in models)
    except Exception:
        pass
    return False