"""Tests for YAML config write endpoints (Phase 3)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

if TYPE_CHECKING:
    from aiohttp.test_utils import TestClient


NEW_YAML_CONTENT = """- id: automation.door_light
  alias: Door Light Updated
  trigger:
    - platform: state
      entity_id: binary_sensor.front_door
      to: "on"
  action:
    - service: light.turn_on
      target:
        entity_id: light.hallway_new
"""


async def test_dry_run_returns_diff(client: TestClient, auth_headers: dict[str, str]) -> None:
    """dry_run=true should return a diff without modifying the file."""
    resp = await client.put(
        "/v1/config/file?path=automations.yaml&dry_run=true",
        data=NEW_YAML_CONTENT,
        headers={**auth_headers, "Content-Type": "text/plain"},
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "dry_run"
    assert "diff" in data
    # Diff should show changes
    assert "---" in data["diff"] or data["diff"] == ""


async def test_dry_run_is_default(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Default should be dry_run=true."""
    resp = await client.put(
        "/v1/config/file?path=automations.yaml",
        data=NEW_YAML_CONTENT,
        headers={**auth_headers, "Content-Type": "text/plain"},
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "dry_run"


@patch("companion.routes.config._validate_config", new_callable=AsyncMock, return_value=None)
async def test_apply_creates_backup(
    mock_validate: AsyncMock, client: TestClient, auth_headers: dict[str, str], config_dir: Path
) -> None:
    """dry_run=false should create a backup file."""
    resp = await client.put(
        "/v1/config/file?path=automations.yaml&dry_run=false",
        data=NEW_YAML_CONTENT,
        headers={**auth_headers, "Content-Type": "text/plain"},
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "applied"
    assert "backup" in data

    # Verify backup file exists
    backup_files = list(config_dir.glob("automations.yaml.bak.*"))
    assert len(backup_files) == 1

    # Verify new content was written
    content = (config_dir / "automations.yaml").read_text()
    assert "Door Light Updated" in content


@patch("companion.routes.config._validate_config", new_callable=AsyncMock)
async def test_apply_validation_failure_restores(
    mock_validate: AsyncMock, client: TestClient, auth_headers: dict[str, str], config_dir: Path
) -> None:
    """If config validation fails, the backup should be restored."""
    mock_validate.return_value = {"valid": False, "error": "Invalid config"}

    original_content = (config_dir / "automations.yaml").read_text()

    resp = await client.put(
        "/v1/config/file?path=automations.yaml&dry_run=false",
        data=NEW_YAML_CONTENT,
        headers={**auth_headers, "Content-Type": "text/plain"},
    )
    assert resp.status == 400

    # Original content should be restored
    restored_content = (config_dir / "automations.yaml").read_text()
    assert restored_content == original_content


async def test_write_empty_body_rejected(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = await client.put(
        "/v1/config/file?path=automations.yaml&dry_run=false",
        data="",
        headers={**auth_headers, "Content-Type": "text/plain"},
    )
    assert resp.status == 400


async def test_write_invalid_yaml_rejected(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = await client.put(
        "/v1/config/file?path=automations.yaml&dry_run=false",
        data=": invalid:\n  - :\n  [broken",
        headers={**auth_headers, "Content-Type": "text/plain"},
    )
    assert resp.status == 400


async def test_write_path_traversal_rejected(client: TestClient, auth_headers: dict[str, str]) -> None:
    resp = await client.put(
        "/v1/config/file?path=../etc/passwd&dry_run=false",
        data="hacked: true\n",
        headers={**auth_headers, "Content-Type": "text/plain"},
    )
    assert resp.status == 400


async def test_write_secrets_denied(client: TestClient, auth_headers: dict[str, str], config_dir: Path) -> None:
    (config_dir / "secrets.yaml").write_text("wifi_password: hunter2\n")
    resp = await client.put(
        "/v1/config/file?path=secrets.yaml&dry_run=false",
        data="wifi_password: newpassword\n",
        headers={**auth_headers, "Content-Type": "text/plain"},
    )
    assert resp.status == 403
