import json
from pathlib import Path
import pytest

from tests_v2.test_discovery import platform, campaign
from aegis_v2.runtime import TERMINAL
from aegis_v2.budget import Budget
from aegis_v2.storage import PrivateAccess, Conflict
from aegis_v2.repair import RepairService
from aegis_v2.contracts import CampaignCreate, Family, Property


def run_to_completion(p,cid):
    for _ in range(200):
        if p.store.get(cid,"default")["state"] in TERMINAL:
            return
        p.step("default",cid)
    pytest.fail("Campaign failed to complete")


def test_complete_real_control_pipeline_with_fixture_providers(platform):
    p,admin,target,seen=platform
    cid=campaign(p,admin,target)
    run_to_completion(p,cid)
    c=p.store.get(cid,"default")
    assert c["state"]=="completed" and c["finished_at"]
    assert len(c["experiments"])==1 and len(c["verification_runs"])==1
    e=p.store.get(c["experiments"][0],"default",private_access=True)
    candidates={cand["label"]:cand for cand in e["candidates"]}
    assert candidates["B"]["state"]=="rejected"
    assert candidates["C"]["state"]=="ready"
    assert candidates["C"]["diff"] and candidates["C"]["artifact"]["hash"]
    assert e["winner"]==candidates["C"]["id"] and e["frozen_at"]
    result=p.store.get(c["verification_runs"][0],"default")
    assert result["verdict"]=="validated_in_scope"
    assert result["suites"]["baseline"]["replay"]["asr"]==1
    assert result["suites"]["candidate"]["replay"]["asr"]==0
    assert result["suites"]["candidate"]["unseen"]["valid"]==3
    assert result["suites"]["candidate"]["adaptive"]["valid"]==2
    assert result["suites"]["candidate"]["utility"]["utility"]==1
    b=Budget(p.store,cid,"default").snapshot()
    assert b["used"]["target_calls"]==len(seen["target"])
    assert b["used"]["generator_calls"]==len(seen["red"])
    assert b["reserved"]["target_calls"]==0


def test_final_payload_is_evaluator_only_and_adaptation_receives_candidate_observations(platform):
    p,admin,target,seen=platform;cid=campaign(p,admin,target);run_to_completion(p,cid)
    finals=p.store.list("final","default",private_access=True)
    assert len(finals)==1 and finals[0]["closed_at"]
    with pytest.raises(PrivateAccess):p.store.get(finals[0]["id"],"default")
    adaptive=[r for r in seen["red"] if r.get("defense_information")]
    assert len(adaptive)==2
    assert adaptive[0]["defense_information"]["profile"]=="declared_gray_box"
    assert adaptive[1]["allowed_observations"]
    assert "oracle" not in json.dumps(adaptive)


def test_tampered_candidate_cannot_enter_final_evaluation(platform):
    p,admin,target,_=platform;cid=campaign(p,admin,target)
    for _ in range(100):
        if p.store.get(cid,"default")["phase"]=="verifying":break
        p.step("default",cid)
    c=p.store.get(cid,"default");e=p.store.get(c["experiments"][0],"default",private_access=True)
    winner=next(x for x in e["candidates"] if x["id"]==e["winner"])
    path=Path(winner["artifact"]["path"])
    payload=json.loads(path.read_text());payload["configuration"]["tool_authorization"]=False
    path.write_text(json.dumps(payload))
    with pytest.raises(Conflict):p.step("default",cid)


def test_findings_are_scoped_to_campaign_not_global_defect_hash(platform):
    p,admin,target,_=platform
    ids=[]
    for _ in range(2):
        cid=campaign(p,admin,target);run_to_completion(p,cid)
        c=p.store.get(cid,"default");ids.append(c["findings"][0])
        assert p.store.get(ids[-1],"default",private_access=True)["campaign_id"]==cid
    assert ids[0]!=ids[1]

