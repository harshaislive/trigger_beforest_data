import os
import re
import requests
from html.parser import HTMLParser
from pathlib import Path
from typing import Type, ClassVar
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

    @staticmethod
    def _normalize_query(query: str) -> str:
        q = query.strip()
        if "beforest" not in q.lower():
            return f"Beforest {q}"
        return q
    
    def _run(self, query: str, count: int = 5) -> str:
        api_key = os.getenv("BRAVE_API_KEY")
        if not api_key:
            return "Error: BRAVE_API_KEY not configured"

        effective_query = self._normalize_query(query)
        
        try:
            response = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": api_key},
                params={"q": effective_query, "count": count},
                timeout=20,
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

            return (
                f"Search query used: {effective_query}\n\n"
                + "\n\n---\n\n".join(formatted)
            )
        except Exception as e:
            return f"Search error: {str(e)}"


class URLContentInput(BaseModel):
    """Input schema for URL content fetching tool."""

    url: str = Field(description="The URL to fetch and summarize from")
    max_chars: int = Field(default=4000, description="Max characters to return")


class _HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._chunks = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self._chunks.append(text)

    def text(self) -> str:
        return " ".join(self._chunks)


class URLContentTool(BaseTool):
    """Tool for fetching and extracting text from a webpage URL."""

    name: str = "fetch_url_content"
    description: str = (
        "Fetch a URL and extract readable text content. "
        "Use this after web search to verify facts before writing the final answer."
    )
    args_schema: Type[BaseModel] = URLContentInput

    def _run(self, url: str, max_chars: int = 4000) -> str:
        if not url.startswith(("http://", "https://")):
            return "Error: URL must start with http:// or https://"

        try:
            response = requests.get(
                url,
                timeout=20,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0 Safari/537.36"
                    )
                },
            )
            response.raise_for_status()

            extractor = _HTMLTextExtractor()
            extractor.feed(response.text)
            text = " ".join(extractor.text().split())

            if not text:
                return f"No readable text extracted from URL: {url}"

            clipped = text[: max(500, min(max_chars, 12000))]
            return f"URL: {url}\n\nExtracted content:\n{clipped}"
        except Exception as e:
            return f"URL fetch error: {str(e)}"


class RAGSearchInput(BaseModel):
    """Input schema for RAG Search tool."""
    query: str = Field(description="The search query")


class RAGSearchTool(BaseTool):
    """Tool for searching the knowledge base (RAG)."""
    
    name: str = "knowledge_base_search"
    description: str = "Search the knowledge base for relevant information. Use this first before web search."
    args_schema: Type[BaseModel] = RAGSearchInput

    BRAND_FILE_HINTS: ClassVar[dict[str, str]] = {
        "beforest": "beforest.co.md",
        "bewild": "bewild.life.md",
        "bewildproduce": "bewild.life.md",
        "hospitality": "hospitality.beforest.co.md",
        "experiences": "experiences.beforest.co.md",
        "10percent": "10percent.beforest.co.md",
    }

    @staticmethod
    def _search_local_beforest_data(query: str, limit: int = 5):
        base_dir = Path(__file__).resolve().parents[2] / "beforest_data"
        if not base_dir.exists():
            return []

        terms = [t for t in re.findall(r"[a-zA-Z0-9]+", query.lower()) if len(t) > 2]
        if not terms:
            return []

        query_lower = query.lower()
        preferred_files = {
            file_name
            for key, file_name in RAGSearchTool.BRAND_FILE_HINTS.items()
            if key in query_lower
        }

        scored = []
        for file_path in sorted(base_dir.glob("*.md")):
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            content_lower = content.lower()
            score = 0
            for term in terms:
                score += len(re.findall(re.escape(term), content_lower))

            if file_path.name in preferred_files:
                score += 20

            if "produce" in query_lower and file_path.name == "bewild.life.md":
                score += 30

            if score <= 0:
                continue

            first_term = next((t for t in terms if t in content_lower), None)
            if first_term:
                idx = content_lower.find(first_term)
                start = max(0, idx - 240)
                end = min(len(content), idx + 760)
                snippet = " ".join(content[start:end].split())
            else:
                snippet = " ".join(content[:700].split())

            scored.append(
                {
                    "title": file_path.stem,
                    "url": file_path.name,
                    "content": snippet,
                    "score": score,
                }
            )

        scored.sort(key=lambda item: item["score"], reverse=True)

        if not scored and preferred_files:
            for file_name in preferred_files:
                file_path = base_dir / file_name
                if not file_path.exists():
                    continue
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                snippet = " ".join(content[:900].split())
                scored.append(
                    {
                        "title": file_path.stem,
                        "url": file_path.name,
                        "content": snippet,
                        "score": 1,
                    }
                )

        return scored[:limit]
    
    def _run(self, query: str) -> str:
        from .convex_client import get_convex_client
        
        try:
            results = get_convex_client().search_knowledge_base(query, limit=5)
            if not results:
                results = self._search_local_beforest_data(query, limit=5)
                if not results:
                    return "No relevant information found in knowledge base."
            
            formatted = []
            for r in results:
                title = r.get("title", r.get("url", "Unknown"))
                content = r.get("content", "")
                formatted.append(f"[Source: {title}]\n{content}")
            
            return f"Found {len(results)} relevant results:\n\n" + "\n\n---\n\n".join(formatted)
        except Exception as e:
            fallback = self._search_local_beforest_data(query, limit=5)
            if fallback:
                formatted = []
                for r in fallback:
                    title = r.get("title", r.get("url", "Unknown"))
                    content = r.get("content", "")
                    formatted.append(f"[Source: {title}]\n{content}")
                return (
                    f"Knowledge base error: {str(e)}. "
                    f"Using local beforest_data fallback:\n\n"
                    + "\n\n---\n\n".join(formatted)
                )
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
