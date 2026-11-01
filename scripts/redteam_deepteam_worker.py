"""JSON bridge to four tested DeepTeam local attacks; no provider is created."""
from __future__ import annotations

import contextlib
import importlib.metadata
import io
import json
import os
import sys

os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "YES"
os.environ["DEEPTEAM_TELEMETRY_OPT_OUT"] = "YES"
os.environ["DEEPEVAL_UPDATE_WARNING_OPT_OUT"] = "YES"


def main(request):
    with contextlib.redirect_stdout(io.StringIO()):
        from deepteam.attacks.single_turn import Base64, ROT13, Leetspeak, CharacterStream
    classes = {"deepteam:" + cls.__name__: cls for cls in (Base64, ROT13, Leetspeak, CharacterStream)}
    version = importlib.metadata.version("deepteam")
    if request["action"] == "catalog":
        transforms, failures = [], []
        for identifier, cls in classes.items():
            try:
                output = cls().enhance("AEGIS integration test")
                if not isinstance(output, str) or output == "AEGIS integration test":
                    raise ValueError("No local transformation")
                transforms.append({"id": identifier, "framework": "deepteam", "version": version,
                    "license": "Apache-2.0", "description": cls.description,
                    "api": "deepteam.attacks.single_turn." + cls.__name__ + ".enhance", "local": True})
            except Exception as exc:
                failures.append({"id": identifier, "error": type(exc).__name__})
        return {"transforms": transforms, "failures": failures}
    if request["action"] != "transform" or request["id"] not in classes:
        raise ValueError("Unregistered DeepTeam component")
    return {"outputs": [classes[request["id"]]().enhance(request["text"])]}


if __name__ == "__main__":
    request = json.loads(sys.stdin.read())
    result = main(request)
    sys.stdout.write(json.dumps(result, ensure_ascii=True))
