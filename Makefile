.PHONY: test lint typecheck deadcode quality ci install

install:
	uv venv
	uv pip install -e ".[dev]"
	uv pip install sentence-transformers tiktoken prompt_toolkit

test:
	uv run pytest --cov=src/nanoagent/ --cov-report=term tests/

lint:
	uv run ruff check src/ tests/

typecheck:
	uv run pyright src/

deadcode:
	uv run vulture src/nanoagent/ --min-confidence 60

quality: lint typecheck deadcode test

ci: quality
