# Implementation Progress

Tracking file for hactl-companion implementation phases.

## Phase 0: Skeleton & CI ✅

- [x] pyproject.toml (deps, ruff, mypy, pytest config)
- [x] `src/companion/` package structure
- [x] `__main__.py` entrypoint
- [x] `server.py` — app factory with middleware
- [x] `routes/health.py` — GET /v1/health
- [x] Dockerfile
- [x] config.yaml (Add-on manifest)
- [x] run.sh
- [x] CI workflow (.github/workflows/ci.yml)
- [x] dependabot.yml
- [x] translations/en.yaml
- [x] Test fixtures (configuration.yaml, automations.yaml, scripts.yaml)
- [x] test_health.py — 3 tests

## Phase 1: Plugin Architecture & Auth ✅

- [x] Plugin registry (`register_routes` + RouteDef pattern)
- [x] Auth middleware (Bearer token validation)
- [x] Ingress header bypass (X-Ingress-Path)
- [x] /v1/health exempted from auth
- [x] test_auth.py — 5 tests

## Phase 2: YAML Config Read ✅

- [x] GET /v1/config/files — list YAML files, excludes secrets.yaml
- [x] GET /v1/config/file?path=... — read whole file
- [x] GET /v1/config/block?path=...&id=... — extract block by id/alias (list + dict)
- [x] Path traversal prevention
- [x] secrets.yaml deny-list
- [x] test_config.py — 9 tests

## Phase 3: YAML Config Write ✅

- [x] PUT /v1/config/file — dry_run=true returns unified diff
- [x] PUT /v1/config/file — dry_run=false writes + creates timestamped backup
- [x] Config validation via ha core check-config (with graceful fallback)
- [x] Automatic rollback on validation failure
- [x] YAML parse validation on input
- [x] Empty body rejection
- [x] Path traversal + secrets.yaml protection on write
- [x] test_config_write.py — 8 tests

## Phase 4: Supervisor API Proxy ✅

- [x] GET /v1/supervisor/info — shaped response (hostname, arch, HA version, disk, memory)
- [x] GET /v1/supervisor/addons — installed add-ons + status
- [x] GET /v1/supervisor/backups — backup list
- [x] POST /v1/supervisor/backups/new — trigger new backup (120s timeout)
- [x] GET /v1/supervisor/addon/{slug}/logs — add-on logs (plain text)
- [x] Slug validation, 502 on Supervisor unreachable
- [x] test_supervisor.py — 6 tests

## Phase 5: Direct Logs ✅

- [x] GET /v1/logs/core — read from /config/home-assistant.log
- [x] GET /v1/logs/supervisor — via Supervisor API
- [x] GET /v1/logs/addon/{slug} — via Supervisor API
- [x] `lines` param (tail), `level` filter (error/warning/info/debug/critical)
- [x] Traceback continuation lines included with parent log entry
- [x] test_logs.py — 7 tests

## Phase 6: HA CLI Bridge ✅

- [x] POST /v1/ha/reload/{domain} — whitelisted domains only
- [x] POST /v1/ha/restart — ha core restart
- [x] GET /v1/ha/resolution — ha resolution info
- [x] POST /v1/ha/check-config — ha core check-config
- [x] Command whitelist (no arbitrary execution)
- [x] Domain validation, timeout handling (504), CLI-not-found handling (502)
- [x] test_ha_cli.py — 7 tests

## Phase 7: OpenAPI Export ✅

- [x] `src/companion/openapi.py` — spec generation from ENDPOINT_META
- [x] `openapi/companion-v1.yaml` — committed spec file
- [x] `write_spec()` CLI for regeneration
- [x] OpenAPI 3.0.3 validation via openapi-spec-validator
- [x] Conformance: all routes ↔ spec bidirectional check
- [x] test_openapi.py — 6 tests

## Integration Testing ✅

Live Docker-based integration tests against real HA Core + companion containers.

- [x] `docker-compose.integration.yaml` — HA Core + companion on shared bridge network, named volume
- [x] `tests/integration/conftest.py` — session-scoped compose lifecycle, HA readiness polling, headless 5-step onboarding (create user → auth code → core config → analytics → long-lived WS token)
- [x] `tests/integration/test_auth.py` — 5 tests: token enforcement, ingress bypass, health exemption
- [x] `tests/integration/test_live.py` — 15 tests: health, config read (list, read, traversal, secrets deny), config write (dry-run, apply, traversal, invalid YAML), core logs (read, filter)
- [x] `tests/integration/test_no_supervisor.py` — 10 tests: supervisor proxy 502, log proxy 502, CLI bridge 502 (no Supervisor available in standalone HA Core)
- [x] `Makefile` targets: `make test` (unit), `make test-int` (integration), `make lint`, `make fmt`, `make clean`

## Phase 8: hactl Integration ☐

See [HACTL_INTEGRATION.md](HACTL_INTEGRATION.md) for full implementation & test instructions.

- [ ] Go companion client (`internal/companion/client.go` + `types.go`)
- [ ] Vendor OpenAPI spec (`testdata/companion-v1.yaml`)
- [ ] Docker Compose for hactl integration (`docker-compose.companion.yaml`)
- [ ] Go test helpers: compose lifecycle, headless onboarding, wait utils
- [ ] Integration tests: health, config CRUD, logs, supervisor 502, CLI 502
- [ ] OpenAPI contract tests (kin-openapi spec validation)
- [ ] `make test-companion` Makefile target
- [ ] CI job: `companion-integration` in GitHub Actions

## Phase 9: Packaging & HACS ☐

---

## Test Summary

### Unit Tests

| Phase | Tests | Status |
|-------|-------|--------|
| 0 | 3 | ✅ |
| 1 | 5 | ✅ |
| 2 | 9 | ✅ |
| 3 | 8 | ✅ |
| 4 | 6 | ✅ |
| 5 | 7 | ✅ |
| 6 | 7 | ✅ |
| 7 | 6 | ✅ |
| **Total** | **51** | **All passing** |

### Integration Tests

| Suite | Tests | Status |
|-------|-------|--------|
| Auth | 5 | ✅ |
| Live (health, config, logs) | 15 | ✅ |
| No-Supervisor (502s) | 10 | ✅ |
| **Total** | **30** | **All passing** |

## Tooling

- **Runtime**: Python 3.11+, aiohttp, ruamel.yaml
- **Dev**: uv, ruff, mypy, pytest, pytest-aiohttp
- **Integration**: Docker, docker-compose, requests, websocket-client
- **CI**: GitHub Actions (lint + test + docker build)
