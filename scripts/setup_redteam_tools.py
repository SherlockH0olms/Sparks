"""Install isolated red-team components and index their real local resources."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


def json_worker(command, request):
    result = subprocess.run(command, input=json.dumps(request), encoding="utf-8",
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=ROOT, check=True)
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-only", action="store_true", help="Use the already installed packages")
    parser.add_argument("--with-deepteam", action="store_true", help="Install DeepTeam into a separate Python 3.12 environment")
    args = parser.parse_args()
    environment = ROOT / ".venv-redtools"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    node = shutil.which("node")
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not node or not npm:
        raise SystemExit("Install Node.js >=22.22 and npm first.")
    if not args.index_only:
        if not python.exists():
            venv.EnvBuilder(with_pip=True).create(environment)
        subprocess.run([str(python), "-m", "pip", "install", "pyrit==1.1.0", "xdg-base-dirs==6.0.3"], check=True)
        # Garak is used for datasets and local buffs only. Its full scanner's
        # torch/provider dependencies are not required by this bridge.
        subprocess.run([str(python), "-m", "pip", "install", "--no-deps", "garak==0.17.1"], check=True)
        subprocess.run([npm, "install", "--prefix", str(ROOT / ".runtime/redtools-node"),
            "--ignore-scripts", "--omit=optional", "--no-audit", "--no-fund", "promptfoo@0.125.1"], check=True)
    imported = json_worker([str(python), str(ROOT / "scripts/redteam_framework_worker.py")], {"action": "catalog"})
    promptfoo = json_worker([node, str(ROOT / "scripts/redteam_promptfoo_worker.cjs")], {"action": "catalog"})
    imported["transforms"] += promptfoo["transforms"]
    imported["failures"] += promptfoo["failures"]
    imported["schema_version"] = 1
    imported["frameworks"] = [
        {"id": "pyrit", "version": "1.1.0", "url": "https://github.com/microsoft/PyRIT", "license": "MIT", "mode": "resources_and_local_converters"},
        {"id": "garak", "version": "0.17.1", "url": "https://github.com/NVIDIA/garak", "license": "Apache-2.0", "mode": "resources_and_local_buffs"},
        {"id": "promptfoo", "version": "0.125.1", "url": "https://github.com/promptfoo/promptfoo", "license": "MIT", "mode": "public_local_strategy_api"},
    ]
    deep_environment = ROOT / ".venv-redtools-deep"
    deep_python = deep_environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if args.with_deepteam and not args.index_only:
        subprocess.run([str(python), "-m", "pip", "install", "uv==0.13.6"], check=True)
        uv = environment / ("Scripts/uv.exe" if os.name == "nt" else "bin/uv")
        runtimes = ROOT / ".runtime/python-runtimes"
        cache = ROOT / ".runtime/uv-cache"
        subprocess.run([str(uv), "python", "install", "3.12", "--install-dir", str(runtimes),
                        "--no-bin", "--no-registry", "--cache-dir", str(cache)], check=True)
        candidates = list(runtimes.glob("cpython-3.12*/python.exe" if os.name == "nt" else "cpython-3.12*/bin/python3.12"))
        if not candidates:
            raise SystemExit("Private Python 3.12 runtime is missing")
        if not deep_python.exists():
            subprocess.run([str(uv), "venv", str(deep_environment), "--python", str(sorted(candidates)[-1]),
                            "--seed", "--cache-dir", str(cache)], check=True)
        subprocess.run([str(deep_python), "-m", "pip", "install", "deepteam==1.0.10", "deepeval==4.3.2", "sentry-sdk==2.42.1"], check=True)
    if deep_python.exists():
        deep = json_worker([str(deep_python), str(ROOT / "scripts/redteam_deepteam_worker.py")], {"action": "catalog"})
        imported["transforms"] += deep["transforms"]
        imported["failures"] += deep["failures"]
        imported["frameworks"].append({"id": "deepteam", "version": "1.0.10", "url": "https://github.com/confident-ai/deepteam",
            "license": "Apache-2.0", "mode": "local_single_turn_attacks"})
    output = ROOT / ".runtime/redteam-library.json"
    if output.is_file():
        previous = json.loads(output.read_text(encoding="utf-8"))
        for key in ("corpus", "research_sources"):
            if key in previous:
                imported[key] = previous[key]
    imported["revision"] = hashlib.sha256(json.dumps(imported, sort_keys=True, ensure_ascii=True).encode()).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(imported, ensure_ascii=False), encoding="utf-8")
    temporary.replace(output)
    print(json.dumps({"catalog": str(output), "revision": imported["revision"],
        "unique_resources": len(imported["resources"]), "executable_transforms": len(imported["transforms"]),
        "failures": imported["failures"]}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
