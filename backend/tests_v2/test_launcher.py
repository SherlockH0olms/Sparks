"""Port conflicts and launch orchestration; no application servers are started."""
import argparse
import io
import json
from pathlib import Path
import socket
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import ports
import run as launcher


@pytest.mark.parametrize("value", [-1, 65536, "not-a-port"])
def test_invalid_port_is_rejected(value):
    with pytest.raises(ValueError):
        ports.port_number(value)


def test_occupied_port_falls_back_and_preserves_the_other_socket():
    occupied = ports.reserve_port(0)
    selected = None
    try:
        selected = ports.reserve_port(occupied.port)
        assert selected.port != occupied.port
        assert occupied.socket.fileno() >= 0
        assert not ports.port_available(selected.port)
        with pytest.raises(OSError):
            ports.reserve_port(occupied.port, strict=True)
    finally:
        if selected:
            selected.close()
        occupied.close()


def test_wildcard_listener_is_treated_as_occupied():
    occupied = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    selected = None
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            occupied.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        occupied.bind(("0.0.0.0", 0))
        occupied.listen()
        requested = occupied.getsockname()[1]
        selected = ports.reserve_port(requested)
        assert selected.port != requested
    finally:
        if selected:
            selected.close()
        occupied.close()


def test_same_preference_gets_two_distinct_ports():
    api = ports.reserve_port(0)
    web = None
    try:
        web = ports.reserve_port(api.port)
        assert web.port != api.port
    finally:
        if web:
            web.close()
        api.close()


def test_exhausted_nearby_range_falls_back_to_os_port(monkeypatch):
    real_socket = socket.socket
    attempts = []

    class ExcludedPorts:
        def __init__(self, *args):
            self.real = real_socket(*args)

        def setsockopt(self, *args):
            self.real.setsockopt(*args)

        def bind(self, address):
            attempts.append(address[1])
            if address[1]:
                raise OSError("excluded or occupied")
            self.real.bind(address)

        def getsockname(self):
            return self.real.getsockname()

        def close(self):
            self.real.close()

    monkeypatch.setattr(ports.socket, "socket", ExcludedPorts)
    selected = ports.reserve_port(3002)
    try:
        assert selected.port > 0
        assert attempts == list(range(3002, 3103)) + [0]
    finally:
        selected.close()


class Child:
    def __init__(self, pid):
        self.pid = pid
        self.returncode = None

    def poll(self):
        return self.returncode

    def terminate(self):
        self.returncode = -15

    def wait(self, timeout):
        return self.returncode


def args(api_port=0, web_port=0, strict=False):
    return argparse.Namespace(mode="dev", dist_dir=".next-dev", api_port=api_port,
                              web_port=web_port, strict_ports=strict)


def test_both_conflicts_update_proxy_origin_and_saved_urls(tmp_path, monkeypatch):
    api, web = ports.reserve_port(0), ports.reserve_port(0)
    calls, checks = [], []

    def spawn(command, **kwargs):
        child = Child(100 + len(calls))
        calls.append((command, dict(kwargs["env"]), child))
        return child

    monkeypatch.setattr(launcher.subprocess, "Popen", spawn)
    monkeypatch.setattr(launcher, "ready", lambda url, processes, **kw: checks.append((url, kw)))
    state_file = tmp_path / "state.json"
    try:
        request = args(api.port, web.port)
        request.launch_id = "parent-launch-with-python-redirector"
        children, state = launcher.launch(request, "node", Path("next"), state_file)
        assert state["api_port"] != api.port and state["web_port"] != web.port
        assert state["api_port"] != state["web_port"]
        assert state["launch_id"] == request.launch_id
        assert json.loads(state_file.read_text())["status"] == "ready"
        assert state["api_url"] == f"http://127.0.0.1:{state['api_port']}"
        assert state["platform_url"] == f"http://127.0.0.1:{state['web_port']}/"
        for _, env, _ in calls:
            assert env["AEGIS_API"] == state["api_url"]
            assert state["platform_url"].rstrip("/") in env["AEGIS_ALLOWED_ORIGINS"]
            assert env["AEGIS_INSTANCE_ID"] == state["instance_id"]
        assert checks[-1][0] == state["platform_url"].rstrip("/") + "/api/health"
        assert checks[-1][1]["instance_id"] == state["instance_id"]
        assert api.socket.fileno() >= 0 and web.socket.fileno() >= 0
        launcher.stop_children(children)
    finally:
        api.close()
        web.close()


def test_startup_race_retries_without_stopping_the_new_port_owner(tmp_path, monkeypatch):
    calls, foreign = [], []
    preferred_api, preferred_web = ports.reserve_port(0), ports.reserve_port(0)
    requested = args(preferred_api.port, preferred_web.port)
    preferred_api.close()
    preferred_web.close()

    def spawn(command, **kwargs):
        child = Child(200 + len(calls))
        calls.append(child)
        if "-p" in command and not foreign:
            reservation = ports.reserve_port(int(command[-1]), strict=True)
            reservation.socket.listen()
            foreign.append(reservation)
            child.returncode = 1
        return child

    def check(url, processes, **kwargs):
        if any(child.poll() is not None for child in processes):
            raise launcher.ServerExited("port occupied after reservation was released")

    monkeypatch.setattr(launcher.subprocess, "Popen", spawn)
    monkeypatch.setattr(launcher, "ready", check)
    try:
        children, state = launcher.launch(requested, "node", Path("next"), tmp_path / "state.json")
        assert len(calls) == 4
        assert calls[0].poll() is not None
        assert state["web_port"] != foreign[0].port
        assert foreign[0].socket.fileno() >= 0
        launcher.stop_children(children)
    finally:
        for reservation in foreign:
            reservation.close()


def test_non_port_failure_does_not_retry_or_leave_children(tmp_path, monkeypatch):
    children = []

    def spawn(*args, **kwargs):
        child = Child(300)
        children.append(child)
        return child

    def fail(*args, **kwargs):
        raise RuntimeError("API configuration failure")

    monkeypatch.setattr(launcher.subprocess, "Popen", spawn)
    monkeypatch.setattr(launcher, "ready", fail)
    with pytest.raises(RuntimeError, match="configuration"):
        launcher.launch(args(), "node", Path("next"), tmp_path / "state.json")
    assert len(children) == 1 and children[0].poll() is not None
    assert json.loads((tmp_path / "state.json").read_text())["status"] == "failed"


def test_wrong_backend_health_cannot_pass_readiness(monkeypatch):
    class Response(io.BytesIO):
        status = 200

    monkeypatch.setattr(launcher.HTTP, "open", lambda *a, **kw: Response(b'{"status":"ok","instance_id":"other"}'))
    with pytest.raises(launcher.ServerExited, match="another server"):
        launcher.ready("http://127.0.0.1:1234/api/health", [Child(400)], instance_id="expected")


def test_plan_selects_both_ports_without_starting_or_writing(tmp_path, monkeypatch, capsys):
    api, web = ports.reserve_port(0), ports.reserve_port(0)
    monkeypatch.setattr(sys, "argv", ["run.py", "--plan", "--api-port", str(api.port), "--web-port", str(web.port),
                                     "--state-file", str(tmp_path / "state.json")])
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda *a, **kw: pytest.fail("plan must not start servers"))
    try:
        launcher.main()
        state = json.loads(capsys.readouterr().out)
        assert state["api_port"] != api.port and state["web_port"] != web.port
        assert not (tmp_path / "state.json").exists()
    finally:
        api.close()
        web.close()
