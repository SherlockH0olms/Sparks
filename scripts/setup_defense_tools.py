from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="Install and verify isolated local defense validators.")
    parser.add_argument("--index-only", action="store_true")
    parser.add_argument("--python", help="Python 3.12 executable for creating the isolated environment")
    args = parser.parse_args()
    python = ROOT / ".venv-defensetools" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        runtimes = sorted((ROOT / ".runtime/python-runtimes").glob("cpython-3.12*/python.exe" if os.name == "nt" else "cpython-3.12*/bin/python3.12"))
        interpreter = args.python or (str(runtimes[-1]) if runtimes else sys.executable)
        probe = subprocess.run([interpreter, "-c", "import sys; print(str(sys.version_info.major)+'.'+str(sys.version_info.minor))"], capture_output=True, text=True, check=True)
        if probe.stdout.strip() != "3.12":
            parser.error("The isolated defense tools require Python 3.12. Supply --python with its executable path.")
        subprocess.run([interpreter, "-m", "venv", str(python.parent.parent if os.name == "nt" else python.parent.parent)], check=True)
    if not args.index_only:
        subprocess.run([str(python), "-m", "pip", "install", "guardrails-ai==0.11.0", "presidio-analyzer==2.2.366"], check=True)
    env = dict(os.environ, OTEL_SDK_DISABLED="true", GUARDRAILS_DISABLE_TELEMETRY="true")
    probes = [
        {"tool": "guardrails_ai", "payload": {"ok": True}, "schema": {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"], "additionalProperties": False}},
        {"tool": "presidio", "text": "Contact demo.person@example.com or +1 202 555 0100"},
    ]
    entries = []
    for probe in probes:
        result = subprocess.run([str(python), str(ROOT / "scripts/defense_tool_worker.py")],
            input=json.dumps(probe), encoding="utf-8", capture_output=True, env=env, check=True)
        value = json.loads(result.stdout)
        verified = value.get("valid") is True if probe["tool"] == "guardrails_ai" else len(value["matches"]) >= 2
        if not verified:
            raise RuntimeError("A local defense tool did not pass its smoke test.")
        entries.append({"id": value["tool"], "version": value["version"], "verified": verified,
                        "mode": "local_schema_validator" if value["tool"] == "guardrails_ai" else "local_pattern_recognizers"})
    path = ROOT / ".runtime/defense-tools.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"available": True, "tools": entries}, indent=2), encoding="utf-8")
    print(json.dumps({"available": True, "tools": entries}))


if __name__ == "__main__":
    main()
