.PHONY: install dev run convex

install:
	uv sync

dev:
	uv run uvicorn src.api.main:app --reload --port 3000

run:
	uv run uvicorn src.api.main:app --host 0.0.0.0 --port 3000

convex:
	npx convex dev
