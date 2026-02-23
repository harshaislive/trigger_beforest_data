import os
from crewai import LLM


def get_llm(model: str = "anthropic/MiniMax-M2.1") -> LLM:
    """Return a CrewAI-compatible LLM configured for MiniMax Anthropic API."""
    api_key = os.getenv("MINIMAX_API_KEY")
    api_url = os.getenv("MINIMAX_API_URL", "https://api.minimax.io/anthropic")

    if not api_key:
        raise ValueError("MINIMAX_API_KEY is required")

    return LLM(
        model=os.getenv("MINIMAX_MODEL", model),
        api_key=api_key,
        base_url=api_url.rstrip("/"),
        temperature=0.7,
        max_tokens=512,
    )
