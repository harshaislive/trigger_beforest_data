import os
import time
import re
import json
from typing import Optional, Any

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict


app = FastAPI(title="CrewAI ManyChat")


MANYCHAT_API_KEY = os.getenv("MANYCHAT_API_KEY")
MANYCHAT_API_URL = "https://api.manychat.com/fb/sending/sendContent"

GREETINGS = [
    "hi",
    "hello",
    "hey",
    "hiya",
    "good morning",
    "good evening",
    "good afternoon",
    "what's up",
    "wassup",
    "yo",
]


class ManyChatRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    message: str
    instagramUserId: Optional[str] = None
    name: Optional[str] = None
    contact_id: Optional[str] = None
    flow_id: Optional[str] = None
    campaign_id: Optional[str] = None
    message_id: Optional[str] = None


class ManyChatResponse(BaseModel):
    version: str = "v2"
    messages: list
    _timestamp: Optional[int] = None


def is_greeting(message: str) -> bool:
    lower = message.lower().strip()
    return any(
        g == lower or lower.startswith(g + " ") or lower.endswith(" " + g)
        for g in GREETINGS
    )


def send_manychat_message(subscriber_id: str, message: str) -> dict:
    if not MANYCHAT_API_KEY:
        raise HTTPException(status_code=500, detail="MANYCHAT_API_KEY not configured")

    response = requests.post(
        MANYCHAT_API_URL,
        headers={
            "Authorization": f"Bearer {MANYCHAT_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "subscriber_id": int(subscriber_id),
            "data": {
                "version": "v2",
                "content": {
                    "type": "instagram",
                    "messages": [
                        {"type": "text", "text": chunk}
                        for chunk in split_message_chunks(message)
                    ],
                },
            },
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def split_message_chunks(text: str, max_chars: int = 240) -> list[str]:
    cleaned = text.replace("\u2014", "-").replace("\u2013", "-").strip()
    if not cleaned:
        return [""]

    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", cleaned) if p.strip()]
    chunks: list[str] = []
    current = ""

    for part in parts:
        candidate = part if not current else f"{current} {part}"
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""

        if len(part) <= max_chars:
            current = part
            continue

        words = part.split()
        segment = ""
        for word in words:
            candidate_word = word if not segment else f"{segment} {word}"
            if len(candidate_word) <= max_chars:
                segment = candidate_word
            else:
                chunks.append(segment)
                segment = word
        if segment:
            current = segment

    if current:
        chunks.append(current)

    return chunks or [cleaned]


def infer_lead_signals(message: str) -> dict:
    lower = message.lower()

    intent_rules = [
        ("investment", ["invest", "investment", "returns", "roi"]),
        ("stay", ["stay", "book", "booking", "room", "night", "hospitality"]),
        ("experience", ["experience", "retreat", "workshop", "event", "visit"]),
        ("partnership", ["partner", "collab", "collaborate", "media", "press"]),
        ("community", ["collective", "community", "membership", "join"]),
    ]

    intent = "general"
    for key, terms in intent_rules:
        if any(t in lower for t in terms):
            intent = key
            break

    score = 25
    if "?" in lower:
        score += 10
    if any(t in lower for t in ["price", "cost", "book", "visit", "join", "interested"]):
        score += 25
    if any(t in lower for t in ["today", "now", "asap", "this week"]):
        score += 15
    if any(t in lower for t in ["just browsing", "curious", "maybe"]):
        score -= 10
    score = max(0, min(100, score))

    stage = "awareness"
    if any(t in lower for t in ["details", "how", "what", "where", "which", "price", "cost"]):
        stage = "consideration"
    if any(t in lower for t in ["book", "visit", "schedule", "call", "when can i"]):
        stage = "intent"
    if any(t in lower for t in ["paid", "confirmed", "done booking"]):
        stage = "conversion"

    follow_up_hours = 24
    if score >= 70 or stage == "intent":
        follow_up_hours = 4
    elif score >= 50:
        follow_up_hours = 12

    follow_up_ms = int(time.time() * 1000) + follow_up_hours * 60 * 60 * 1000

    return {
        "intent": intent,
        "score": score,
        "stage": stage,
        "follow_up_ms": follow_up_ms,
        "follow_up_hours": follow_up_hours,
    }


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return False


def parse_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if cleaned.isdigit():
            return int(cleaned)
    return 0


def build_follow_up_message(name: str, intent: str) -> str:
    first_name = (name or "there").split()[0]
    if intent == "stay":
        return f"Hey {first_name}, want me to share stay options and best dates to visit?"
    if intent == "investment":
        return f"Hey {first_name}, I can share the next step to evaluate Beforest investment fit."
    if intent == "experience":
        return f"Hey {first_name}, I can help you pick an experience that matches your pace."
    if intent == "community":
        return f"Hey {first_name}, want a quick breakdown of collectives and who each one is for?"
    return f"Hey {first_name}, happy to help with the next step when you are ready."


@app.post("/api/chat", response_model=ManyChatResponse)
async def chat(request: ManyChatRequest):
    from src.crewai_manychat.convex_client import get_convex_client
    from src.crewai_manychat.crew import run_crew

    user_id = None
    payload = request.model_dump(exclude_none=True)
    core_fields = {
        "message",
        "instagramUserId",
        "name",
        "contact_id",
        "flow_id",
        "campaign_id",
        "message_id",
    }
    metadata = {k: v for k, v in payload.items() if k not in core_fields}

    if not request.contact_id:
        raise HTTPException(status_code=400, detail="contact_id is required")

    if not request.message:
        raise HTTPException(status_code=400, detail="message is required")

    if request.message_id:
        try:
            incoming = get_convex_client().register_incoming_message(
                message_id=request.message_id,
                contact_id=request.contact_id,
            )
            if incoming.get("isDuplicate"):
                return ManyChatResponse(
                    messages=[],
                    _timestamp=int(time.time() * 1000),
                )
        except Exception as e:
            print(f"Idempotency check error: {e}")

    try:
        user_id = get_convex_client().get_or_create_user(
            instagram_user_id=request.instagramUserId,
            contact_id=request.contact_id,
            name=request.name,
        )
    except Exception as e:
        print(f"Convex user error: {e}")

    if is_greeting(request.message):
        answer = "Hey. I'm Forest Guide at Beforest. What would you like to know?"
    else:
        try:
            answer = run_crew(
                message=request.message,
                contact_id=request.contact_id,
                name=request.name or "User",
            )
        except Exception as e:
            print(f"Crew error: {e}")
            answer = "I'm thinking... give me a moment."

    answer = answer.replace("\u2014", "-").replace("\u2013", "-")

    try:
        if user_id:
            client = get_convex_client()
            client.store_chat_message(
                user_id=user_id,
                message=request.message,
                response=answer,
            )

            lead = infer_lead_signals(request.message)

            if parse_bool(metadata.get("is_ig_verified_user")):
                lead["score"] = min(100, lead["score"] + 10)

            followers = parse_int(metadata.get("ig_followers_count"))
            if followers >= 10000:
                lead["score"] = min(100, lead["score"] + 15)
            elif followers >= 3000:
                lead["score"] = min(100, lead["score"] + 8)

            client.update_lead_profile(
                user_id=user_id,
                lead_intent=lead["intent"],
                lead_score=lead["score"],
                funnel_stage=lead["stage"],
                next_follow_up_at=lead["follow_up_ms"],
                last_outcome="replied",
            )

            client.upsert_pending_follow_up(
                user_id=user_id,
                scheduled_for=lead["follow_up_ms"],
                message_draft=build_follow_up_message(request.name or "there", lead["intent"]),
                reason=f"auto_follow_up_{lead['stage']}",
            )

            details = {
                "intent": lead["intent"],
                "score": lead["score"],
                "stage": lead["stage"],
                "contact_id": request.contact_id,
                "flow_id": request.flow_id,
                "campaign_id": request.campaign_id,
                "message_id": request.message_id,
                "metadata": metadata,
            }
            client.log_lead_event(
                user_id=user_id,
                event_type="incoming_message",
                details=json.dumps({k: v for k, v in details.items() if v is not None}),
            )
    except Exception as e:
        print(f"Convex store error: {e}")

    try:
        send_manychat_message(request.contact_id, answer)
    except Exception as e:
        print(f"ManyChat send error: {e}")

    return ManyChatResponse(
        messages=[{"text": chunk} for chunk in split_message_chunks(answer)],
        _timestamp=int(time.time() * 1000),
    )


@app.get("/health")
async def health():
    return {"status": "ok", "app": "crewai-manychat"}


@app.get("/")
async def root():
    return {"message": "Hello World"}
