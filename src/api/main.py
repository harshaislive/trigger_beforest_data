import os
import time
import re
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


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
    message: str
    instagramUserId: Optional[str] = None
    name: Optional[str] = None
    contact_id: Optional[str] = None


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


@app.post("/api/chat", response_model=ManyChatResponse)
async def chat(request: ManyChatRequest):
    from src.crewai_manychat.convex_client import get_convex_client
    from src.crewai_manychat.crew import run_crew

    user_id = None

    if not request.contact_id:
        raise HTTPException(status_code=400, detail="contact_id is required")

    if not request.message:
        raise HTTPException(status_code=400, detail="message is required")

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
            get_convex_client().store_chat_message(
                user_id=user_id,
                message=request.message,
                response=answer,
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
