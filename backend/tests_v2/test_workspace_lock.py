import json
from pathlib import Path
import sys

import pytest

from aegis_v2.workspace_lock import WorkspaceLock
from tests_v2.test_discovery import platform

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import run as launcher


def test_a_second_server_cannot_acquire_the_same_workspace(tmp_path):
    first = WorkspaceLock(tmp_path).acquire()
    try:
        with pytest.raises(RuntimeError, match="already has a running"):
            WorkspaceLock(tmp_path).acquire()
        other = WorkspaceLock(tmp_path / "other").acquire()
        other.close()
    finally:
        first.close()
    replacement = WorkspaceLock(tmp_path).acquire()
    replacement.close()


def test_old_supervisor_cannot_replace_new_state_and_archives_remain(tmp_path):
    path = tmp_path / "live-workspace.json"
    older = {"status": "ready", "launch_id": "older", "managed_workspace": True}
    newer = {"status": "ready", "launch_id": "newer", "managed_workspace": True}
    launcher.write_state(path, older)
    launcher.write_state(path, newer)
    launcher.write_state(path, older | {"status": "stopped"})
    assert json.loads(path.read_text())["launch_id"] == "newer"
    assert json.loads((tmp_path / "live-instances" / "older.json").read_text())["status"] == "stopped"
    assert json.loads((tmp_path / "live-instances" / "newer.json").read_text())["status"] == "ready"


def test_api_rejects_a_duplicate_managed_worker_and_releases_the_lock(platform):
    from dataclasses import replace
    from fastapi.testclient import TestClient
    from aegis_v2.api import create_app
    p, _, _, _ = platform
    settings = replace(p.settings, managed_workspace=True, workspace_release="verified-release")
    with TestClient(create_app(settings, platform=p)) as first:
        health = first.get("/api/health").json()
        assert health["managed_workspace"] and health["workspace_release"] == "verified-release"
        with pytest.raises(RuntimeError, match="already has a running"):
            with TestClient(create_app(settings, platform=p)):
                pass
        assert first.get("/api/health").status_code == 200
    with TestClient(create_app(settings, platform=p)) as replacement:
        assert replacement.get("/api/health").status_code == 200
