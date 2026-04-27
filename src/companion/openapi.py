"""OpenAPI schema generation from registered routes."""

from __future__ import annotations

from companion import __version__

# Manually maintained response schemas for each endpoint group
_HEALTH_SCHEMA = {"type": "object", "properties": {"status": {"type": "string"}, "version": {"type": "string"}}}

_CONFIG_FILES_SCHEMA = {
    "type": "object",
    "properties": {"files": {"type": "array", "items": {"type": "string"}}},
}
_CONFIG_FILE_SCHEMA = {
    "type": "object",
    "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
}
_CONFIG_BLOCK_SCHEMA = {
    "type": "object",
    "properties": {"path": {"type": "string"}, "id": {"type": "string"}, "content": {"type": "string"}},
}
_CONFIG_WRITE_DRY_SCHEMA = {
    "type": "object",
    "properties": {"status": {"type": "string"}, "diff": {"type": "string"}},
}
_CONFIG_WRITE_APPLY_SCHEMA = {
    "type": "object",
    "properties": {"status": {"type": "string"}, "backup": {"type": "string"}},
}

_SUPERVISOR_INFO_SCHEMA = {"type": "object", "additionalProperties": True}
_ADDONS_SCHEMA = {"type": "object", "properties": {"addons": {"type": "array", "items": {"type": "object"}}}}
_BACKUPS_SCHEMA = {"type": "object", "properties": {"backups": {"type": "array", "items": {"type": "object"}}}}
_BACKUP_CREATED_SCHEMA = {
    "type": "object",
    "properties": {"status": {"type": "string"}, "data": {"type": "object"}},
}

_LOG_SCHEMA = {
    "type": "object",
    "properties": {
        "source": {"type": "string"},
        "lines": {"type": "array", "items": {"type": "string"}},
        "count": {"type": "integer"},
    },
}

_HA_CLI_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string"},
        "exit_code": {"type": "integer"},
        "stdout": {"type": "string"},
        "stderr": {"type": "string"},
    },
}


# Map of (method, path) -> endpoint metadata
ENDPOINT_META: dict[tuple[str, str], dict[str, object]] = {
    ("GET", "/v1/health"): {
        "summary": "Liveness check",
        "tags": ["health"],
        "response_schema": _HEALTH_SCHEMA,
    },
    ("GET", "/v1/config/files"): {
        "summary": "List YAML config files",
        "tags": ["config"],
        "response_schema": _CONFIG_FILES_SCHEMA,
    },
    ("GET", "/v1/config/file"): {
        "summary": "Read a config file",
        "tags": ["config"],
        "parameters": [{"name": "path", "in": "query", "required": True, "schema": {"type": "string"}}],
        "response_schema": _CONFIG_FILE_SCHEMA,
    },
    ("GET", "/v1/config/block"): {
        "summary": "Read a specific block from a config file",
        "tags": ["config"],
        "parameters": [
            {"name": "path", "in": "query", "required": True, "schema": {"type": "string"}},
            {"name": "id", "in": "query", "required": True, "schema": {"type": "string"}},
        ],
        "response_schema": _CONFIG_BLOCK_SCHEMA,
    },
    ("PUT", "/v1/config/file"): {
        "summary": "Write a config file (dry-run or apply)",
        "tags": ["config"],
        "parameters": [
            {"name": "path", "in": "query", "required": True, "schema": {"type": "string"}},
            {"name": "dry_run", "in": "query", "required": False, "schema": {"type": "string", "default": "true"}},
        ],
        "requestBody": {
            "content": {"text/plain": {"schema": {"type": "string"}}},
            "required": True,
        },
        "response_schema": _CONFIG_WRITE_DRY_SCHEMA,
    },
    ("GET", "/v1/supervisor/info"): {
        "summary": "System info via Supervisor",
        "tags": ["supervisor"],
        "response_schema": _SUPERVISOR_INFO_SCHEMA,
    },
    ("GET", "/v1/supervisor/addons"): {
        "summary": "Installed add-ons",
        "tags": ["supervisor"],
        "response_schema": _ADDONS_SCHEMA,
    },
    ("GET", "/v1/supervisor/backups"): {
        "summary": "Backup list",
        "tags": ["supervisor"],
        "response_schema": _BACKUPS_SCHEMA,
    },
    ("POST", "/v1/supervisor/backups/new"): {
        "summary": "Create a new backup",
        "tags": ["supervisor"],
        "response_schema": _BACKUP_CREATED_SCHEMA,
    },
    ("GET", "/v1/supervisor/addon/{slug}/logs"): {
        "summary": "Add-on logs",
        "tags": ["supervisor"],
        "parameters": [{"name": "slug", "in": "path", "required": True, "schema": {"type": "string"}}],
        "response_schema": {"type": "string"},
    },
    ("GET", "/v1/logs/core"): {
        "summary": "HA Core logs",
        "tags": ["logs"],
        "parameters": [
            {"name": "lines", "in": "query", "required": False, "schema": {"type": "integer", "default": 100}},
            {"name": "level", "in": "query", "required": False, "schema": {"type": "string"}},
        ],
        "response_schema": _LOG_SCHEMA,
    },
    ("GET", "/v1/logs/supervisor"): {
        "summary": "Supervisor logs",
        "tags": ["logs"],
        "parameters": [
            {"name": "lines", "in": "query", "required": False, "schema": {"type": "integer", "default": 100}},
        ],
        "response_schema": _LOG_SCHEMA,
    },
    ("GET", "/v1/logs/addon/{slug}"): {
        "summary": "Add-on logs",
        "tags": ["logs"],
        "parameters": [
            {"name": "slug", "in": "path", "required": True, "schema": {"type": "string"}},
            {"name": "lines", "in": "query", "required": False, "schema": {"type": "integer", "default": 100}},
        ],
        "response_schema": _LOG_SCHEMA,
    },
    ("POST", "/v1/ha/reload/{domain}"): {
        "summary": "Reload a domain",
        "tags": ["ha-cli"],
        "parameters": [{"name": "domain", "in": "path", "required": True, "schema": {"type": "string"}}],
        "response_schema": _HA_CLI_SCHEMA,
    },
    ("POST", "/v1/ha/restart"): {
        "summary": "Restart HA Core",
        "tags": ["ha-cli"],
        "response_schema": _HA_CLI_SCHEMA,
    },
    ("GET", "/v1/ha/resolution"): {
        "summary": "Resolution center info",
        "tags": ["ha-cli"],
        "response_schema": _HA_CLI_SCHEMA,
    },
    ("POST", "/v1/ha/check-config"): {
        "summary": "Validate HA configuration",
        "tags": ["ha-cli"],
        "response_schema": _HA_CLI_SCHEMA,
    },
}


def generate_spec() -> dict[str, object]:
    """Generate a full OpenAPI 3.0 spec dict from registered routes."""
    paths: dict[str, dict[str, object]] = {}

    for (method, path), meta in ENDPOINT_META.items():
        # Convert aiohttp path format {param} to OpenAPI {param} (same format)
        openapi_path = path
        if openapi_path not in paths:
            paths[openapi_path] = {}

        operation: dict[str, object] = {
            "summary": meta.get("summary", ""),
            "tags": meta.get("tags", []),
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {"application/json": {"schema": meta.get("response_schema", {})}},
                },
            },
        }

        if "parameters" in meta:
            operation["parameters"] = meta["parameters"]
        if "requestBody" in meta:
            operation["requestBody"] = meta["requestBody"]

        paths[openapi_path][method.lower()] = operation

    return {
        "openapi": "3.0.3",
        "info": {
            "title": "hactl-companion API",
            "version": __version__,
            "description": "HA Add-on exposing internal HA features for hactl CLI",
        },
        "servers": [{"url": "/", "description": "HA Ingress"}],
        "paths": paths,
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                },
            },
        },
        "security": [{"bearerAuth": []}],
    }


def write_spec(output_path: str = "openapi/companion-v1.yaml") -> None:
    """Generate and write the OpenAPI spec to a YAML file."""
    from pathlib import Path

    from ruamel.yaml import YAML

    spec = generate_spec()
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    y = YAML()
    y.default_flow_style = False
    with open(out, "w", encoding="utf-8") as f:
        y.dump(spec, f)


if __name__ == "__main__":
    write_spec()
