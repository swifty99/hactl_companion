"""Supervisor API proxy endpoints."""

from __future__ import annotations

import os
from dataclasses import dataclass

import aiohttp
from aiohttp import web

SUPERVISOR_URL = "http://supervisor"
INFO_TIMEOUT = aiohttp.ClientTimeout(total=10)
BACKUP_TIMEOUT = aiohttp.ClientTimeout(total=120)


@dataclass
class RouteDef:
    method: str
    path: str
    handler: object


def _supervisor_headers() -> dict[str, str]:
    token = os.environ.get("SUPERVISOR_TOKEN", "")
    return {"Authorization": f"Bearer {token}"}


async def _supervisor_get(path: str, timeout: aiohttp.ClientTimeout = INFO_TIMEOUT) -> dict[str, object]:
    """GET request to Supervisor API. Returns parsed JSON data field."""
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session, session.get(
            f"{SUPERVISOR_URL}{path}", headers=_supervisor_headers()
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise web.HTTPBadGateway(text=f"Supervisor returned {resp.status}: {text}")
            body = await resp.json()
            return body.get("data", body)  # type: ignore[no-any-return]
    except aiohttp.ClientError as exc:
        raise web.HTTPBadGateway(text=f"Supervisor unreachable: {exc}") from exc


async def _supervisor_post(path: str, timeout: aiohttp.ClientTimeout = INFO_TIMEOUT) -> dict[str, object]:
    """POST request to Supervisor API."""
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session, session.post(
            f"{SUPERVISOR_URL}{path}", headers=_supervisor_headers()
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise web.HTTPBadGateway(text=f"Supervisor returned {resp.status}: {text}")
            body = await resp.json()
            return body.get("data", body)  # type: ignore[no-any-return]
    except aiohttp.ClientError as exc:
        raise web.HTTPBadGateway(text=f"Supervisor unreachable: {exc}") from exc


async def get_supervisor_info(request: web.Request) -> web.Response:
    """GET /v1/supervisor/info — OS, arch, HA version, disk, memory."""
    data = await _supervisor_get("/info")
    shaped = {
        k: data.get(k)
        for k in ("hostname", "operating_system", "arch", "machine", "supervisor", "homeassistant",
                   "disk_total", "disk_used", "disk_free", "memory_total", "memory_used", "memory_free")
        if k in data
    }
    return web.json_response(shaped)


async def get_supervisor_addons(request: web.Request) -> web.Response:
    """GET /v1/supervisor/addons — installed add-ons + status."""
    data = await _supervisor_get("/addons")
    addons = data.get("addons", []) if isinstance(data, dict) else data
    shaped = []
    for addon in addons:  # type: ignore[union-attr]
        if isinstance(addon, dict):
            shaped.append({
                k: addon.get(k)
                for k in ("name", "slug", "version", "state", "description", "installed")
                if k in addon
            })
    return web.json_response({"addons": shaped})


async def get_supervisor_backups(request: web.Request) -> web.Response:
    """GET /v1/supervisor/backups — backup list."""
    data = await _supervisor_get("/backups")
    backups = data.get("backups", []) if isinstance(data, dict) else data
    shaped = []
    for backup in backups:  # type: ignore[union-attr]
        if isinstance(backup, dict):
            shaped.append({
                k: backup.get(k)
                for k in ("slug", "name", "date", "type", "size")
                if k in backup
            })
    return web.json_response({"backups": shaped})


async def post_supervisor_backup(request: web.Request) -> web.Response:
    """POST /v1/supervisor/backups/new — trigger a new backup."""
    data = await _supervisor_post("/backups/new/full", timeout=BACKUP_TIMEOUT)
    return web.json_response({"status": "created", "data": data})


async def get_addon_logs(request: web.Request) -> web.Response:
    """GET /v1/supervisor/addon/{slug}/logs — add-on logs."""
    slug = request.match_info["slug"]
    # Validate slug format (alphanumeric, underscores, hyphens)
    if not slug or not all(c.isalnum() or c in ("_", "-") for c in slug):
        raise web.HTTPBadRequest(text="Invalid add-on slug")

    try:
        async with aiohttp.ClientSession(timeout=INFO_TIMEOUT) as session, session.get(
            f"{SUPERVISOR_URL}/addons/{slug}/logs",
            headers=_supervisor_headers(),
        ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise web.HTTPBadGateway(text=f"Supervisor returned {resp.status}: {text}")
                text = await resp.text()
                return web.Response(text=text, content_type="text/plain")
    except aiohttp.ClientError as exc:
        raise web.HTTPBadGateway(text=f"Supervisor unreachable: {exc}") from exc


routes: list[RouteDef] = [
    RouteDef("GET", "/v1/supervisor/info", get_supervisor_info),
    RouteDef("GET", "/v1/supervisor/addons", get_supervisor_addons),
    RouteDef("GET", "/v1/supervisor/backups", get_supervisor_backups),
    RouteDef("POST", "/v1/supervisor/backups/new", post_supervisor_backup),
    RouteDef("GET", r"/v1/supervisor/addon/{slug}/logs", get_addon_logs),
]
