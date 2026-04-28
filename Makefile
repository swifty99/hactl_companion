COMPOSE_FILE := docker-compose.integration.yaml
VENV := .venv/Scripts

.PHONY: test test-int lint fmt clean

test:
	$(VENV)/pytest tests/ --ignore=tests/integration -v --tb=short

test-int:
	docker compose -f $(COMPOSE_FILE) up -d --build
	$(VENV)/pytest tests/integration -v --tb=short -x; \
	status=$$?; \
	docker compose -f $(COMPOSE_FILE) down -v; \
	exit $$status

lint:
	$(VENV)/ruff check src/ tests/

fmt:
	$(VENV)/ruff format src/ tests/

clean:
	docker compose -f $(COMPOSE_FILE) down -v 2>nul || true
