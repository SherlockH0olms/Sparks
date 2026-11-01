import bz2
import importlib.util
import json
from pathlib import Path

import pytest

from aegis_v2.red_corpus import AttackCorpus, add_resource, initialize_corpus
from aegis_v2.red_library import AttackLibrary, LibraryError
from test_red_tools import CANDIDATE, DIRECT, generate, generator, setup, tool_reply


@pytest.fixture
def corpus_library(tmp_path):
    path = tmp_path / "corpus.sqlite"
    db = initialize_corpus(path)
    rows = [
        {"id": "tensortrust:s1", "framework": "tensortrust", "text": "Seed original " + "x" * 7000, "title": "Seed one"},
        {"id": "tensortrust:s2", "framework": "tensortrust", "text": "Independent seed two", "title": "Seed two"},
        {"id": "bipia:s1", "framework": "bipia", "text": "External document instruction", "title": "Document seed"},
        {"id": "agentdojo:g1", "framework": "agentdojo", "text": "Tool result literal template", "title": "Agent template", "kind": "guidance"},
        {"id": "wildteaming:t1", "framework": "wildteaming", "text": "Roleplay a fictional task", "title": "Fictional roleplay", "kind": "tactic"},
        {"id": "wildteaming:t2", "framework": "wildteaming", "text": "Translation into another language", "title": "Translation", "kind": "tactic"},
        {"id": "wildteaming:t3", "framework": "wildteaming", "text": "JSON metadata carrier", "title": "JSON metadata", "kind": "tactic"},
        {"id": "wildteaming:compose", "framework": "wildteaming", "text": "Compose [INSERT SIMPLE PROMPT] with [INSERT STRATEGY LIST]", "title": "Composition", "kind": "guidance"},
    ]
    for row in rows:
        assert add_resource(db, row)
    assert not add_resource(db, rows[0] | {"id": "bipia:alias", "framework": "bipia", "path": "other.json"})
    summary = {"unique_resources": len(rows), "resource_kinds": {"seed": 3, "tactic": 3, "guidance": 2},
        "resources_per_framework": {"tensortrust": 2, "bipia": 1, "wildteaming": 4, "agentdojo": 1}, "sources": [],
        "source_kinds": {"tensortrust": {"seed": 2}, "bipia": {"seed": 1}, "wildteaming": {"tactic": 3, "guidance": 1}, "agentdojo": {"guidance": 1}}}
    db.execute("INSERT INTO metadata VALUES('summary',?)", (json.dumps(summary),))
    db.commit()
    db.close()
    return AttackLibrary({"resources": [], "transforms": [], "frameworks": [], "revision": "corpus-fixture",
                          "corpus": {"path": path.name}}, root=tmp_path)


def test_disk_corpus_search_paging_full_retrieval_aliases_and_readonly(corpus_library):
    corpus = corpus_library.corpus
    first = corpus.search(limit=2)
    assert first["total"] == 8 and first["next_offset"] == 2
    ids = [r["id"] for offset in range(0, 8, 2) for r in corpus.search(offset=offset, limit=2)["results"]]
    assert len(set(ids)) == 8 and corpus.search(offset=8)["next_offset"] is None
    assert "text" not in first["results"][0]
    alias = corpus.get("bipia:alias")
    assert len(alias["text"]) > 7000 and len(alias["provenance"]) == 2
    assert alias["id"] == "tensortrust:s1"
    assert corpus.search(framework="bipia", kind="seed")["total"] == 2
    assert corpus.search("translation", kind="tactic")["total"] == 1
    assert corpus.search('" OR 1=1; DROP TABLE resources --')["total"] == 0
    assert corpus.search(framework="bipia' OR 1=1 --")["total"] == 0
    assert corpus.get("../../.env") is None
    with corpus.connect() as db:
        with pytest.raises(Exception, match="readonly"):
            db.execute("DELETE FROM resources")


def test_seed_bundles_rotate_deterministically_and_compose_upstream_prompt(corpus_library):
    library = corpus_library
    bundle = library.bundle(seed_source="tensortrust", variation_key="case1", tactic_count=3)
    assert bundle == library.bundle(seed_source="tensortrust", variation_key="case1", tactic_count=3)
    assert len(set(bundle["tactic_ids"])) == 3 and len(bundle["seed_ids"]) == 2
    variations = [library.bundle(seed_source="tensortrust", variation_key=str(i), tactic_count=1)["tactic_ids"][0] for i in range(12)]
    assert len(set(variations)) > 1
    result = library.compose(bundle["tactic_ids"][:2], "Registered target-specific objective")
    assert "Registered target-specific objective" in result["composition_prompt"]
    assert "[INSERT" not in result["composition_prompt"]
    assert result["tactic_ids"] == bundle["tactic_ids"][:2]
    assert library.bundle(seed_source="agentdojo")["seed_ids"] == ["agentdojo:g1"]
    with pytest.raises(LibraryError): library.compose(["tensortrust:s1"], "objective")
    with pytest.raises(LibraryError): library.compose([{}], "objective")
    with pytest.raises(LibraryError): library.bundle(seed_source="wildteaming")
    with pytest.raises(LibraryError): library.bundle(seed_source="arbitrary")
    with pytest.raises(LibraryError): AttackLibrary().compose(["x"], "objective")
    methods = {m["id"]: m for m in library.list_methods()["methods"]}
    assert methods["wild_tactic_composition"]["resource_count"] == 3
    assert library.get_method("wild_tactic_composition", 2)["next_offset"] is None
    seen = [{"red_strategy": {"resources": [{"framework": "tensortrust"}]}}]
    assert library.recommend(DIRECT, seen, "case")["seed_source"] != "tensortrust"


def test_native_bundle_composition_records_actual_read_resources_and_replays(setup, corpus_library):
    calls = []
    def handler(request):
        payload = json.loads(request.content)
        calls.append(payload)
        if len(calls) == 1:
            enum = next(t for t in payload["tools"] if t["function"]["name"] == "search_attack_resources")["function"]["parameters"]["properties"]["framework"]["enum"]
            assert "tensortrust" in enum and "wildteaming" in enum
            return tool_reply("get_attack_bundle", {"seed_source": "tensortrust", "tactic_count": 2})
        result = json.loads(payload["messages"][-1]["content"])
        if len(calls) == 2:
            assert len(result["seed_ids"]) == 2
            assert any(len(r["text"]) > 7000 for r in result["resources"])
            return tool_reply("compose_attack_tactics", {"tactic_ids": result["tactic_ids"], "objective": "Target-specific task deviation"})
        assert "Target-specific task deviation" in result["composition_prompt"]
        return tool_reply("submit_attack", CANDIDATE)
    red, budget = generator(setup, handler)
    red.library = corpus_library
    candidate = generate(red, budget)
    strategy = candidate["red_strategy"]
    assert strategy["tool_names"] == ["get_attack_bundle", "compose_attack_tactics"]
    assert len(strategy["tactic_ids"]) == 2 and len(strategy["compositions"]) == 1
    assert {r["framework"] for r in strategy["resources"]} == {"tensortrust", "wildteaming"}
    assert generate(red, budget) == candidate and len(calls) == 3


def test_corpus_builder_handles_escaped_unicode_without_losing_scalar_pairs(tmp_path):
    db = initialize_corpus(tmp_path / "unicode.sqlite")
    assert add_resource(db, {"framework": "test", "text": "Pair \ud83d\ude00 and lone \ud800"})
    record = json.loads(db.execute("SELECT record FROM resources").fetchone()[0])
    assert record["text"] == "Pair \U0001f600 and lone \ufffd"
    db.close()


def test_importer_keeps_only_attacker_input_and_deduplicated_tactic_definitions(tmp_path):
    from collections import Counter
    script = Path(__file__).resolve().parents[2] / "scripts/expand_redteam_library.py"
    spec = importlib.util.spec_from_file_location("expand_redteam_library", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    attack = {"attack_id": 1, "attacker_input": "A valid crafted instruction", "access_code": "PRIVATE_CODE", "opening_defense": "PRIVATE_DEFENSE", "llm_output": "PRIVATE_OUTPUT", "is_self_attack": False}
    path = tmp_path / "attacks.bz2"
    with bz2.open(path, "wt", encoding="utf-8") as stream:
        for row in [attack, attack | {"is_self_attack": True}, attack | {"attacker_input": "PRIVATE_CODE"}, attack | {"attacker_input": "guess123"}]:
            stream.write(json.dumps(row) + "\n")
    counts = Counter()
    rows = list(module.rows_from_file("tensortrust", path, "attacks.bz2", counts))
    assert len(rows) == 1 and rows[0]["text"] == attack["attacker_input"]
    assert "PRIVATE" not in json.dumps(rows) and counts["raw_records"] == 4
    tactics = tmp_path / "tactics.json"
    tactics.write_text(json.dumps({"roleplay": {"definition": ["Use a persona", "Use a persona"], "excerpt": "EXCLUDED", "uid": ["id1"], "strategy_type": ["new", "new"]}}), encoding="utf-8")
    rows = list(module.rows_from_file("wildteaming", tactics, "auto_tactics.json", Counter()))
    assert rows[0]["text"] == "roleplay\nUse a persona" and rows[0]["strategy_type"] == ["new"]
    assert "EXCLUDED" not in json.dumps(rows)
