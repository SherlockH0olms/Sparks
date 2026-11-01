"""Import fingerprinted public research resources into an indexed, deduplicated corpus.

Only attacker inputs and tactic definitions are exposed. Benchmark passwords,
defenses, model responses, private identities and carrier documents are excluded.
"""
from __future__ import annotations

import argparse
import ast
import bz2
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from aegis_v2.red_corpus import initialize_corpus, add_resource


SOURCES = [
    ("tensortrust", "HumanCompatibleAI/tensor-trust-data", "v2", "not-specified", "dataset", ["raw-data/v2/raw_dump_attacks.jsonl.bz2"]),
    ("wildteaming", "allenai/wildteaming", "snapshot", "not-specified", "tactics_and_composition", ["data/tactics/auto_tactics.json", "data/prompts/compose_tactics.txt"]),
    ("bipia", "microsoft/BIPIA", "snapshot", "MIT (attack templates)", "indirect_injection", ["benchmark/text_attack_train.json", "benchmark/text_attack_test.json", "benchmark/code_attack_train.json", "benchmark/code_attack_test.json"]),
    ("injecagent", "uiuc-kang-lab/InjecAgent", "snapshot", "MIT", "agent_injection", ["data/attacker_cases_ds.jsonl", "data/attacker_cases_dh.jsonl"]),
    ("harmbench", "centerforaisafety/HarmBench", "snapshot", "MIT", "mutation_templates", ["baselines/gptfuzz/GPTFuzzer.csv", "baselines/human_jailbreaks/jailbreaks.py"]),
    ("agentdojo", "ethz-spylab/agentdojo", "snapshot", "MIT", "agent_injection", ["src/agentdojo/attacks/important_instructions_attacks.py", "src/agentdojo/attacks/baseline_attacks.py"]),
]


def cached_file(source, repo, relative, *, offline=False):
    folder = ROOT / ".runtime/red-sources" / source
    folder.mkdir(parents=True, exist_ok=True)
    filename = folder / (relative.replace("/", "__"))
    url = "https://raw.githubusercontent.com/" + repo + "/main/" + relative
    if not filename.is_file():
        if source == "tensortrust" and (ROOT / ".runtime/red-sources/tensortrust-v2.jsonl.bz2").is_file():
            filename = ROOT / ".runtime/red-sources/tensortrust-v2.jsonl.bz2"
        elif source == "wildteaming" and relative.endswith("auto_tactics.json") and (ROOT / ".runtime/red-research/wild-tactics.txt").is_file():
            filename = ROOT / ".runtime/red-research/wild-tactics.txt"
        else:
            if offline:
                raise FileNotFoundError("Not cached: " + relative)
            temporary = filename.with_suffix(filename.suffix + ".download")
            request = urllib.request.Request(url, headers={"User-Agent": "AEGIS-Research-Corpus/1.0"})
            with urllib.request.urlopen(request, timeout=90) as response, temporary.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            temporary.replace(filename)
    hasher = hashlib.sha256()
    with filename.open("rb") as content:
        while chunk := content.read(1024 * 1024):
            hasher.update(chunk)
    return filename, url, hasher.hexdigest()


def rows_from_file(source, path, relative, counts):
    if source == "tensortrust":
        with bz2.open(path, "rt", encoding="utf-8") as stream:
            for line in stream:
                obj = json.loads(line)
                counts["raw_records"] += 1
                text = obj.get("attacker_input", "")
                if obj.get("is_self_attack"):
                    counts["excluded_self_attacks"] += 1
                    continue
                if not isinstance(text, str) or not text.strip() or text.strip() == str(obj.get("access_code", "")):
                    counts["excluded_empty_or_correct_password"] += 1
                    continue
                if re.fullmatch(r"[A-Za-z0-9_\-]{1,32}", text.strip()):
                    counts["excluded_single_code_guesses"] += 1
                    continue
                yield {"text": text, "title": "TensorTrust attacker input " + str(obj["attack_id"]),
                    "location": str(obj["attack_id"]), "kind": "seed",
                    "description": "Public prompt-injection game attacker input. Adapt the mechanism to this target; game-specific passwords, magic responses and names are not target facts."}
    elif source == "wildteaming" and relative.endswith(".json"):
        obj = json.loads(path.read_text(encoding="utf-8"))
        for title, record in obj.items():
            counts["raw_records"] += 1
            definition = record.get("definition", "")
            if isinstance(definition, list):
                definition = "\n".join(dict.fromkeys(s for s in definition if isinstance(s, str)))
            if isinstance(definition, str) and definition.strip():
                strategy_type = record.get("strategy_type")
                if isinstance(strategy_type, list):
                    strategy_type = list(dict.fromkeys(s for s in strategy_type if isinstance(s, str)))
                yield {"text": title + "\n" + definition, "title": title, "location": title,
                    "kind": "tactic", "description": "WildTeaming mined tactic definition; excerpt and original harmful objective were not imported.",
                    "strategy_type": strategy_type}
    elif source == "injecagent":
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
            obj = json.loads(line)
            counts["raw_records"] += 1
            yield {"text": obj.get("Attacker Instruction", ""), "title": "InjecAgent " + obj.get("Attack Type", "attack"),
                   "location": str(index), "kind": "seed",
                   "description": "Agent/tool-result injection seed. Original tool names and destinations must be adapted to the authorized target."}
    elif path.suffix == ".json":
        def visit(obj, location=""):
            if isinstance(obj, str):
                counts["raw_records"] += 1
                yield {"text": obj, "title": location or relative, "location": location, "kind": "seed"}
            elif isinstance(obj, list):
                for index, child in enumerate(obj):
                    yield from visit(child, location + "/" + str(index))
            elif isinstance(obj, dict):
                for name, child in obj.items():
                    yield from visit(child, location + "/" + name)
        yield from visit(json.loads(path.read_text(encoding="utf-8")))
    elif path.suffix == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as stream:
            for index, record in enumerate(csv.DictReader(stream)):
                for name, text in record.items():
                    if text and len(text) >= 80 and name.lower() not in {"id", "model", "source"}:
                        counts["raw_records"] += 1
                        yield {"text": text, "title": "GPTFuzzer mutation seed", "location": str(index) + "/" + name, "kind": "seed"}
    elif path.suffix == ".py":
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) >= 120:
                counts["raw_records"] += 1
                yield {"text": node.value, "title": source + " upstream template fragment", "location": str(node.lineno),
                       "kind": "guidance", "description": "Literal upstream attack-template fragment, extracted without executing repository code."}
    else:
        counts["raw_records"] += 1
        yield {"text": path.read_text(encoding="utf-8"), "title": "WildTeaming composition instructions",
               "location": "0", "kind": "guidance"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    catalog_path = ROOT / ".runtime/redteam-library.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    destination = ROOT / ".runtime/redteam-corpus.sqlite"
    temporary = destination.with_name("redteam-corpus-building.sqlite")
    # Only replace this explicitly named build artifact, not existing live data.
    if temporary.exists():
        temporary.unlink()
    db = initialize_corpus(temporary)
    for record in catalog["resources"]:
        add_resource(db, record)
    reports = []
    started = time.monotonic()
    for source, repo, version, license_name, mode, paths in SOURCES:
        counts = Counter()
        files = []
        for relative in paths:
            path, url, sha = cached_file(source, repo, relative, offline=args.offline)
            files.append({"path": relative, "url": url, "sha256": sha, "bytes": path.stat().st_size})
            for row in rows_from_file(source, path, relative, counts):
                row.update(framework=source, version=version, license=license_name, path=relative,
                           upstream_source=url, source_sha256=sha)
                counts["usable_records"] += 1
                counts["new_unique_resources"] += int(add_resource(db, row))
                if counts["usable_records"] % 10000 == 0:
                    db.commit()
        db.commit()
        report = {"id": source, "url": "https://github.com/" + repo, "version": version, "license": license_name,
                  "mode": mode, "files": files, "counts": dict(counts), "available": True}
        reports.append(report)
        print(json.dumps({"source": source, "counts": dict(counts)}, ensure_ascii=True), flush=True)
    total = db.execute("SELECT count(*) FROM resources").fetchone()[0]
    by_source = dict(db.execute("SELECT framework,count(*) FROM resources GROUP BY framework").fetchall())
    by_kind = dict(db.execute("SELECT kind,count(*) FROM resources GROUP BY kind").fetchall())
    source_kinds = {}
    for source, kind, count in db.execute("SELECT framework,kind,count(*) FROM resources GROUP BY framework,kind"):
        source_kinds.setdefault(source, {})[kind] = count
    summary = {"unique_resources": total, "resources_per_framework": by_source, "resource_kinds": by_kind,
               "source_kinds": source_kinds, "sources": reports, "search_backend": "SQLite FTS5", "schema_version": 2}
    summary["revision"] = hashlib.sha256(json.dumps(summary, sort_keys=True).encode()).hexdigest()
    db.execute("INSERT INTO metadata VALUES('summary',?)", (json.dumps(summary),))
    db.execute("INSERT INTO search(search) VALUES('optimize')")
    db.commit()
    db.close()
    temporary.replace(destination)
    catalog["corpus"] = {"path": str(destination.relative_to(ROOT)), "revision": summary["revision"]}
    catalog["research_sources"] = reports
    catalog.pop("revision", None)
    catalog["revision"] = hashlib.sha256(json.dumps(catalog, sort_keys=True).encode()).hexdigest()
    replacement = catalog_path.with_suffix(".json.tmp")
    replacement.write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")
    replacement.replace(catalog_path)
    print(json.dumps({"complete": True, "unique_resources": total, "resource_kinds": by_kind,
                      "seconds": round(time.monotonic()-started, 2), "corpus": str(destination)}, indent=2))


if __name__ == "__main__":
    main()
