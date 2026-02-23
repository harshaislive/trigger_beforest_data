import os
import requests
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class BraveSearchInput(BaseModel):
    """Input schema for Brave Search tool."""
    query: str = Field(description="The search query")
    count: int = Field(default=5, description="Number of results to return")


class BraveSearchTool(BaseTool):
    """Tool for searching the web using Brave Search API."""
    
    name: str = "brave_search"
    description: str = "Search the web using Brave Search. Use this to find current information, news, or any content not in your knowledge base."
    args_schema: Type[BaseModel] = BraveSearchInput
    
    def _run(self, query: str, count: int = 5) -> str:
        api_key = os.getenv("BRAVE_API_KEY")
        if not api_key:
            return "Error: BRAVE_API_KEY not configured"
        
        try:
            response = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": api_key},
                params={"q": query, "count": count}
            )
            response.raise_for_status()
            data = response.json()
            
            results = data.get("web", {}).get("results", [])
            if not results:
                return "No results found"
            
            formatted = []
            for r in results:
                formatted.append(
                    f"Title: {r.get('title', '')}\n"
                    f"Description: {r.get('description', '')}\n"
                    f"URL: {r.get('url', '')}"
                )
            
            return "\n\n---\n\n".join(formatted)
        except Exception as e:
            return f"Search error: {str(e)}"


class RAGSearchInput(BaseModel):
    """Input schema for RAG Search tool."""
    query: str = Field(description="The search query")


class RAGSearchTool(BaseTool):
    """Tool for searching the knowledge base (RAG)."""
    
    name: str = "knowledge_base_search"
    description: str = "Search the knowledge base for relevant information. Use this first before web search."
    args_schema: Type[BaseModel] = RAGSearchInput
    
    def _run(self, query: str) -> str:
        from .convex_client import get_convex_client
        
        try:
            results = get_convex_client().search_knowledge_base(query, limit=5)
            if not results:
                return "No relevant information found in knowledge base."
            
            formatted = []
            for r in results:
                title = r.get("title", r.get("url", "Unknown"))
                content = r.get("content", "")
                formatted.append(f"[Source: {title}]\n{content}")
            
            return f"Found {len(results)} relevant results:\n\n" + "\n\n---\n\n".join(formatted)
        except Exception as e:
            return f"Knowledge base error: {str(e)}"


class MemorySearchInput(BaseModel):
    """Input schema for Memory Search tool."""
    contact_id: str = Field(description="The user's contact ID")


class MemorySearchTool(BaseTool):
    """Tool for retrieving conversation history (memory)."""
    
    name: str = "conversation_memory"
    description: str = "Get the conversation history with this user to maintain context."
    args_schema: Type[BaseModel] = MemorySearchInput
    
    def _run(self, contact_id: str) -> str:
        from .convex_client import get_convex_client
        
        try:
            client = get_convex_client()
            user = client.get_user_by_contact_id(contact_id)
            if not user:
                return "No user found."
            
            messages = client.get_chat_history(user["_id"], limit=10)
            if not messages:
                return "No previous conversation history found."
            
            formatted = []
            for m in messages[-5:]:
                formatted.append(f"User: {m.get('message', '')}\nAssistant: {m.get('response', '')}")
            
            return "Recent conversation:\n\n" + "\n\n".join(formatted)
        except Exception as e:
            return f"Memory error: {str(e)}"
