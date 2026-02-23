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

    def update_lead_profile(
        self,
        user_id: str,
        lead_intent: Optional[str] = None,
        lead_score: Optional[int] = None,
        funnel_stage: Optional[str] = None,
        next_follow_up_at: Optional[int] = None,
        last_outcome: Optional[str] = None,
    ) -> str:
        """Update lead state fields on user profile."""
        return self._mutation("chat:updateLeadProfile", {
            "userId": user_id,
            "leadIntent": lead_intent,
            "leadScore": lead_score,
            "funnelStage": funnel_stage,
            "nextFollowUpAt": next_follow_up_at,
            "lastOutcome": last_outcome,
        })

    def log_lead_event(
        self,
        user_id: str,
        event_type: str,
        details: Optional[str] = None,
    ) -> str:
        """Log a lead event for analytics and automation."""
        return self._mutation("chat:logLeadEvent", {
            "userId": user_id,
            "eventType": event_type,
            "details": details,
        })

    def upsert_pending_follow_up(
        self,
        user_id: str,
        scheduled_for: int,
        message_draft: str,
        reason: Optional[str] = None,
    ) -> str:
        """Create or update pending follow-up task for user."""
        return self._mutation("chat:upsertPendingFollowUp", {
            "userId": user_id,
            "scheduledFor": scheduled_for,
            "messageDraft": message_draft,
            "reason": reason,
        })

    def register_incoming_message(
        self,
        message_id: str,
        contact_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Register inbound message ID for idempotency checks."""
        return self._mutation("chat:registerIncomingMessage", {
            "messageId": message_id,
            "contactId": contact_id,
        })

    def upsert_crawl_url(
        self,
        domain: str,
        url: str,
        status: str,
        page_type: Optional[str] = None,
        source: Optional[str] = None,
        lastmod: Optional[str] = None,
        content_hash: Optional[str] = None,
        title: Optional[str] = None,
        error: Optional[str] = None,
    ) -> str:
        return self._mutation("chat:upsertCrawlUrl", {
            "domain": domain,
            "url": url,
            "pageType": page_type,
            "source": source,
            "lastmod": lastmod,
            "contentHash": content_hash,
            "title": title,
            "status": status,
            "error": error,
        })

    def upsert_product(
        self,
        brand: str,
        domain: str,
        name: str,
        url: str,
        category: Optional[str] = None,
        availability: Optional[str] = None,
        price_text: Optional[str] = None,
        source: Optional[str] = None,
        content_hash: Optional[str] = None,
    ) -> str:
        return self._mutation("chat:upsertProduct", {
            "brand": brand,
            "domain": domain,
            "name": name,
            "url": url,
            "category": category,
            "availability": availability,
            "priceText": price_text,
            "source": source,
            "contentHash": content_hash,
        })

    def get_products_by_brand(self, brand: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self._query("chat:getProductsByBrand", {
            "brand": brand,
            "limit": limit,
        })

    def list_knowledge_items(self, limit: int = 1000) -> List[Dict[str, Any]]:
        return self._query("chat:listKnowledgeItems", {"limit": limit})

    def upsert_knowledge_embedding(
        self,
        knowledge_item_id: str,
        embedding: List[float],
        embedding_model: str,
    ) -> str:
        return self._mutation("chat:upsertKnowledgeEmbedding", {
            "knowledgeItemId": knowledge_item_id,
            "embedding": embedding,
            "embeddingModel": embedding_model,
        })

    def semantic_search_knowledge_base(
        self,
        query_embedding: List[float],
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        return self._query("chat:semanticSearchKnowledgeBase", {
            "queryEmbedding": query_embedding,
            "limit": limit,
        })

    def get_crawl_url_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        return self._query("chat:getCrawlUrlByUrl", {"url": url})


# Global client instance - initialized lazily
convex_client = None

def get_convex_client():
    global convex_client
    if convex_client is None:
        convex_client = ConvexClient()
    return convex_client
