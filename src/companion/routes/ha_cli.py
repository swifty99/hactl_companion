"""HA CLI bridge endpoints."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from aiohttp import web

COMMAND_TIMEOUT = 30

ALLOWED_RELOAD_DOMAINS: set[str] = {
    "automation",
    "script",
    "scene",
    "group",
    "core",
    "input_boolean",
    "input_number",
    "input_select",
    "template",
}


@dataclass
class RouteDef:
    method: str
    path: str
    handler: object


async def _run_ha_command(args: list[str], timeout: int = COMMAND_TIMEOUT) -> dict[str, object]:
    """Execute an ha CLI command and return stdout/stderr."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return {
            "exit_code": proc.returncode,
            "stdout": stdout.decode("utf-8", errors="replace").strip(),
            "stderr": stderr.decode("utf-8", errors="replace").strip(),
        }
    except TimeoutError as exc:
        raise web.HTTPGatewayTimeout(text=f"Command timed out after {timeout}s") from exc
    except FileNotFoundError as exc:
        raise web.HTTPBadGateway(text="ha CLI not available") from exc


async def post_reload(request: web.Request) -> web.Response:
    """POST /v1/ha/reload/{domain} — reload a specific domain."""
    domain = request.match_info["domain"]

    if domain not in ALLOWED_RELOAD_DOMAINS:
        raise web.HTTPBadRequest(
            text=f"Invalid domain: {domain}. Allowed: {', '.join(sorted(ALLOWED_RELOAD_DOMAINS))}"
        )

    result = await _run_ha_command(["ha", domain, "reload"])
    return web.json_response({"action": f"reload/{domain}", **result})


async def post_restart(request: web.Request) -> web.Response:
    """POST /v1/ha/restart — restart HA Core."""
    result = await _run_ha_command(["ha", "core", "restart"])
    return web.json_response({"action": "restart", **result})


async def get_resolution(request: web.Request) -> web.Response:
    """GET /v1/ha/resolution — resolution center info."""
    result = await _run_ha_command(["ha", "resolution", "info"])
    return web.json_response({"action": "resolution", **result})


async def post_check_config(request: web.Request) -> web.Response:
    """POST /v1/ha/check-config — validate HA config."""
    result = await _run_ha_command(["ha", "core", "check-config"])
    return web.json_response({"action": "check-config", **result})


routes: list[RouteDef] = [
    RouteDef("POST", r"/v1/ha/reload/{domain}", post_reload),
    RouteDef("POST", "/v1/ha/restart", post_restart),
    RouteDef("GET", "/v1/ha/resolution", get_resolution),
    RouteDef("POST", "/v1/ha/check-config", post_check_config),
]
