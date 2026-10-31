"""Prepare local access without printing or replacing provider credentials."""
from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
import re
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def prepare():
    path = ROOT / ".env"
    if not path.exists():
        path.write_text((ROOT / ".env.example").read_text(encoding="utf-8"), encoding="utf-8")
    text = path.read_text(encoding="utf-8-sig")
    match = re.search(r"^AEGIS_ADMIN_TOKEN=(.*)$", text, re.MULTILINE)
    if not match or not match.group(1).strip().strip("\"'"):
        line = "AEGIS_ADMIN_TOKEN=" + secrets.token_urlsafe(40)
        text = re.sub(r"^AEGIS_ADMIN_TOKEN=.*$", line, text, flags=re.MULTILINE) if match else text + "\n" + line + "\n"
        path.write_text(text, encoding="utf-8")
        print("Platform access key generated in .env: AEGIS_ADMIN_TOKEN (value is not logged).")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-providers", action="store_true")
    args = parser.parse_args()
    prepare()
    from aegis_v2.config import Settings
    from aegis_v2.providers import ChatClient, ProviderError
    settings = Settings.load()
    for name, cfg in (("Red", settings.red), ("Judge", settings.judge)):
        issues = cfg.issues()
        print(name + ": " + ("; ".join(issues) if issues else "settings complete"))
        if args.check_providers and not issues:
            try:
                answer = ChatClient(replace(cfg, max_output_tokens=256)).chat([{"role": "user", "content": "Reply with READY."}])
                print(name + ": " + ("live request succeeded" if answer.content.strip() else "request returned an empty response"))
            except ProviderError as exc:
                print(name + ": " + str(exc))
    print("Local model: " + ("configured" if settings.local_model else "AEGIS_LOCAL_MODEL is missing"))
    print("Login key: copy AEGIS_ADMIN_TOKEN from " + str(ROOT / ".env"))


if __name__ == "__main__":
    main()
