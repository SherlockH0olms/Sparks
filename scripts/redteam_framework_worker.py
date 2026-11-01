"""Isolated JSON bridge using real PyRIT converters and Garak buffs/resources."""
from __future__ import annotations

import asyncio
from contextlib import redirect_stdout
import hashlib
from importlib import metadata
import io
import json
import os
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
for kind in ("CONFIG", "CACHE", "DATA"):
    os.environ["XDG_" + kind + "_HOME"] = str(ROOT / ".runtime" / ("redtools-" + kind.lower()))

# These classes operate on local text. Target-dependent/image/audio converters
# are deliberately not advertised as executable text transforms.
CONVERTERS = [
    "ROT13Converter", "AtbashConverter", "BinaryConverter", "BinAsciiConverter",
    "MorseConverter", "NatoConverter", "LeetspeakConverter", "CharacterSpaceConverter",
    "JsonStringConverter", "UnicodeConfusableConverter", "ZeroWidthConverter",
    "BidiConverter", "UnicodeSubstitutionConverter", "SuperscriptConverter",
    "FlipConverter", "RandomCapitalLettersConverter", "InsertPunctuationConverter",
    "CaesarConverter", "DiacriticConverter", "ZalgoConverter", "BrailleConverter",
    "Base2048Converter", "EcojiConverter", "AsciiSmugglerConverter",
    "SneakyBitsSmugglerConverter", "VariationSelectorSmugglerConverter",
]
ENCODINGS = {"base64": "b64encode", "base64url": "urlsafe_b64encode",
             "base16": "b16encode", "base32": "b32encode",
             "ascii85": "a85encode", "base85": "b85encode"}


def transform(identifier, text):
    random.seed(hashlib.sha256((identifier + text).encode()).hexdigest())
    framework, name = identifier.split(":", 1)
    with redirect_stdout(io.StringIO()):
        if framework == "pyrit":
            import pyrit.converter as converters
            if name in ENCODINGS:
                converter = converters.Base64Converter(encoding_func=ENCODINGS[name])
            elif name == "CaesarConverter":
                converter = converters.CaesarConverter(caesar_offset=3)
            elif name in CONVERTERS:
                converter = getattr(converters, name)()
            else:
                raise ValueError("Unsupported converter")
            output = asyncio.run(converter.convert_async(prompt=text, input_type="text")).output_text
        elif framework == "garak" and name in {"Base64", "CharCode"}:
            from garak.attempt import Attempt, Message
            from garak.buffs import encoding
            output = next(getattr(encoding, name)().transform(Attempt(prompt=Message(text=text)))).prompt.last_message().text
        else:
            raise ValueError("Unsupported framework transformation")
    return {"outputs": [output], "framework": framework, "version": metadata.version(framework)}


def resources():
    import yaml
    rows = []
    seen = set()

    def add(framework, relative, location, text, title="", source="", description=""):
        if not isinstance(text, str) or not text.strip():
            return
        fingerprint = hashlib.sha256(text.encode()).hexdigest()
        # Do not inflate counts with duplicate copies in PyRIT and Garak.
        if fingerprint in seen:
            return
        seen.add(fingerprint)
        rows.append({"id": framework + ":" + hashlib.sha256((relative + location + text).encode()).hexdigest()[:20],
            "framework": framework, "version": metadata.version(framework),
            "license": "MIT" if framework == "pyrit" else "Apache-2.0",
            "path": relative, "location": location, "title": str(title) or Path(relative).stem,
            "text": text, "description": str(description or ""), "upstream_source": str(source or ""),
            "sha256": fingerprint})

    pyrit_root = Path(metadata.distribution("pyrit").locate_file("pyrit/datasets"))
    for path in sorted(pyrit_root.rglob("*")):
        relative = path.relative_to(pyrit_root).as_posix()
        if path.suffix not in {".yaml", ".prompt"}:
            continue
        # Import attacks and transformation prompts, not scoring rubrics or
        # unrelated harmful-content datasets.
        if not (relative.startswith(("jailbreak/", "converters/", "executors/")) or
                relative == "seed_datasets/local/psfuzz_steal_system.prompt" or
                relative.startswith("seed_datasets/local/garak/")):
            continue
        obj = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
        if isinstance(obj, dict):
            add("pyrit", relative, "value", obj.get("value"), obj.get("name", ""),
                obj.get("source", ""), obj.get("description", ""))
            for index, seed in enumerate(obj.get("seeds", [])):
                if isinstance(seed, dict):
                    add("pyrit", relative, f"seeds/{index}", seed.get("value"), obj.get("name", ""),
                        obj.get("source", ""), obj.get("description", ""))

    garak_root = Path(metadata.distribution("garak").locate_file("garak/data"))
    names = ["sysprompt_extraction/attacks.json", "inthewild_jailbreak_llms.json",
        "agent_breaker/prompts.yaml", "goat/attack_techniques.json", "autodan/autodan_prompts.json",
        "autodan/autodan_init.txt", "adaptive_attacks/seeds.txt", "adaptive_attacks/suffixes.txt",
        "tap/tap_jailbreaks.txt", "gcg/gcg.txt", "beast/suffixes.txt", "typology_payloads.tsv"]
    names += [p.relative_to(garak_root).as_posix() for p in sorted((garak_root / "dan").glob("*.json"))]

    def walk(obj, relative, location=""):
        if isinstance(obj, str):
            add("garak", relative, location, obj, location or Path(relative).stem)
        elif isinstance(obj, list):
            for index, child in enumerate(obj):
                walk(child, relative, location + "/" + str(index))
        elif isinstance(obj, dict):
            # JSON records' URL/name/category fields are metadata, not attacks.
            text_keys = [key for key in ("prompt", "text", "attack", "template", "content") if key in obj]
            if text_keys:
                for key in text_keys:
                    walk(obj[key], relative, location + "/" + key)
            else:
                for key, child in obj.items():
                    if isinstance(child, (list, dict)):
                        walk(child, relative, location + "/" + key)

    for relative in names:
        path = garak_root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8-sig")
        if path.suffix in {".yaml", ".json"}:
            walk(yaml.safe_load(text) if path.suffix == ".yaml" else json.loads(text), relative)
        else:
            for index, line in enumerate(text.splitlines()):
                add("garak", relative, str(index), line)
    return rows


def catalog():
    transforms, failures = [], []
    for identifier in (["pyrit:" + name for name in [*ENCODINGS, *CONVERTERS]] +
                       ["garak:Base64", "garak:CharCode"]):
        try:
            result = transform(identifier, "AEGIS local library integration test")
            if not result["outputs"] or not isinstance(result["outputs"][0], str):
                raise ValueError("No text result")
            framework, name = identifier.split(":", 1)
            transforms.append({"id": identifier, "framework": framework, "name": name,
                "version": result["version"], "license": "MIT" if framework == "pyrit" else "Apache-2.0",
                "implementation": "convert_async" if framework == "pyrit" else "Buff.transform", "local": True})
        except Exception as exc:
            failures.append({"id": identifier, "error": type(exc).__name__ + ": " + str(exc)})
    return {"resources": resources(), "transforms": transforms, "failures": failures}


if __name__ == "__main__":
    try:
        request = json.load(sys.stdin)
        if request["action"] == "catalog":
            result = catalog()
        elif request["action"] == "transform":
            result = transform(request["id"], request["text"])
        else:
            raise ValueError("Unknown action")
        print(json.dumps(result, ensure_ascii=True))
    except Exception as exc:
        print(type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        raise SystemExit(1)
