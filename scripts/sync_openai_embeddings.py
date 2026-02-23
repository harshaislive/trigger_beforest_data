from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env_file(ROOT_DIR / ".env.local")
load_env_file(ROOT_DIR / ".env")

from src.crewai_manychat.convex_client import get_convex_client


def embed_text(api_key: str, model: str, text: str) -> list[float] | None:
    try:
        response = requests.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"model": model, "input": text},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json().get("data", [])
        if not data:
            return None
        emb = data[0].get("embedding")
        if not isinstance(emb, list) or not emb:
            return None
        return [float(x) for x in emb]
    except Exception:
        return None


def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required")

    model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    client = get_convex_client()
    items = client.list_knowledge_items(limit=1000)

    ok = 0
    skipped = 0
    failed = 0

    for item in items:
        existing = item.get("embedding")
        if existing and len(existing) > 0 and item.get("embeddingModel") == model:
            skipped += 1
            continue

        text = " ".join(
            [
                str(item.get("title") or ""),
                str(item.get("summary") or ""),
                str(item.get("content") or "")[:4000],
            ]
        ).strip()

        if not text:
            failed += 1
            continue

        vector = embed_text(api_key, model, text)
        if not vector:
            failed += 1
            continue

        client.upsert_knowledge_embedding(
            knowledge_item_id=item["_id"],
            embedding=vector,
            embedding_model=model,
        )
        ok += 1

    print(f"Embedding sync complete. Updated: {ok}, Skipped: {skipped}, Failed: {failed}")


if __name__ == "__main__":
    main()
