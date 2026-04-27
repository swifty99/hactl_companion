"""Direct log access endpoints."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import aiohttp
from aiohttp import web

SUPERVISOR_URL = "http://supervisor"
LOG_TIMEOUT = aiohttp.ClientTimeout(total=10)
LOG_LEVELS = {"critical", "error", "warning", "info", "debug"}
# Regex to match HA core log lines: "2026-04-27 12:00:00.000 ERROR (MainThread) ..."
LOG_LINE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}(?:\.\d+)?\s+(\w+)\s")
MAX_LINES = 10000
DEFAULT_LINES = 100


@dataclass
class RouteDef:
    method: str
    path: str
    handler: object


def _tail_lines(text: str, n: int) -> list[str]:
    """Return last n lines from text."""
    lines = text.splitlines()
    return lines[-n:] if len(lines) > n else lines


def _filter_by_level(lines: list[str], level: str) -> list[str]:
    """Filter log lines to only include entries at or above the given level."""
    level_order = ["debug", "info", "warning", "error", "critical"]
    min_idx = level_order.index(level)
    allowed = set(level_order[min_idx:])

    result: list[str] = []
    include_continuation = False
    for line in lines:
        m = LOG_LINE_RE.match(line)
        if m:
            line_level = m.group(1).lower()
            include_continuation = line_level in allowed
        # Lines without a level prefix are continuation lines (tracebacks etc.)
        if include_continuation:
            result.append(line)
    return result


def _supervisor_headers() -> dict[str, str]:
    token = os.environ.get("SUPERVISOR_TOKEN", "")
    return {"Authorization": f"Bearer {token}"}


async def get_core_logs(request: web.Request) -> web.Response:
    """GET /v1/logs/core — read HA Core log from /config/home-assistant.log."""
    lines_param = min(int(request.query.get("lines", str(DEFAULT_LINES))), MAX_LINES)
    level = request.query.get("level", "").lower()

    if level and level not in LOG_LEVELS:
        raise web.HTTPBadRequest(text=f"Invalid level: {level}. Must be one of: {', '.join(sorted(LOG_LEVELS))}")

    config_base = request.app["config_base_path"]
    log_path = Path(config_base) / "home-assistant.log"

    if not log_path.is_file():
        raise web.HTTPNotFound(text="Core log file not found")

    content = log_path.read_text(encoding="utf-8", errors="replace")
    lines = _tail_lines(content, lines_param)

    if level:
        lines = _filter_by_level(lines, level)

    return web.json_response({"source": "core", "lines": lines, "count": len(lines)})


async def get_supervisor_logs(request: web.Request) -> web.Response:
    """GET /v1/logs/supervisor — supervisor logs via Supervisor API."""
    lines_param = min(int(request.query.get("lines", str(DEFAULT_LINES))), MAX_LINES)

    try:
        async with aiohttp.ClientSession(timeout=LOG_TIMEOUT) as session, session.get(
            f"{SUPERVISOR_URL}/supervisor/logs",
            headers=_supervisor_headers(),
        ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise web.HTTPBadGateway(text=f"Supervisor returned {resp.status}: {text}")
                text = await resp.text()
    except aiohttp.ClientError as exc:
        raise web.HTTPBadGateway(text=f"Supervisor unreachable: {exc}") from exc

    lines = _tail_lines(text, lines_param)
    return web.json_response({"source": "supervisor", "lines": lines, "count": len(lines)})


async def get_addon_logs(request: web.Request) -> web.Response:
    """GET /v1/logs/addon/{slug} — add-on logs via Supervisor API."""
    slug = request.match_info["slug"]
    if not slug or not all(c.isalnum() or c in ("_", "-") for c in slug):
        raise web.HTTPBadRequest(text="Invalid add-on slug")

    lines_param = min(int(request.query.get("lines", str(DEFAULT_LINES))), MAX_LINES)

    try:
        async with aiohttp.ClientSession(timeout=LOG_TIMEOUT) as session, session.get(
            f"{SUPERVISOR_URL}/addons/{slug}/logs",
            headers=_supervisor_headers(),
        ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise web.HTTPBadGateway(text=f"Supervisor returned {resp.status}: {text}")
                text = await resp.text()
    except aiohttp.ClientError as exc:
        raise web.HTTPBadGateway(text=f"Supervisor unreachable: {exc}") from exc

    lines = _tail_lines(text, lines_param)
    return web.json_response({"source": f"addon/{slug}", "lines": lines, "count": len(lines)})


routes: list[RouteDef] = [
    RouteDef("GET", "/v1/logs/core", get_core_logs),
    RouteDef("GET", "/v1/logs/supervisor", get_supervisor_logs),
    RouteDef("GET", r"/v1/logs/addon/{slug}", get_addon_logs),
]
