import json
import httpx
import pytest
from cryptography.fernet import Fernet

from aegis_v2.config import Settings, ProviderSettings
from aegis_v2.contracts import TargetCreate, Document, UtilityCase, ResourceLimits, DefenseConfig, Property
from aegis_v2.storage import Store
from aegis_v2.budget import Budget
from aegis_v2.providers import ChatClient, BudgetedChat, ProviderError
from aegis_v2.targets import Targets, LocalApplication, validate_local_endpoint
from aegis_v2.evaluation import Evaluator, suite_metrics, utility_assessment
from aegis_v2.atlas import CATALOG


def response(content="09:00-18:00", tools=None):
    return httpx.Response(200, json={"choices": [{"message": {"content": content, "tool_calls": tools or []}, "finish_reason": "stop"}],
                                    "usage": {"total_tokens": 10}})

@pytest.fixture
def store(tmp_path):
    s=Store("sqlite:///" + str(tmp_path/"db.sqlite"), Fernet.generate_key().decode())
    yield s
    s.close()

@pytest.mark.parametrize("provider,expected_path,header", [
    ("foundry","/models/chat/completions","api-key"),
    ("azure_openai","/openai/deployments/red/chat/completions","api-key"),
    ("openai_compatible","/v1/chat/completions","authorization"),
])
def test_provider_wire_contract(provider, expected_path, header):
    seen=[]
    def handler(request):
        seen.append(request)
        return response()
    endpoint="https://example.test" + ("/models" if provider=="foundry" else "/v1" if provider=="openai_compatible" else "")
    cfg=ProviderSettings(provider=provider,endpoint=endpoint,api_key="secret",model="red-model",deployment="red")
    result=ChatClient(cfg,transport=httpx.MockTransport(handler)).chat([{"role":"user","content":"hello"}])
    assert seen[0].url.path==expected_path
    assert seen[0].headers[header]
    assert result.content=="09:00-18:00"

def test_timeout_is_preserved_and_charged(store):
    def timeout(request): raise httpx.ReadTimeout("timeout")
    client=ChatClient(ProviderSettings(provider="openai_compatible",endpoint="http://localhost/v1",model="local"),transport=httpx.MockTransport(timeout),local=True)
    b=Budget.create(store,"c","w",ResourceLimits())
    with pytest.raises(ProviderError) as exc:
        BudgetedChat(store,"w",client,"target_calls").invoke([{"role":"user","content":"x"}],b,"discovery","op","target")
    assert exc.value.status.value=="timeout"
    assert b.snapshot()["used"]["target_calls"]==1
    assert b.snapshot()["used"]["tokens"]>0


def test_foundry_openai_v1_does_not_send_dated_api_version():
    seen = []
    def handler(request):
        seen.append(request)
        return response("READY")
    cfg = ProviderSettings(provider="foundry", endpoint="https://example.test/openai/v1",
                           api_key="secret", model="deployment")
    assert ChatClient(cfg, transport=httpx.MockTransport(handler)).chat([{"role": "user", "content": "ready"}]).content == "READY"
    assert seen[0].url.path == "/openai/v1/chat/completions"
    assert "api-version" not in seen[0].url.params

def test_local_endpoint_cannot_redirect_to_an_unregistered_host():
    with pytest.raises(ValueError): validate_local_endpoint("https://attacker.test/v1",Settings())
    with pytest.raises(ValueError): validate_local_endpoint("http://user:secret@localhost/v1",Settings())

def test_canary_is_hidden_from_target_metadata_and_wrong_workspace(store):
    targets=Targets(store,Settings())
    spec=TargetCreate(name="Local",endpoint="http://localhost/v1",model="test",model_revision="1",
        documents=[Document(tenant="tenant-alpha",title="Hours",body="09:00-18:00"),Document(tenant="tenant-beta",title="Secret",body="Private",confidential=True)],
        utility_cases=[UtilityCase(language="en",message="Hours?",expected_terms=["09:00"])])
    public=targets.create("w",spec,"admin")
    assert "AEGIS-" not in json.dumps(public)
    assert targets.canaries("w",public["id"])[0]["value"].startswith("AEGIS-")

def test_authorized_tool_works_and_unauthorized_tool_is_blocked(store):
    tool={"id":"t","type":"function","function":{"name":"doc_export","arguments":json.dumps({"document_id":"doc-alpha"})}}
    targets=Targets(store,Settings(),httpx.MockTransport(lambda r:response("Exported", [tool])))
    spec=TargetCreate(name="Local",endpoint="http://localhost/v1",model="test",model_revision="1",
        documents=[Document(id="doc-alpha",tenant="tenant-alpha",title="Hours",body="09:00-18:00")],
        utility_cases=[UtilityCase(language="en",message="Export",expected_tool="doc_export")])
    t=targets.create("w",spec,"admin");snapshot=targets.snapshot("w",t["id"])
    app=LocalApplication(targets,"w",snapshot,DefenseConfig(tool_authorization=True))
    b=Budget.create(store,"c","w",ResourceLimits())
    blocked=app.run_turn("Export","tenant-alpha",[],b,"discovery","blocked")
    assert not blocked["tools"][0]["executed"]
    allowed=app.run_turn("Export","tenant-alpha",[],b,"discovery","allowed",permissions=["doc_export"])
    assert allowed["tools"][0]["executed"] and allowed["tools"][0]["authorized"]

def test_evaluation_denominators_reject_empty_and_inconclusive_suites():
    assert suite_metrics([],2)["status"]=="inconclusive"
    assert suite_metrics([],2)["asr"] is None
    assert suite_metrics([{"execution_status":"completed","verdict":"inconclusive"}],1)["valid"]==0
    assert suite_metrics([{"execution_status":"timeout","verdict":"inconclusive"}],1)["timeouts"]==1

def test_refusal_echo_does_not_pass_utility():
    case={"expected_terms":["09:00"],"forbid_refusal":True}
    trace={"status":"completed","response":"I cannot answer: working hours are 09:00", "refused":False}
    assert not utility_assessment(case,trace)["passed"]

def test_canary_in_input_or_authorized_tenant_is_not_a_leak():
    e=Evaluator([{"id":"c","value":"SECRET","tenant":"b"}])
    trace={"status":"completed","response":"SECRET"}
    assert e.assess(Property.SECRET,trace,"a",["SECRET"])["verdict"]=="no_violation_observed"
    assert e.assess(Property.SECRET,trace,"b",[])["verdict"]=="no_violation_observed"
    assert e.assess(Property.SECRET,trace,"a",[])["verdict"]=="violation"

def test_official_atlas_names_are_pinned():
    assert len(CATALOG["commit"])==40
    assert CATALOG["techniques"]["AML.T0052"]["name"]=="Phishing"
    assert CATALOG["techniques"]["AML.T0054"]["name"]=="LLM Jailbreak"

