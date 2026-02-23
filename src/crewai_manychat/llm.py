import os
from typing import Optional
from langchain_openai import ChatOpenAI


class MiniMaxLLM(ChatOpenAI):
    """MiniMax LLM wrapper compatible with ChatOpenAI interface."""
    
    def __init__(
        self,
        model: str = "MiniMax-M2.5",
        minimax_api_key: Optional[str] = None,
        minimax_api_url: str = "https://api.minimax.io/anthropic",
        **kwargs
    ):
        api_key = minimax_api_key or os.getenv("MINIMAX_API_KEY")
        api_url = os.getenv("MINIMAX_API_URL", minimax_api_url)

        if not api_key:
            raise ValueError("MINIMAX_API_KEY is required")

        super().__init__(
            model=model,
            openai_api_key=api_key,
            openai_api_base=f"{api_url.rstrip('/')}/v1",
            **kwargs
        )


def get_llm(model: str = "MiniMax-M2.1") -> MiniMaxLLM:
    """Get configured MiniMax LLM instance."""
    return MiniMaxLLM(
        model=model,
        temperature=0.7,
        max_tokens=512,
    )
