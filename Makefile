COMPOSE_FILE := docker-compose.integration.yaml

.PHONY: test test-int lint fmt clean spec

test:
	uv run pytest tests/ --ignore=tests/integration -v --tb=short

test-int:
	docker compose -f $(COMPOSE_FILE) up -d --build
	uv run pytest tests/integration -v --tb=short -x; \
	status=$$?; \
	docker compose -f $(COMPOSE_FILE) down -v; \
	exit $$status

lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/
	uv run mypy

fmt:
	uv run ruff format src/ tests/

spec:
	uv run python -c "from companion.openapi import write_spec; write_spec()"

clean:
	docker compose -f $(COMPOSE_FILE) down -v 2>nul || true
