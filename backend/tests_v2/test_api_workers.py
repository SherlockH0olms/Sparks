import json
import time
import pytest
from fastapi.testclient import TestClient

from tests_v2.test_discovery import platform, campaign
from aegis_v2.api import create_app
from aegis_v2.contracts import Role
from aegis_v2.runtime import TERMINAL
from aegis_v2.budget import Budget
from aegis_v2.workers import Workers


def wait_state(p,cid,states,seconds=20):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        c=p.store.get(cid,"default")
        if c["state"] in states:return c
        time.sleep(.03)
    pytest.fail("State not reached: "+str(p.store.get(cid,"default")))


def headers(key="a"*40,idem="request"):
    return {"Authorization":"Bearer "+key,"Idempotency-Key":idem}


def test_api_authentication_role_and_workspace_boundaries(platform):
    p,admin,target,_=platform
    with TestClient(create_app(p.settings,platform=p,start_workers=False)) as client:
        assert client.get("/api/targets").status_code==401
        assert client.post("/api/auth/login",json={"key":"a"*40}).status_code==200
        assert client.get("/api/auth/me").json()["role"]=="admin"
        issued=client.post("/api/users",headers=headers(),json={"name":"Reader","role":"viewer","workspace":"default"}).json()
        viewer=issued["access_key"]
        assert client.get("/api/targets",headers=headers(viewer)).status_code==200
        assert client.post("/api/campaigns",headers=headers(viewer),json={"target_id":target["id"]}).status_code==403
        assert client.get("/api/audit",headers=headers(viewer)).status_code==403
        other=client.post("/api/users",headers=headers(),json={"name":"Other","role":"analyst","workspace":"other"}).json()["access_key"]
        assert client.get("/api/targets/"+target["id"],headers=headers(other)).status_code==404
        client.post("/api/auth/logout")
        assert client.get("/api/auth/me").status_code==401


def test_red_library_api_requires_login_and_exposes_only_component_metadata(platform):
    p,_,_,_=platform
    with TestClient(create_app(p.settings,platform=p,start_workers=False)) as client:
        assert client.get("/api/red/library").status_code==401
        result=client.get("/api/red/library",headers=headers()).json()
        assert "methods" in result and "summary" in result
        assert "api_key" not in json.dumps(result).lower()
        assert client.get("/api/health").json()["red_attack_library"]["revision"]==result["summary"]["revision"]


def test_red_corpus_api_auth_search_full_read_and_invalid_ids(platform,monkeypatch):
    from aegis_v2.red_library import AttackLibrary
    library=AttackLibrary({"resources":[{"id":"fixture:seed","framework":"fixture","version":"test","license":"MIT",
        "path":"public.json","title":"Metadata attack","text":"metadata fixture " + "x"*7000,"description":"","sha256":"fixture"}],
        "transforms":[],"frameworks":[],"revision":"api-fixture"})
    monkeypatch.setattr("aegis_v2.api.installed_library",lambda:library)
    p,_,_,_=platform
    with TestClient(create_app(p.settings,platform=p,start_workers=False)) as client:
        for path in ["/api/red/library/sources","/api/red/library/resources","/api/red/library/resource/fixture:seed"]:
            assert client.get(path).status_code==401
        assert client.get("/api/red/library/sources",headers=headers()).json()["summary"]["revision"]=="api-fixture"
        result=client.get("/api/red/library/resources",params={"query":"metadata","limit":1},headers=headers()).json()
        assert result["total"]==1 and "text" not in result["results"][0]
        result=client.get("/api/red/library/resource/fixture:seed",headers=headers()).json()
        assert len(result["text"])>7000
        assert client.get("/api/red/library/resource/nonexistent",headers=headers()).status_code==404
        assert client.get("/api/red/library/resources?limit=100",headers=headers()).status_code==422


def test_idempotent_control_and_real_worker_completion(platform):
    p,admin,target,_=platform
    app=create_app(p.settings,platform=p,start_workers=True)
    with TestClient(app) as client:
        body={"target_id":target["id"],"languages":["en"],"properties":["tool_authorization"],"families":["tool_misuse"],
              "minimum_tests_per_cell":1,"max_discovery_attempts":1,"max_repair_groups":1}
        first=client.post("/api/campaigns",headers=headers(idem="create"),json=body)
        second=client.post("/api/campaigns",headers=headers(idem="create"),json=body)
        assert first.status_code==201 and second.json()["id"]==first.json()["id"]
        cid=first.json()["id"]
        assert client.post("/api/campaigns/"+cid+"/start",headers=headers(idem="start")).status_code==200
        completed=wait_state(p,cid,TERMINAL)
        assert completed["state"]=="completed",completed.get("error")
        assert client.post("/api/campaigns/"+cid+"/start",headers=headers(idem="start")).status_code==200
        summary=client.get("/api/campaigns/"+cid,headers=headers()).json()
        assert summary["coverage"]["coverage_pct"]==100
        assert "coverage_pct" not in summary
        result=client.get("/api/campaigns/"+cid+"/verification",headers=headers()).json()
        assert result[0]["verdict"]=="validated_in_scope"
        pack=client.get("/api/campaigns/"+cid+"/evidence-pack",headers=headers()).json()
        assert pack["assessments"] and pack["budget"]["operations"] and pack["calls"]
        assert "oracle" not in pack
        assert len(pack["content_hash"])==64
        stream=client.get("/api/campaigns/"+cid+"/events?once=true",headers=headers())
        data=[json.loads(line[6:]) for line in stream.text.splitlines() if line.startswith("data: ")]
        assert any(row["kind"]=="scheduler_decision" for row in data)
        assert all(isinstance(row["payload"],dict) for row in data)


def test_worker_pause_resume_preserves_checkpoint(platform):
    p,admin,target,_=platform
    app=create_app(p.settings,platform=p,start_workers=True)
    with TestClient(app) as client:
        cid=campaign(p,admin,target)
        p.control(admin,cid,"pause")
        paused=wait_state(p,cid,{"paused"})
        assert paused["finished_at"] is None
        phase=paused["phase"]
        p.control(admin,cid,"resume")
        complete=wait_state(p,cid,TERMINAL)
        assert complete["state"]=="completed",complete.get("error")
        assert complete["progress"]["discovery"]==2


def test_expired_lease_recovers_and_charges_pending_operation(platform):
    p,admin,target,_=platform;cid=campaign(p,admin,target)
    b=Budget(p.store,cid,"default")
    b.reserve("uncertain","discovery",{"target_calls":1,"tokens":100},"lost request")
    p.store.mutate("job_"+cid,"default",lambda x:x|{"state":"running","owner":"lost-worker","lease_until":0})
    workers=Workers(p)
    claimed=workers.claim("default","job_"+cid)
    assert claimed["owner"]==workers.owner
    assert b.snapshot()["operations"]["uncertain"]["status"]=="interrupted"
    assert b.snapshot()["used"]["target_calls"]==1
    workers.close()


def test_kill_switch_blocks_drafts_and_new_campaigns(platform):
    p,admin,target,_=platform
    with TestClient(create_app(p.settings,platform=p,start_workers=False)) as client:
        cid=campaign(p,admin,target)
        assert client.post("/api/system/kill-switch",headers=headers(),json={"active":True}).status_code==200
        assert p.store.get(cid,"default")["state"]=="cancelled"
        body={"target_id":target["id"],"languages":["en"]}
        assert client.post("/api/campaigns",headers=headers(idem="after-kill"),json=body).status_code==409
        assert client.post("/api/campaigns/"+cid+"/resume",headers=headers(idem="resume")).status_code==409
        assert client.post("/api/system/kill-switch",headers=headers(),json={"active":False}).status_code==200

