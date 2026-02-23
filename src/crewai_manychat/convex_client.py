import os
import requests
from typing import List, Dict, Any, Optional


class ConvexClient:
    """Client for interacting with Convex backend."""
    
    def __init__(self, convex_url: Optional[str] = None):
        self.convex_url = (convex_url or os.getenv("CONVEX_URL") or "").rstrip("/")
        if not self.convex_url:
            raise ValueError("CONVEX_URL is required")

    def _make_request(self, endpoint: str, function_name: str, args: Dict[str, Any]) -> Any:
        url = f"{self.convex_url}/api/{endpoint}"
        response = requests.post(
            url,
            json={"path": function_name, "args": args},
            headers={
                "Content-Type": "application/json",
                "Convex-Client": "python-crewai-manychat/1.0",
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()

        if isinstance(payload, dict) and "value" in payload:
            return payload["value"]
        return payload

    def _query(self, function_name: str, args: Dict[str, Any]) -> Any:
        return self._make_request("query", function_name, args)

    def _mutation(self, function_name: str, args: Dict[str, Any]) -> Any:
        return self._make_request("mutation", function_name, args)
    
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
