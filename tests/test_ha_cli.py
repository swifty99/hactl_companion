"""Tests for HA CLI bridge endpoints (Phase 6)."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

if TYPE_CHECKING:
    from aiohttp.test_utils import TestClient


def _mock_process(returncode: int = 0, stdout: str = "OK", stderr: str = "") -> AsyncMock:
    proc = AsyncMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(
        return_value=(stdout.encode("utf-8"), stderr.encode("utf-8"))
    )
    return proc


@patch("companion.routes.ha_cli.asyncio.create_subprocess_exec")
async def test_reload_automation(
    mock_exec: AsyncMock, client: TestClient, auth_headers: dict[str, str]
) -> None:
    mock_exec.return_value = _mock_process(stdout="Reloaded automations")

    resp = await client.post("/v1/ha/reload/automation", headers=auth_headers)
    assert resp.status == 200
    data = await resp.json()
    assert data["action"] == "reload/automation"
    assert data["exit_code"] == 0
    mock_exec.assert_called_once_with(
        "ha", "automation", "reload",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )


async def test_reload_invalid_domain(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = await client.post("/v1/ha/reload/malicious_command", headers=auth_headers)
    assert resp.status == 400


@patch("companion.routes.ha_cli.asyncio.create_subprocess_exec")
async def test_restart(mock_exec: AsyncMock, client: TestClient, auth_headers: dict[str, str]) -> None:
    mock_exec.return_value = _mock_process(stdout="Restarting")

    resp = await client.post("/v1/ha/restart", headers=auth_headers)
    assert resp.status == 200
    data = await resp.json()
    assert data["action"] == "restart"


@patch("companion.routes.ha_cli.asyncio.create_subprocess_exec")
async def test_resolution_info(mock_exec: AsyncMock, client: TestClient, auth_headers: dict[str, str]) -> None:
    mock_exec.return_value = _mock_process(stdout='{"issues": [], "suggestions": []}')

    resp = await client.get("/v1/ha/resolution", headers=auth_headers)
    assert resp.status == 200
    data = await resp.json()
    assert data["action"] == "resolution"


@patch("companion.routes.ha_cli.asyncio.create_subprocess_exec")
async def test_check_config(mock_exec: AsyncMock, client: TestClient, auth_headers: dict[str, str]) -> None:
    mock_exec.return_value = _mock_process(stdout="Configuration valid")

    resp = await client.post("/v1/ha/check-config", headers=auth_headers)
    assert resp.status == 200
    data = await resp.json()
    assert data["action"] == "check-config"
    assert data["exit_code"] == 0


@patch("companion.routes.ha_cli.asyncio.create_subprocess_exec")
async def test_command_timeout(mock_exec: AsyncMock, client: TestClient, auth_headers: dict[str, str]) -> None:
    async def slow_communicate() -> tuple[bytes, bytes]:
        raise TimeoutError

    proc = AsyncMock()
    proc.communicate = slow_communicate
    mock_exec.return_value = proc

    resp = await client.post("/v1/ha/restart", headers=auth_headers)
    assert resp.status == 504


async def test_arbitrary_command_rejected(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Only whitelisted domains should be allowed."""
    resp = await client.post("/v1/ha/reload/rm", headers=auth_headers)
    assert resp.status == 400

    resp = await client.post("/v1/ha/reload/shell", headers=auth_headers)
    assert resp.status == 400
