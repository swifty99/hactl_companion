"""Integration tests — endpoints that require Supervisor (should return 502 gracefully)."""

from __future__ import annotations

import requests


class TestSupervisorProxy502:
    """All Supervisor proxy endpoints should return 502 when no Supervisor is present."""

    def test_supervisor_info(self, companion_url: str, auth_headers: dict[str, str]) -> None:
        r = requests.get(f"{companion_url}/v1/supervisor/info", headers=auth_headers, timeout=10)
        assert r.status_code == 502
        assert "unreachable" in r.text.lower()

    def test_supervisor_addons(self, companion_url: str, auth_headers: dict[str, str]) -> None:
        r = requests.get(f"{companion_url}/v1/supervisor/addons", headers=auth_headers, timeout=10)
        assert r.status_code == 502

    def test_supervisor_backups(self, companion_url: str, auth_headers: dict[str, str]) -> None:
        r = requests.get(f"{companion_url}/v1/supervisor/backups", headers=auth_headers, timeout=10)
        assert r.status_code == 502

    def test_supervisor_backup_create(self, companion_url: str, auth_headers: dict[str, str]) -> None:
        r = requests.post(f"{companion_url}/v1/supervisor/backups/new", headers=auth_headers, timeout=10)
        assert r.status_code == 502

    def test_supervisor_addon_logs(self, companion_url: str, auth_headers: dict[str, str]) -> None:
        r = requests.get(f"{companion_url}/v1/supervisor/addon/some_addon/logs", headers=auth_headers, timeout=10)
        assert r.status_code == 502


class TestLogsSupervisor502:
    """Log endpoints that proxy to Supervisor should return 502."""

    def test_supervisor_logs(self, companion_url: str, auth_headers: dict[str, str]) -> None:
        r = requests.get(f"{companion_url}/v1/logs/supervisor", headers=auth_headers, timeout=10)
        assert r.status_code == 502

    def test_addon_logs(self, companion_url: str, auth_headers: dict[str, str]) -> None:
        r = requests.get(f"{companion_url}/v1/logs/addon/mosquitto", headers=auth_headers, timeout=10)
        assert r.status_code == 502


class TestHaCli502:
    """HA CLI bridge endpoints should return 502 when ha CLI is not available."""

    def test_reload(self, companion_url: str, auth_headers: dict[str, str]) -> None:
        r = requests.post(f"{companion_url}/v1/ha/reload/automation", headers=auth_headers, timeout=10)
        assert r.status_code == 502
        assert "ha CLI not available" in r.text

    def test_restart(self, companion_url: str, auth_headers: dict[str, str]) -> None:
        r = requests.post(f"{companion_url}/v1/ha/restart", headers=auth_headers, timeout=10)
        assert r.status_code == 502

    def test_resolution(self, companion_url: str, auth_headers: dict[str, str]) -> None:
        r = requests.get(f"{companion_url}/v1/ha/resolution", headers=auth_headers, timeout=10)
        assert r.status_code == 502

    def test_check_config(self, companion_url: str, auth_headers: dict[str, str]) -> None:
        r = requests.post(f"{companion_url}/v1/ha/check-config", headers=auth_headers, timeout=10)
        assert r.status_code == 502
