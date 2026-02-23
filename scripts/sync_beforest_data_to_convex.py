from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.crewai_manychat.convex_client import get_convex_client


def md_name_to_url(name: str) -> str:
    if name.endswith('.md'):
        name = name[:-3]
    return f"https://{name}"


def extract_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        line = line.strip()
        if line.startswith('#'):
            return line.lstrip('#').strip() or fallback
    return fallback


def summarize(content: str, max_len: int = 300) -> str:
    text = " ".join(content.split())
    return text[:max_len]


def main() -> None:
    base_dir = Path(__file__).resolve().parents[1] / "beforest_data"
    if not base_dir.exists():
        raise RuntimeError(f"beforest_data directory not found: {base_dir}")

    client = get_convex_client()
    files = sorted(base_dir.glob("*.md"))
    if not files:
        raise RuntimeError("No markdown files found in beforest_data")

    print(f"Syncing {len(files)} markdown files to Convex...")
    success_count = 0
    fail_count = 0

    for file_path in files:
        content = file_path.read_text(encoding="utf-8", errors="ignore").strip()
        if not content:
            print(f"Skipping empty file: {file_path.name}")
            continue

        url = md_name_to_url(file_path.name)
        fallback_title = file_path.stem
        title = extract_title(content, fallback_title)
        summary = summarize(content)

        try:
            try:
                doc_id = client.upsert_knowledge_item(
                    url=url,
                    title=title,
                    content=content,
                    summary=summary,
                )
                print(f"Upserted {file_path.name} -> {doc_id}")
            except Exception as upsert_error:
                msg = str(upsert_error)
                if "chat:upsertKnowledgeItem" in msg:
                    doc_id = client.add_knowledge_item(
                        url=url,
                        title=title,
                        content=content,
                        summary=summary,
                    )
                    print(f"Inserted {file_path.name} via addKnowledgeItem -> {doc_id}")
                else:
                    raise
            success_count += 1
        except Exception as exc:
            print(f"Failed {file_path.name}: {exc}")
            fail_count += 1

    print(f"Done. Success: {success_count}, Failed: {fail_count}")


if __name__ == "__main__":
    main()
