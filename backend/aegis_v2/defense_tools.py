from __future__ import annotations

import json
import os
import subprocess
import atexit
import queue
import threading
from functools import lru_cache
from .config import ROOT


@lru_cache(maxsize=1)
def tool_catalog():
    path = ROOT / ".runtime/defense-tools.json"
    if not path.is_file():
        return {"tools": [], "available": False}
    return json.loads(path.read_text(encoding="utf-8"))


def available(tool):
    if tool in {None, "jsonschema"}:
        return True
    return any(item["id"] == tool and item["verified"] for item in tool_catalog().get("tools", []))


class Worker:
    def __init__(self):
        self.lock = threading.Lock()
        self.process = None
        self.responses = queue.Queue()

    def close(self):
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

    def start(self):
        python = ROOT / ".venv-defensetools" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        env = dict(os.environ, OTEL_SDK_DISABLED="true", GUARDRAILS_DISABLE_TELEMETRY="true",
                   LANGCHAIN_TRACING_V2="false", LANGSMITH_TRACING="false", PYTHONIOENCODING="utf-8")
        self.responses = queue.Queue()
        self.process = subprocess.Popen([str(python), "-u", str(ROOT / "scripts/defense_tool_worker.py"), "--serve"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            encoding="utf-8", cwd=ROOT, env=env, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        process, responses = self.process, self.responses
        def read():
            for line in process.stdout:
                responses.put(line)
            responses.put(None)
        threading.Thread(target=read, daemon=True).start()

    def call(self, payload):
        with self.lock:
            if self.process is None or self.process.poll() is not None:
                self.start()
            try:
                self.process.stdin.write(json.dumps(payload) + "\n")
                self.process.stdin.flush()
                response = self.responses.get(timeout=90)
                value = json.loads(response) if response else None
                if not value or "error" in value:
                    raise RuntimeError("Local defense validator failed.")
                return value
            except (queue.Empty, OSError, ValueError, RuntimeError) as exc:
                self.close()
                from .providers import ProviderError
                raise ProviderError("Local defense validator did not complete: " + type(exc).__name__) from None


_workers = {tool: Worker() for tool in ("guardrails_ai", "presidio")}
atexit.register(lambda: [worker.close() for worker in _workers.values()])


def run_tool(tool, request):
    if not available(tool):
        raise ValueError("Install the required defense component: " + tool)
    if tool not in _workers:
        raise ValueError("Unknown local defense tool")
    return _workers[tool].call({"tool": tool, **request})
