import os
from typing import Optional, List, Dict, Any
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
        self.minimax_api_key = minimax_api_key or os.getenv("MINIMAX_API_KEY")
        self.minimax_api_url = minimax_api_url
        
        super().__init__(
            model=model,
            openai_api_key=self.minimax_api_key,
            openai_api_base=f"{self.minimax_api_url}/v1",
            **kwargs
        )


def get_llm(model: str = "MiniMax-M2.1") -> MiniMaxLLM:
    """Get configured MiniMax LLM instance."""
    return MiniMaxLLM(
        model=model,
        temperature=0.7,
        max_tokens=512,
    )
