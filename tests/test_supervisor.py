"""Tests for Supervisor API proxy endpoints (Phase 4)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

if TYPE_CHECKING:
    from aiohttp.test_utils import TestClient


def _mock_supervisor_response(data: dict[str, object], status: int = 200) -> AsyncMock:
    """Create a mock aiohttp response for the Supervisor API."""
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value={"result": "ok", "data": data})
    resp.text = AsyncMock(return_value=str(data))
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


def _mock_session(response: AsyncMock) -> MagicMock:
    session = MagicMock()
    session.get = MagicMock(return_value=response)
    session.post = MagicMock(return_value=response)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


@patch("companion.routes.supervisor.aiohttp.ClientSession")
async def test_info_returns_shaped_response(
    mock_cls: MagicMock, client: TestClient, auth_headers: dict[str, str]
) -> None:
    data = {
        "hostname": "haos",
        "operating_system": "Home Assistant OS",
        "arch": "amd64",
        "supervisor": "2026.04.0",
        "homeassistant": "2026.4.3",
        "disk_total": 32.0,
        "disk_used": 8.5,
        "disk_free": 23.5,
        "extra_field": "should be excluded",
    }
    mock_cls.return_value = _mock_session(_mock_supervisor_response(data))

    resp = await client.get("/v1/supervisor/info", headers=auth_headers)
    assert resp.status == 200
    result = await resp.json()
    assert result["hostname"] == "haos"
    assert result["arch"] == "amd64"
    assert "extra_field" not in result


@patch("companion.routes.supervisor.aiohttp.ClientSession")
async def test_addons_list(mock_cls: MagicMock, client: TestClient, auth_headers: dict[str, str]) -> None:
    data = {
        "addons": [
            {"name": "Mosquitto", "slug": "mosquitto", "version": "6.4", "state": "started"},
            {"name": "Terminal", "slug": "terminal", "version": "9.8", "state": "stopped"},
        ]
    }
    mock_cls.return_value = _mock_session(_mock_supervisor_response(data))

    resp = await client.get("/v1/supervisor/addons", headers=auth_headers)
    assert resp.status == 200
    result = await resp.json()
    assert len(result["addons"]) == 2
    assert result["addons"][0]["slug"] == "mosquitto"


@patch("companion.routes.supervisor.aiohttp.ClientSession")
async def test_backups_list(mock_cls: MagicMock, client: TestClient, auth_headers: dict[str, str]) -> None:
    data = {
        "backups": [
            {"slug": "abc123", "name": "Full backup", "date": "2026-04-27", "type": "full", "size": 1.5},
        ]
    }
    mock_cls.return_value = _mock_session(_mock_supervisor_response(data))

    resp = await client.get("/v1/supervisor/backups", headers=auth_headers)
    assert resp.status == 200
    result = await resp.json()
    assert len(result["backups"]) == 1
    assert result["backups"][0]["slug"] == "abc123"


@patch("companion.routes.supervisor.aiohttp.ClientSession")
async def test_backup_create(mock_cls: MagicMock, client: TestClient, auth_headers: dict[str, str]) -> None:
    data = {"slug": "new123"}
    mock_cls.return_value = _mock_session(_mock_supervisor_response(data))

    resp = await client.post("/v1/supervisor/backups/new", headers=auth_headers)
    assert resp.status == 200
    result = await resp.json()
    assert result["status"] == "created"


@patch("companion.routes.supervisor.aiohttp.ClientSession")
async def test_addon_logs(mock_cls: MagicMock, client: TestClient, auth_headers: dict[str, str]) -> None:
    log_text = "2026-04-27 Mosquitto started\n2026-04-27 Client connected"
    resp_mock = AsyncMock()
    resp_mock.status = 200
    resp_mock.text = AsyncMock(return_value=log_text)
    resp_mock.__aenter__ = AsyncMock(return_value=resp_mock)
    resp_mock.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock()
    session.get = MagicMock(return_value=resp_mock)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    mock_cls.return_value = session

    resp = await client.get("/v1/supervisor/addon/mosquitto/logs", headers=auth_headers)
    assert resp.status == 200
    text = await resp.text()
    assert "Mosquitto started" in text


@patch("companion.routes.supervisor.aiohttp.ClientSession")
async def test_supervisor_unreachable(
    mock_cls: MagicMock, client: TestClient, auth_headers: dict[str, str]
) -> None:
    import aiohttp as aiohttp_lib

    session = MagicMock()
    session.get = MagicMock(side_effect=aiohttp_lib.ClientError("connection refused"))
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    mock_cls.return_value = session

    resp = await client.get("/v1/supervisor/info", headers=auth_headers)
    assert resp.status == 502
