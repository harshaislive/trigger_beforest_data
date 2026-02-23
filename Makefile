.PHONY: install dev run convex sync-kb crawl-sites sync-embeddings

install:
	uv sync

dev:
	uv run uvicorn src.api.main:app --reload --port 3000

run:
	uv run uvicorn src.api.main:app --host 0.0.0.0 --port 3000

convex:
	npx convex dev

sync-kb:
	uv run python scripts/sync_beforest_data_to_convex.py

crawl-sites:
	python3 scripts/crawl_sitemaps_to_convex.py

sync-embeddings:
	python3 scripts/sync_openai_embeddings.py
