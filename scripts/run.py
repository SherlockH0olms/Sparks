"""Cross-platform API and web launcher with health checks and clean shutdown."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parents[1]


def ready(url, processes):
    for _ in range(90):
        if any(process.poll() is not None for process in processes):
            raise RuntimeError("A server exited; inspect its output above.")
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(.5)
    raise RuntimeError("Server did not become ready: " + url)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("production", "dev", "demo"), default="production")
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--web-port", type=int, default=3000)
    args = parser.parse_args()
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Install Node.js first.")
    next_cli = ROOT / "frontend" / "node_modules" / "next" / "dist" / "bin" / "next"
    if not next_cli.exists():
        raise RuntimeError("Run npm install in frontend first.")
    sys.path.insert(0, str(ROOT / "scripts"))
    from setup import prepare
    prepare()
    backend_app = "aegis_v2.demo:create_demo_app" if args.mode == "demo" else "aegis_v2.api:app"
    backend = [sys.executable, "-m", "uvicorn", backend_app, "--host", "127.0.0.1", "--port", str(args.api_port)]
    if args.mode == "demo":
        backend.append("--factory")
        print("OFFLINE FIXTURE DEMO. Login: aegis-offline-demo-access-key-2026-only", flush=True)
    env = os.environ.copy()
    env["AEGIS_API"] = f"http://127.0.0.1:{args.api_port}"
    env["AEGIS_ALLOWED_ORIGINS"] = f"http://localhost:{args.web_port},http://127.0.0.1:{args.web_port}"
    processes = []
    try:
        processes.append(subprocess.Popen(backend, cwd=ROOT / "backend", env=env))
        ready(f"http://127.0.0.1:{args.api_port}/api/health", processes)
        if args.mode != "dev" and not (ROOT / "frontend" / ".next" / "BUILD_ID").exists():
            subprocess.run([node, str(next_cli), "build"], cwd=ROOT / "frontend", env=env, check=True)
        processes.append(subprocess.Popen([node, str(next_cli), "dev" if args.mode == "dev" else "start", "-H", "127.0.0.1", "-p", str(args.web_port)], cwd=ROOT / "frontend", env=env))
        ready(f"http://127.0.0.1:{args.web_port}", processes)
        print(f"AEGIS LOOP ready: http://127.0.0.1:{args.web_port} | API: http://127.0.0.1:{args.api_port}/docs", flush=True)
        if args.open:
            webbrowser.open(f"http://127.0.0.1:{args.web_port}")
        while all(process.poll() is None for process in processes):
            time.sleep(.5)
    except KeyboardInterrupt:
        pass
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()


if __name__ == "__main__":
    main()
