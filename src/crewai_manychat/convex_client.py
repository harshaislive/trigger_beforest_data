import os
from typing import List, Dict, Any, Optional
import requests


class ConvexClient:
    """Client for interacting with Convex backend."""
    
    def __init__(self, convex_url: Optional[str] = None):
        self.convex_url = (convex_url or os.getenv("CONVEX_URL") or "").rstrip("/")
        if not self.convex_url:
            raise ValueError("CONVEX_URL is required")

    @staticmethod
    def _clean_args(args: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in args.items() if v is not None}

    def _query(self, function_name: str, args: Dict[str, Any]) -> Any:
        return self._request("query", function_name, args)

    def _mutation(self, function_name: str, args: Dict[str, Any]) -> Any:
        return self._request("mutation", function_name, args)

    def _request(self, endpoint: str, function_name: str, args: Dict[str, Any]) -> Any:
        response = requests.post(
            f"{self.convex_url}/api/{endpoint}",
            json={
                "path": function_name,
                "args": self._clean_args(args),
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()

        if isinstance(payload, dict) and payload.get("status") == "error":
            message = payload.get("errorMessage", "Unknown Convex error")
            raise RuntimeError(f"Convex {endpoint} {function_name} failed: {message}")

        if isinstance(payload, dict) and "value" in payload:
            return payload["value"]
        return payload
    
    def get_or_create_user(
        self,
        instagram_user_id: Optional[str] = None,
        contact_id: Optional[str] = None,
        name: Optional[str] = None
    ) -> str:
        """Get or create a user in Convex."""
        result = self._mutation("chat:getOrCreateUser", {
            "instagramUserId": instagram_user_id,
            "contactId": contact_id,
            "name": name,
        })
        return result
    
    def get_chat_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get chat history for a user."""
        result = self._query("chat:getChatHistory", {
            "userId": user_id,
            "limit": limit,
        })
        return result
    
    def store_chat_message(
        self,
        user_id: str,
        message: str,
        response: str,
        sources: Optional[List[str]] = None
    ) -> str:
        """Store a chat message in Convex."""
        result = self._mutation("chat:storeChatMessage", {
            "userId": user_id,
            "message": message,
            "response": response,
            "sources": sources or [],
        })
        return result
    
    def search_knowledge_base(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search the knowledge base in Convex."""
        result = self._query("chat:searchKnowledgeBase", {
            "query": query,
            "limit": limit,
        })
        return result

    def upsert_knowledge_item(
        self,
        url: str,
        content: str,
        title: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> str:
        """Insert or update a knowledge item by URL."""
        result = self._mutation("chat:upsertKnowledgeItem", {
            "url": url,
            "title": title,
            "content": content,
            "summary": summary,
        })
        return result

    def add_knowledge_item(
        self,
        url: str,
        content: str,
        title: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> str:
        """Insert a knowledge item."""
        result = self._mutation("chat:addKnowledgeItem", {
            "url": url,
            "title": title,
            "content": content,
            "summary": summary,
        })
        return result
    
    def get_user_by_contact_id(self, contact_id: str) -> Optional[Dict[str, Any]]:
        """Get user by contact ID."""
        result = self._query("chat:getUserByContactId", {
            "contactId": contact_id,
        })
        return result


# Global client instance - initialized lazily
convex_client = None

def get_convex_client():
    global convex_client
    if convex_client is None:
        convex_client = ConvexClient()
    return convex_client
