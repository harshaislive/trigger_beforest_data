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

CANONICAL_BRANDS = [
    "beforest.co",
    "bewild.life",
    "hospitality.beforest.co",
    "experiences.beforest.co",
    "10percent.beforest.co",
]

BRAND_RESPONSE_OVERRIDES = {
    "bewild": {
        "products": (
            "On bewild.life, core categories include forest-friendly produce, single origin coffee,"
            " herbal infusions, rice varieties, pulses, and spices. "
            "Examples visible from current listings include veggie bags, Canephora coffee,"
            " Rosella infusion, Mysore Mallige rice, and Mappillai Samba red rice."
        )
    }
}

DOMAIN_ALIASES = {
    "beforest.in": "beforest.co",
    "www.beforest.in": "beforest.co",
    "www.beforest.co": "beforest.co",
    "www.bewild.life": "bewild.life",
}


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


def enforce_canonical_brand_domains(text: str) -> str:
    normalized = text
    for wrong, correct in DOMAIN_ALIASES.items():
        normalized = re.sub(rf"\b{re.escape(wrong)}\b", correct, normalized, flags=re.IGNORECASE)

    def replace_beforest_domain(match: re.Match[str]) -> str:
        domain = match.group(0).lower()
        if domain in CANONICAL_BRANDS:
            return domain
        if domain.startswith("beforest."):
            return "beforest.co"
        return domain

    normalized = re.sub(r"\bbeforest\.[a-z]{2,}\b", replace_beforest_domain, normalized, flags=re.IGNORECASE)
    return normalized


def apply_brand_no_info_override(user_message: str, answer: str) -> str:
    lower_q = user_message.lower()
    lower_a = answer.lower()

    no_info_signals = (
        "don't have",
        "do not have",
        "no specific",
        "not sure",
        "no info",
        "no information",
    )

    asks_products = any(k in lower_q for k in ("product", "produce", "available", "catalog"))
    says_no_info = any(s in lower_a for s in no_info_signals)

    if "bewild" in lower_q and asks_products and says_no_info:
        return BRAND_RESPONSE_OVERRIDES["bewild"]["products"]

    return answer


def humanize_manager_voice(answer: str) -> str:
    replacements = {
        "based on my research": "",
        "from my research": "",
        "according to my research": "",
        "from my context": "",
        "in my context": "",
        "according to my memory": "",
        "from conversation memory": "",
        "knowledge base": "current details",
        "i do not have this in my context": "I do not have that detail yet",
    }

    out = answer
    for src, dst in replacements.items():
        out = re.sub(rf"\b{re.escape(src)}\b", dst, out, flags=re.IGNORECASE)

    out = re.sub(r"\s{2,}", " ", out).strip()
    out = out.replace(" .", ".").replace(" ,", ",")
    return out


def should_use_structured_bewild_lookup(message: str) -> bool:
    lower = message.lower()
    asks_products = any(k in lower for k in ("product", "produce", "available", "catalog", "shop"))
    return "bewild" in lower and asks_products


def build_bewild_products_response(products: list[dict]) -> Optional[str]:
    if not products:
        return None

    names = []
    categories = []
    seen_names = set()
    seen_categories = set()

    for item in products:
        name = (item.get("name") or "").strip()
        category = (item.get("category") or "").strip()

        if name and name.lower() not in seen_names and len(names) < 8:
            names.append(name)
            seen_names.add(name.lower())

        if category and category.lower() not in seen_categories and len(categories) < 5:
            categories.append(category)
            seen_categories.add(category.lower())

    if not names:
        return None

    category_text = ", ".join(categories) if categories else "multiple produce and pantry categories"
    name_text = ", ".join(names[:6])
    return (
        f"On bewild.life, we currently list products across {category_text}. "
        f"Some available items include {name_text}. "
        "If you want, I can narrow this to coffee, grains, spices, or weekly produce picks."
    )


def should_use_fast_kb_path(message: str) -> bool:
    lower = message.lower()
    brand_terms = ("beforest", "bewild", "hospitality", "experiences", "10percent")
    info_terms = ("what", "about", "products", "produce", "available", "where", "which", "tell me")
    return any(b in lower for b in brand_terms) and any(t in lower for t in info_terms)


def build_fast_kb_response(query: str, kb_rows: list[dict]) -> Optional[str]:
    if not kb_rows:
        return None

    titles = []
    points = []
    seen_titles = set()

    for row in kb_rows[:3]:
        title = (row.get("title") or row.get("url") or "").strip()
        content = " ".join((row.get("content") or "").split())
        if title and title.lower() not in seen_titles:
            titles.append(title)
            seen_titles.add(title.lower())
        if content:
            snippet = content[:220].rstrip()
            points.append(snippet)

    if not points:
        return None

    source_text = ", ".join(titles[:3]) if titles else "our current knowledge base"
    summary = points[0]
    return (
        f"Here is what we currently have from {source_text}. "
        f"{summary} "
        "If you want, I can break this down into exact options and next step for you."
    )


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
            client = get_convex_client()
            if should_use_structured_bewild_lookup(request.message):
                products = client.get_products_by_brand("bewild", limit=40)
                override = build_bewild_products_response(products)
                if override:
                    answer = override
                else:
                    answer = run_crew(
                        message=request.message,
                        contact_id=request.contact_id,
                        name=request.name or "User",
                    )
            elif should_use_fast_kb_path(request.message):
                kb_rows = client.search_knowledge_base(request.message, limit=3)
                quick = build_fast_kb_response(request.message, kb_rows)
                if quick:
                    answer = quick
                else:
                    answer = run_crew(
                        message=request.message,
                        contact_id=request.contact_id,
                        name=request.name or "User",
                    )
            else:
                answer = run_crew(
                    message=request.message,
                    contact_id=request.contact_id,
                    name=request.name or "User",
                )
        except Exception as e:
            print(f"Crew error: {e}")
            answer = "I'm thinking... give me a moment."

    answer = answer.replace("\u2014", "-").replace("\u2013", "-")
    answer = humanize_manager_voice(answer)
    answer = enforce_canonical_brand_domains(answer)
    answer = apply_brand_no_info_override(request.message, answer)

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
