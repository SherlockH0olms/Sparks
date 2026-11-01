import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from aegis_v2.api import create_app
from aegis_v2.contracts import CampaignCreate, TargetCreate
from aegis_v2.naming import campaign_names, target_names
from aegis_v2.scenarios import target_template
from tests_v2.test_discovery import platform


def spec(name="Granite", revision=""):
    return target_template("http://localhost/v1", "local") | {"name": name, "model_revision": revision}


def test_duplicate_names_are_chronological_and_do_not_change_snapshots(platform):
    p, admin, _, _ = platform
    first = p.targets.create("default", TargetCreate.model_validate(spec()), admin.id)
    original = p.targets.snapshot("default", first["id"])
    second = p.targets.create("default", TargetCreate.model_validate(spec()), admin.id)
    third = p.targets.create("default", TargetCreate.model_validate(spec()), admin.id)
    names = target_names(p.store, "default")
    assert [names[t["id"]]["display_name"] for t in (first, second, third)] == ["Granite 1", "Granite 2", "Granite 3"]
    assert not names[first["id"]]["is_latest_for_model"]
    assert names[third["id"]]["is_latest_for_model"]
    assert p.targets.snapshot("default", first["id"]) == original
    assert p.store.get(first["id"], "default")["name"] == "Granite"
    assert p.targets.public("default", first["id"])["revision"] == first["revision"]


def test_names_are_consistent_between_paginated_list_detail_and_idempotent_create(platform):
    p, _, _, _ = platform
    headers = {"Authorization": "Bearer " + "a" * 40}
    with TestClient(create_app(p.settings, platform=p, start_workers=False)) as client:
        first = client.post("/api/targets", headers=headers | {"Idempotency-Key": "named-first"}, json=spec()).json()
        second = client.post("/api/targets", headers=headers | {"Idempotency-Key": "named-second"}, json=spec()).json()
        again = client.post("/api/targets", headers=headers | {"Idempotency-Key": "named-second"}, json=spec()).json()
        assert again["id"] == second["id"]
        assert again["display_name"] == "Granite 2"
        newest = client.get("/api/targets?limit=1", headers=headers).json()[0]
        older = client.get("/api/targets?limit=1&offset=1", headers=headers).json()[0]
        detail = client.get("/api/targets/" + first["id"], headers=headers).json()
        assert newest["id"] == second["id"] and newest["display_name"] == "Granite 2"
        assert older["id"] == first["id"] and older["display_name"] == detail["display_name"] == "Granite 1"
        assert "api_key" not in json.dumps(detail)


def test_workspace_boundaries_and_literal_suffix_collisions(platform):
    p, admin, _, _ = platform
    values = [p.targets.create("default", TargetCreate.model_validate(spec(name)), admin.id)
              for name in ("Granite", "Granite", "Granite 1")]
    other = p.targets.create("other", TargetCreate.model_validate(spec()), admin.id)
    names = target_names(p.store, "default")
    assert len({names[t["id"]]["display_name"] for t in values}) == 3
    assert other["id"] not in names
    assert target_names(p.store, "other")[other["id"]]["display_name"] == "Granite"


def test_concurrent_registrations_receive_distinct_readable_numbers(platform):
    p, admin, _, _ = platform
    with ThreadPoolExecutor(4) as executor:
        created = list(executor.map(lambda _: p.targets.create("default", TargetCreate.model_validate(spec("Assistant")), admin.id), range(4)))
    names = target_names(p.store, "default")
    assert {names[t["id"]]["display_name"] for t in created} == {f"Assistant {n}" for n in range(1, 5)}


def test_campaign_numbers_and_latest_target_names_match_list_and_detail(platform):
    p, admin, target, _ = platform
    first = p.create_campaign(admin, CampaignCreate(target_id=target["id"], languages=["en"]))
    second = p.create_campaign(admin, CampaignCreate(target_id=target["id"], languages=["en"]))
    assert first["display_name"] == "Test 1" and second["display_name"] == "Test 2"
    assert campaign_names(p.store, "default")[first["id"]]["is_latest"] is False
    with TestClient(create_app(p.settings, platform=p, start_workers=False)) as client:
        headers = {"Authorization": "Bearer " + "a" * 40}
        newest = client.get("/api/campaigns?limit=1", headers=headers).json()[0]
        older = client.get("/api/campaigns?limit=1&offset=1", headers=headers).json()[0]
        detail = client.get("/api/campaigns/" + second["id"], headers=headers).json()
        assert newest["display_name"] == detail["display_name"] == "Test 2"
        assert newest["target_name"] == target["display_name"]
        assert newest["is_latest"] is True and older["display_name"] == "Test 1"


@pytest.mark.parametrize("revision", ["", "   ", None])
def test_blank_model_revision_can_register_connect_and_create_a_campaign(platform, revision):
    p, admin, _, _ = platform
    parsed = TargetCreate.model_validate(spec("Unpinned target", revision))
    assert parsed.model_revision == ""
    target = p.targets.create("default", parsed, admin.id)
    assert p.targets.preflight("default", target["id"])["connected"]
    campaign = p.create_campaign(admin, CampaignCreate(target_id=target["id"], languages=["en"]))
    assert campaign["state"] == "draft"
    assert p.snapshot_for(campaign, "default")["model_revision"] == ""


def test_model_revision_may_be_omitted_and_model_identifier_is_still_required():
    body = spec()
    body.pop("model_revision")
    assert TargetCreate.model_validate(body).model_revision == ""
    with pytest.raises(ValueError):
        TargetCreate.model_validate(body | {"model": ""})
