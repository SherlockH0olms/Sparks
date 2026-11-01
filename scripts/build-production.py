"""Build the actual AEGIS platform and write an immutable production release manifest."""
from __future__ import annotations

import argparse
import compileall
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", help="Live backend to check; defaults to the recorded workspace or the initial Granite backend.")
    args = parser.parse_args()
    state_file = ROOT / ".runtime" / "live-workspace.json"
    state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {}
    recorded_live = state.get("status") == "ready" and state.get("source") == str(ROOT) and state.get("mode") == "production"
    api_url = (args.api_url or (state.get("api_url") if recorded_live else None) or "http://127.0.0.1:8008").rstrip("/")
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is required.")
    backend = ROOT / "backend" / "aegis_v2"
    if not compileall.compile_dir(str(backend), quiet=1, force=True):
        raise RuntimeError("The Python backend did not compile.")
    release = ".next-release-main-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    frontend = ROOT / "frontend"
    env = os.environ.copy()
    env["AEGIS_NEXT_DIST_DIR"] = release
    subprocess.run([node, str(frontend / "node_modules" / "next" / "dist" / "bin" / "next"), "build"], cwd=frontend, env=env, check=True)
    artifact = frontend / release
    # Next's internal error bootstrap is a framework shell, not a rendered application page.
    pages = sorted(p for p in (artifact / "server" / "app").glob("*.html") if p.name != "_global-error.html")
    for page in pages:
        html = page.read_text(encoding="utf-8")
        if not re.search(r'<html\b[^>]*\blang="en"', html):
            raise RuntimeError("The production page is not English: " + page.name)
    if len(pages) < 10:
        raise RuntimeError("The production release is missing platform pages.")
    sys.path.insert(0, str(ROOT / "backend"))
    from aegis_v2.config import Settings
    import httpx
    settings = Settings.load()
    with httpx.Client(base_url=api_url + "/api", headers={"Authorization": "Bearer " + settings.admin_token}, timeout=10, trust_env=False) as client:
        health_response = client.get("/health")
        health_response.raise_for_status()
        health = health_response.json()
        if health.get("fixture_environment") or health.get("version") != "2.0.0":
            raise RuntimeError("The selected backend is a fixture, not the actual live platform.")
        if recorded_live and not args.api_url and health.get("instance_id") != state.get("instance_id"):
            raise RuntimeError("The recorded backend was replaced by a different instance.")
        target_response = client.get("/targets")
        target_response.raise_for_status()
        targets = target_response.json()
        campaigns_response = client.get("/campaigns")
        campaigns_response.raise_for_status()
        campaigns = campaigns_response.json()
    manifest = {
        "source": str(ROOT), "release": release, "frontend_artifact": str(artifact),
        "build_id": (artifact / "BUILD_ID").read_text(encoding="utf-8").strip(),
        "backend": str(backend), "backend_modules_compiled": len(list(backend.rglob("*.py"))),
        "interface_language": "en", "static_pages": [p.stem for p in pages],
        "live_backend": api_url, "platform_url": state.get("platform_url") if recorded_live else None,
        "preferred_ports": {"web": 3002, "api": 8008}, "automatic_port_selection": True,
        "fixture_environment": False, "saved_targets": len(targets), "saved_campaigns": len(campaigns),
        "attack_resources": health.get("red_attack_library", {}).get("unique_resources"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    runtime = ROOT / ".runtime"
    runtime.mkdir(exist_ok=True)
    (runtime / "current-production-build.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (ROOT / "Open MAIN Build.cmd").write_text(
        '@echo off\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\\Open-LiveWorkspace.ps1" -BuiltRelease "'
        + release + '" %*\nif errorlevel 1 pause\n', encoding="utf-8")
    (runtime / "MAIN-BUILD.txt").write_text(
        "AEGIS LOOP / ACTUAL PRODUCTION BUILD\n\nSource: " + str(ROOT)
        + "\nFrontend release: " + str(artifact)
        + "\nPython backend: " + str(backend)
        + "\nInterface: English\nChecked live backend: " + api_url
        + f"\nSaved targets: {len(targets)}\nSaved campaigns: {len(campaigns)}"
        + f"\nAvailable attack resources: {manifest['attack_resources']}"
        + "\n\nLaunch: Open MAIN Build.cmd\nWeb and API ports are selected automatically. The actual address is saved in .runtime/PLATFORM-URL.txt after validation.\nThe launcher preserves records and verifies the actual pages before opening the browser.\n",
        encoding="utf-8")
    print("Actual AEGIS production build completed: " + str(artifact), flush=True)
    print("Launcher: " + str(ROOT / "Open MAIN Build.cmd"), flush=True)


if __name__ == "__main__":
    main()
