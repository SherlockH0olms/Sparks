"""Cross-platform API/web launcher with automatic ports and readiness checks."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
import webbrowser

from ports import HOST, port_available, port_number, reserve_port

ROOT = Path(__file__).resolve().parents[1]
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class ServerExited(RuntimeError):
    pass


def ready(url, processes, *, instance_id=None):
    for _ in range(90):
        if any(process.poll() is not None for process in processes):
            raise ServerExited("A server exited; inspect its output above.")
        try:
            with HTTP.open(url, timeout=1) as response:
                if response.status == 200:
                    if instance_id is None:
                        return
                    health = json.load(response)
                    if health.get("instance_id") == instance_id and health.get("status") == "ok":
                        return
                    raise ServerExited("The selected port was taken by another server during startup.")
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(.5)
    raise RuntimeError("Server did not become ready: " + url)


def atomic_state(path: Path, state: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        json.dump(state, output, indent=2)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_state(path: Path, state: dict):
    if state.get("managed_workspace") and state.get("launch_id"):
        atomic_state(path.parent / "live-instances" / (state["launch_id"] + ".json"), state)
    # An older supervisor must never overwrite a newer launch's published state.
    if state.get("status") in {"stopped", "failed"} and path.exists():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            current = {}
        if current.get("launch_id") and current["launch_id"] != state.get("launch_id"):
            return
    atomic_state(path, state)


def stop_children(processes):
    # These handles were created by this invocation. Never stop a port's owner.
    for process in reversed(processes):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def launch(args, node, next_cli, state_file):
    launch_id = getattr(args, "launch_id", None) or uuid.uuid4().hex
    dist_dir = args.dist_dir or {"production": ".next-live", "demo": ".next-demo", "dev": ".next-dev"}[args.mode]
    if Path(dist_dir).is_absolute() or ".." in Path(dist_dir).parts or dist_dir in {".", ""}:
        raise ValueError("Use a build directory inside frontend.")
    env = os.environ.copy()
    env["AEGIS_NEXT_DIST_DIR"] = dist_dir
    if env.get("AEGIS_MANAGED_WORKSPACE", "false").lower() == "true":
        env["AEGIS_WORKSPACE_RELEASE"] = dist_dir
    if args.mode != "dev" and not (ROOT / "frontend" / dist_dir / "BUILD_ID").exists():
        subprocess.run([node, str(next_cli), "build"], cwd=ROOT / "frontend", env=env, check=True)
    for attempt in range(5):
        processes = []
        api_reservation = reserve_port(args.api_port, strict=args.strict_ports)
        try:
            web_reservation = reserve_port(args.web_port, strict=args.strict_ports)
        except BaseException:
            api_reservation.close()
            raise
        api_port, web_port = api_reservation.port, web_reservation.port
        instance_id = uuid.uuid4().hex
        api_url, web_url = f"http://{HOST}:{api_port}", f"http://{HOST}:{web_port}"
        env["AEGIS_API"] = api_url
        env["AEGIS_INSTANCE_ID"] = instance_id
        env["AEGIS_ALLOWED_ORIGINS"] = f"http://localhost:{web_port},{web_url}"
        if args.mode == "demo":
            env["AEGIS_DEMO_RUNTIME_DIR"] = str(ROOT / ".runtime" / f"demo-{api_port}-{web_port}")
        state = {
            "status": "starting", "source": str(ROOT), "mode": args.mode,
            "release": dist_dir, "instance_id": instance_id, "launch_id": launch_id,
            "managed_workspace": env.get("AEGIS_MANAGED_WORKSPACE", "false").lower() == "true",
            "api_port": api_port, "web_port": web_port,
            "api_url": api_url, "platform_url": web_url + "/",
            "launcher_pid": os.getpid(),
            "runtime_dir": env.get("AEGIS_RUNTIME_DIR", str(ROOT / ".runtime")),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        write_state(state_file, state)
        if (api_port, web_port) != (args.api_port, args.web_port):
            print(f"Available ports selected: web {web_port}, API {api_port}. Other applications were left running.", flush=True)
        backend_app = "aegis_v2.demo:create_demo_app" if args.mode == "demo" else "aegis_v2.api:app"
        backend = [sys.executable, "-m", "uvicorn", backend_app, "--app-dir", str(ROOT / "backend"), "--host", HOST, "--port", str(api_port)]
        if args.mode == "demo":
            backend.append("--factory")
        try:
            # Release each reservation immediately before binding its real server.
            api_reservation.close()
            processes.append(subprocess.Popen(backend, cwd=ROOT / "backend", env=env))
            state["backend_pid"] = processes[0].pid
            write_state(state_file, state)
            ready(api_url + "/api/health", processes, instance_id=instance_id)
            web_reservation.close()
            processes.append(subprocess.Popen([node, str(next_cli), "dev" if args.mode == "dev" else "start", "-H", HOST, "-p", str(web_port)], cwd=ROOT / "frontend", env=env))
            state["frontend_pid"] = processes[1].pid
            write_state(state_file, state)
            ready(web_url, processes)
            # Verify the frontend proxy reaches THIS backend, not a stale address.
            ready(web_url + "/api/health", processes, instance_id=instance_id)
            state["status"] = "ready"
            write_state(state_file, state)
            return processes, state
        except ServerExited:
            api_reservation.close()
            web_reservation.close()
            stop_children(processes)
            if args.strict_ports or attempt == 4 or (port_available(api_port) and port_available(web_port)):
                state["status"] = "failed"
                write_state(state_file, state)
                raise
            print("A selected port became occupied during startup; selecting another pair.", flush=True)
        except BaseException:
            api_reservation.close()
            web_reservation.close()
            stop_children(processes)
            state["status"] = "failed"
            write_state(state_file, state)
            raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("production", "dev", "demo"), default="production")
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--api-port", type=port_number, default=port_number(os.getenv("AEGIS_API_PORT", "8000")), help="Preferred API port; automatically falls back if occupied. 0 lets the OS choose.")
    parser.add_argument("--web-port", type=port_number, default=port_number(os.getenv("AEGIS_WEB_PORT", "3000")), help="Preferred web port; automatically falls back if occupied. 0 lets the OS choose.")
    parser.add_argument("--strict-ports", action="store_true", help="Require the requested ports, for deployments/tests with fixed mappings.")
    parser.add_argument("--plan", action="store_true", help="Print an available port pair without starting servers or changing files.")
    parser.add_argument("--state-file", type=Path, help="JSON file containing the actual URLs, process IDs, and startup status.")
    parser.add_argument("--launch-id", help="Parent-provided launch identity, independent of Windows Python redirector process IDs.")
    parser.add_argument("--dist-dir", help="Separate Next.js build directory; defaults to .next-live, .next-demo, or .next-dev.")
    args = parser.parse_args()
    if args.plan:
        api_reservation = reserve_port(args.api_port, strict=args.strict_ports)
        try:
            web_reservation = reserve_port(args.web_port, strict=args.strict_ports)
            try:
                print(json.dumps({"api_port": api_reservation.port, "web_port": web_reservation.port,
                                  "api_url": f"http://{HOST}:{api_reservation.port}",
                                  "platform_url": f"http://{HOST}:{web_reservation.port}/"}))
            finally:
                web_reservation.close()
        finally:
            api_reservation.close()
        return
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Install Node.js first.")
    next_cli = ROOT / "frontend" / "node_modules" / "next" / "dist" / "bin" / "next"
    if not next_cli.exists():
        raise RuntimeError("Run npm install in frontend first.")
    from setup import prepare
    prepare()
    if args.mode == "demo":
        print("OFFLINE FIXTURE DEMO. Login: aegis-offline-demo-access-key-2026-only", flush=True)
    state_file = args.state_file or ROOT / ".runtime" / f"launcher-{args.mode}.json"
    processes, state = [], None
    try:
        processes, state = launch(args, node, next_cli, state_file)
        print(f"AEGIS LOOP ready: {state['platform_url']} | API: {state['api_url']}/docs", flush=True)
        print(f"Connection details: {state_file}", flush=True)
        if args.open:
            webbrowser.open(state["platform_url"])
        while all(process.poll() is None for process in processes):
            time.sleep(.5)
        raise ServerExited("A running server exited; both services have been stopped.")
    except KeyboardInterrupt:
        pass
    finally:
        stop_children(processes)
        if state:
            state["status"] = "stopped"
            write_state(state_file, state)


if __name__ == "__main__":
    main()
