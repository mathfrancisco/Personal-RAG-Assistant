.PHONY: install hello config test lint fmt ingest ask eval ollama-up ollama-pull ollama-down

install:
	uv sync --dev

# --- Ollama (LLM primário, via Docker) ---
ollama-up:
	docker compose up -d

ollama-pull:
	docker exec rag-ollama ollama pull $${OLLAMA_LLM_MODEL:-llama3.2:3b}
	docker exec rag-ollama ollama pull $${OLLAMA_EMBED_MODEL:-nomic-embed-text}

ollama-down:
	docker compose down

# --- App ---
hello:
	uv run python scripts/hello.py

config:
	uv run rag config

test:
	uv run pytest

lint:
	uv run ruff check .

fmt:
	uv run ruff format .

ingest:
	uv run rag ingest ./data/documents

ask:
	uv run rag ask "$(Q)"

eval:
	uv run rag eval
