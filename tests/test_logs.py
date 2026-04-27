"""Tests for direct log access endpoints (Phase 5)."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

if TYPE_CHECKING:
    from aiohttp.test_utils import TestClient

FIXTURES_DIR = Path(__file__).parent.parent / "testdata" / "fixtures"


async def test_core_log_tail(client: TestClient, auth_headers: dict[str, str], config_dir: Path) -> None:
    """Should return the last N lines from core log."""
    shutil.copy2(FIXTURES_DIR / "home-assistant.log", config_dir / "home-assistant.log")

    resp = await client.get("/v1/logs/core?lines=3", headers=auth_headers)
    assert resp.status == 200
    data = await resp.json()
    assert data["source"] == "core"
    assert data["count"] == 3
    assert len(data["lines"]) == 3


async def test_core_log_filter_errors(client: TestClient, auth_headers: dict[str, str], config_dir: Path) -> None:
    """Should filter log lines by level."""
    shutil.copy2(FIXTURES_DIR / "home-assistant.log", config_dir / "home-assistant.log")

    resp = await client.get("/v1/logs/core?lines=100&level=error", headers=auth_headers)
    assert resp.status == 200
    data = await resp.json()
    assert data["count"] > 0
    # All returned primary lines should be ERROR or CRITICAL
    for line in data["lines"]:
        if line.startswith("20"):  # date-prefixed lines (not traceback continuations)
            assert "ERROR" in line or "CRITICAL" in line


async def test_core_log_includes_tracebacks(
    client: TestClient, auth_headers: dict[str, str], config_dir: Path
) -> None:
    """Error filter should include traceback continuation lines."""
    shutil.copy2(FIXTURES_DIR / "home-assistant.log", config_dir / "home-assistant.log")

    resp = await client.get("/v1/logs/core?lines=100&level=error", headers=auth_headers)
    data = await resp.json()
    text = "\n".join(data["lines"])
    assert "Traceback" in text
    assert "ConnectionError" in text


async def test_core_log_invalid_level(client: TestClient, auth_headers: dict[str, str], config_dir: Path) -> None:
    shutil.copy2(FIXTURES_DIR / "home-assistant.log", config_dir / "home-assistant.log")

    resp = await client.get("/v1/logs/core?level=bogus", headers=auth_headers)
    assert resp.status == 400


async def test_core_log_file_not_found(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Should return 404 when log file doesn't exist."""
    resp = await client.get("/v1/logs/core", headers=auth_headers)
    assert resp.status == 404


@patch("companion.routes.logs.aiohttp.ClientSession")
async def test_supervisor_logs(mock_cls: MagicMock, client: TestClient, auth_headers: dict[str, str]) -> None:
    log_text = "line1\nline2\nline3\nline4\nline5"
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

    resp = await client.get("/v1/logs/supervisor?lines=3", headers=auth_headers)
    assert resp.status == 200
    data = await resp.json()
    assert data["source"] == "supervisor"
    assert data["count"] == 3


@patch("companion.routes.logs.aiohttp.ClientSession")
async def test_addon_log_via_supervisor(mock_cls: MagicMock, client: TestClient, auth_headers: dict[str, str]) -> None:
    log_text = "addon log line 1\naddon log line 2"
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

    resp = await client.get("/v1/logs/addon/mosquitto?lines=10", headers=auth_headers)
    assert resp.status == 200
    data = await resp.json()
    assert data["source"] == "addon/mosquitto"
    assert data["count"] == 2
