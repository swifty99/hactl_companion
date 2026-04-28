# hactl-companion v2 — Implementation Plan

> Repo: `swifty99/hactl_companion` (Python, aiohttp)  
> Scope: **YAML file access only** — things the HA REST/WS API cannot do.  
> Everything else (reload, check-config, logs, supervisor) handled by hactl directly via HA API.

---

## Design Principle

Companion exists because HA exposes **zero API** for:
- Reading YAML config file contents (template.yaml, scripts.yaml, automations.yaml)
- Writing/editing YAML blocks in-place
- Resolving `!include` / `!include_dir_named` directives
- Discovering script parameters (`fields:` key) or template sensor Jinja2 source

hactl already handles via HA API:
- Reload: `POST /api/services/{domain}/reload`
- Config check: WS `call_service` → `homeassistant/check_config`
- Logs: WS `system_log/list` + REST `/api/error_log`
- Config entries: WS `config/entries`
- Supervisor: WS `hassio/addon/info`

---

## v2 API Surface (20 endpoints)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/v1/health` | Liveness check |
| GET | `/v1/config/files` | List YAML config files in /config |
| GET | `/v1/config/file?path=&resolve=true` | Read file content (with !include resolution) |
| GET | `/v1/config/block?path=&id=` | Read specific block from a config file |
| PUT | `/v1/config/file?path=&dry_run=true` | Write file (dry-run or apply with backup) |
| GET | `/v1/config/templates` | List all template sensor/binary_sensor definitions |
| GET | `/v1/config/template?id=<unique_id>` | Get single template definition (YAML) |
| PUT | `/v1/config/template?id=<unique_id>&dry_run=true` | Update template definition |
| POST | `/v1/config/template` | Create new template sensor |
| DELETE | `/v1/config/template?id=<unique_id>` | Delete template sensor |
| GET | `/v1/config/scripts` | List all script definitions with fields |
| GET | `/v1/config/script?id=<script_id>` | Get single script definition (YAML) |
| PUT | `/v1/config/script?id=<script_id>&dry_run=true` | Update script definition |
| POST | `/v1/config/script` | Create new script |
| DELETE | `/v1/config/script?id=<script_id>` | Delete script |
| GET | `/v1/config/automations` | List all automation definitions |
| GET | `/v1/config/automation?id=<automation_id>` | Get single automation definition (YAML) |
| PUT | `/v1/config/automation?id=<automation_id>&dry_run=true` | Update automation definition |
| POST | `/v1/config/automation` | Create new automation |
| DELETE | `/v1/config/automation?id=<automation_id>` | Delete automation |

---

## Phase 1: Strip Dead Endpoints

**Goal**: Remove everything hactl handles directly.

| # | Task | Files |
|---|------|-------|
| 1.1 | Delete `src/companion/routes/supervisor.py` | routes/ |
| 1.2 | Delete `src/companion/routes/logs.py` | routes/ |
| 1.3 | Delete `src/companion/routes/ha_cli.py` | routes/ |
| 1.4 | Delete `tests/test_supervisor.py` | tests/ |
| 1.5 | Delete `tests/test_logs.py` | tests/ |
| 1.6 | Delete `tests/test_ha_cli.py` | tests/ |
| 1.7 | Remove route registrations from `server.py` | server.py |
| 1.8 | Update `openapi/companion-v1.yaml` — remove 12 paths | openapi/ |
| 1.9 | Run `pytest` + `ruff` + `mypy` — green | CI |

**Removed endpoints** (12):
- `/v1/supervisor/info`, `/v1/supervisor/addons`, `/v1/supervisor/backups`, `/v1/supervisor/backups/new`, `/v1/supervisor/addon/{slug}/logs`
- `/v1/logs/core`, `/v1/logs/supervisor`, `/v1/logs/addon/{slug}`
- `/v1/ha/reload/{domain}`, `/v1/ha/restart`, `/v1/ha/resolution`, `/v1/ha/check-config`

**Kept endpoints** (5):
- `/v1/health`, `/v1/config/files`, `/v1/config/file` (GET+PUT), `/v1/config/block`

---

## Phase 2: !include Resolution

**Goal**: Config file reads resolve HA YAML includes, returning complete content.

| # | Task | Details |
|---|------|---------|
| 2.1 | Implement `YamlResolver` class | `src/companion/yaml_resolver.py` |
| 2.2 | Handle `!include <path>` | Inline file content at reference point |
| 2.3 | Handle `!include_dir_named <dir>` | Merge directory of YAML files as named dict |
| 2.4 | Handle `!include_dir_list <dir>` | Merge as list |
| 2.5 | Handle `!include_dir_merge_named <dir>` | Merge named with deep merge |
| 2.6 | Add `resolve` query param to `GET /v1/config/file` | Default: `true` |
| 2.7 | Security: resolved paths must stay within `/config` | Path traversal prevention |
| 2.8 | Tests: fixture with `configuration.yaml` using `!include template.yaml` | tests/test_config.py |
| 2.9 | Tests: `!include_dir_named packages` with 2 package files | tests/test_config.py |
| 2.10 | Tests: `resolve=false` returns raw content | tests/test_config.py |

**Implementation notes**:
- Use `ruamel.yaml` with custom constructors for `!include` tags
- Resolve relative to the file containing the `!include`
- Circular include detection (set of visited paths)
- `secrets.yaml` exclusion applies to resolved content too

---

## Phase 3: Template Sensor Endpoints

**Goal**: Structured CRUD for template sensors defined in `template.yaml`.

| # | Task | Details |
|---|------|---------|
| 3.1 | `GET /v1/config/templates` | Parse template.yaml (resolved), extract all sensor/binary_sensor blocks |
| 3.2 | Response schema | `{"templates": [{"unique_id", "name", "domain", "state", "unit_of_measurement", "device_class"}]}` |
| 3.3 | `GET /v1/config/template?id=<unique_id>` | Find block by unique_id, return as YAML text |
| 3.4 | `PUT /v1/config/template?id=<unique_id>&dry_run=true` | Replace block, show diff (dry_run) or write + backup (apply) |
| 3.5 | `POST /v1/config/template` | Append new block to template.yaml, body = YAML |
| 3.6 | `DELETE /v1/config/template?id=<unique_id>` | Remove block from template.yaml |
| 3.7 | Validation: require `unique_id` in all template blocks | Return 400 if missing |
| 3.8 | Tests: list templates from fixture | tests/test_templates.py |
| 3.9 | Tests: get by id, not-found → 404 | tests/test_templates.py |
| 3.10 | Tests: create, update (dry-run + apply), delete | tests/test_templates.py |

**template.yaml structure** (from user's real config):
```yaml
- sensor:
    - name: "Energie Zählerstand Flur"
      unit_of_measurement: "kWh"
      state: "{{(states('sensor.energieverbrauch_total')|float(0) + ...}}"
      unique_id: uuidTemplatesddfgfdffewesdsfsckl
- binary_sensor:
    - name: "Wohnzimmer Bewegung doublechek"
      state: |-
        {% set motion = ... %}
      unique_id: uuidTemplatesdzaktiwozimotiondoubel
```

**Parsing logic**:
- Top-level list, each item has `sensor:` or `binary_sensor:` key
- Inner value is list of sensor defs
- Match by `unique_id` field

---

## Phase 4: Script Definition Endpoints

**Goal**: Structured CRUD for scripts defined in `scripts.yaml`.

| # | Task | Details |
|---|------|---------|
| 4.1 | `GET /v1/config/scripts` | Parse scripts.yaml, return list with metadata |
| 4.2 | Response schema | `{"scripts": [{"id", "alias", "mode", "fields": [{"name", "description", "required", "selector"}]}]}` |
| 4.3 | `GET /v1/config/script?id=<script_id>` | Return full YAML block for script |
| 4.4 | `PUT /v1/config/script?id=<script_id>&dry_run=true` | Update script definition |
| 4.5 | `POST /v1/config/script` | Create new script (body = YAML with id as top-level key) |
| 4.6 | `DELETE /v1/config/script?id=<script_id>` | Remove script from scripts.yaml |
| 4.7 | Tests: list, get, create, update, delete | tests/test_scripts.py |

**scripts.yaml structure** (from user's real config):
```yaml
kino_start:
  alias: Kino Start
  mode: single
  fields:
    brightness:
      description: "Target brightness"
      required: false
      selector:
        number:
          min: 0
          max: 255
  sequence:
    - service: light.turn_on
      ...
```

**Parsing logic**:
- Top-level dict, keys = script IDs
- Each value has `alias`, `mode`, optional `fields`, `sequence`

---

## Phase 5: Automation Definition Endpoints

**Goal**: Structured CRUD for automations defined in `automations.yaml`.

| # | Task | Details |
|---|------|---------|
| 5.1 | `GET /v1/config/automations` | Parse automations.yaml, return list |
| 5.2 | Response schema | `{"automations": [{"id", "alias", "mode", "description"}]}` |
| 5.3 | `GET /v1/config/automation?id=<id>` | Full YAML block for automation |
| 5.4 | `PUT /v1/config/automation?id=<id>&dry_run=true` | Update |
| 5.5 | `POST /v1/config/automation` | Create |
| 5.6 | `DELETE /v1/config/automation?id=<id>` | Delete |
| 5.7 | Tests | tests/test_automations.py |

**automations.yaml structure**:
```yaml
- id: "1234567890"
  alias: "Turn on lights at sunset"
  mode: single
  trigger:
    - platform: sun
      event: sunset
  action:
    - service: light.turn_on
```

**Parsing logic**:
- Top-level list, each item is a dict with `id` field
- Match by `id`

---

## Phase 6: OpenAPI Spec + CI

| # | Task | Details |
|---|------|---------|
| 6.1 | Regenerate `openapi/companion-v1.yaml` | 20 endpoints |
| 6.2 | Add schema definitions for all response types | components/schemas |
| 6.3 | Update CI workflow — pytest covers all new tests | .github/workflows/ci.yml |
| 6.4 | Full `ruff` + `mypy` + `pytest` green | Verification |
| 6.5 | Tag release `v0.2.0` | Git tag |

---

## Test Fixtures

Create `testdata/fixtures/` in companion repo:

```
testdata/fixtures/
├── configuration.yaml    # with !include template.yaml, !include_dir_named packages
├── template.yaml         # 3 template sensors (sensor + binary_sensor)
├── scripts.yaml          # 3 scripts (one with fields)
├── automations.yaml      # 3 automations
├── secrets.yaml          # must be denied
└── packages/
    ├── energy.yaml       # package with template sensors
    └── security.yaml     # package with automations
```

---

## Metrics Targets

| Phase | Unit Tests | Coverage |
|-------|-----------|----------|
| After Phase 1 | ≥5 (health + config basics) | |
| After Phase 2 | ≥15 (+ include resolution) | |
| After Phase 3 | ≥30 (+ templates CRUD) | |
| After Phase 4 | ≥42 (+ scripts CRUD) | |
| After Phase 5 | ≥54 (+ automations CRUD) | |
| After Phase 6 | ≥56 (+ OpenAPI) | |

---

## Execution Order

```
Phase 1 (strip) → Phase 2 (!include) → Phase 3-5 (parallel: templates, scripts, automations) → Phase 6 (spec + release)
```

Phases 3, 4, 5 are independent and can be developed in parallel since they follow the same pattern on different YAML structures.

---

## Done Criteria

- [ ] 20 endpoints implemented and tested
- [ ] `!include` / `!include_dir_named` / `!include_dir_list` / `!include_dir_merge_named` all work
- [ ] `secrets.yaml` always denied (read, include, block)
- [ ] Path traversal blocked in all file operations
- [ ] All writes create `.bak.<timestamp>` backup before modifying
- [ ] Dry-run returns unified diff without modifying files
- [ ] OpenAPI spec committed and validates against implementation
- [ ] `ruff` + `mypy` + `pytest` all green
- [ ] Docker image builds and runs
- [ ] Tagged `v0.2.0`
