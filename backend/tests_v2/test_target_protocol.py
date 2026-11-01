import json
import httpx
import pytest
from tests_v2.test_discovery import platform, campaign
from aegis_v2.target_protocol import decode
from aegis_v2.providers import ProviderError
from aegis_v2.targets import LocalApplication
from aegis_v2.contracts import DefenseConfig
from aegis_v2.budget import Budget


@pytest.mark.parametrize("content", [
    'I called doc_export', '<tool_call name="doc_export"></tool_call>',
    '{"response":"ok","tool_calls":[],"extra":true}',
    '{"response":"ok","response":"bad","tool_calls":[]}',
    '{"response":"ok","tool_calls":[{"name":"doc_export","arguments":"{}"}]}',
])
def test_text_claims_and_malformed_envelopes_are_not_tool_effects(content):
    with pytest.raises(ProviderError):
        decode(content, False)


def test_json_adapter_effects_use_the_actual_authorization_gateway(platform):
    p, admin, target, _ = platform
    cid = campaign(p, admin, target)
    envelope = {"response": "Export requested", "tool_calls": [{"name": "doc_export", "arguments": {"document_id": "doc_alpha_contract"}}]}
    seen = []
    def respond(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(envelope)}}], "usage": {"total_tokens": 10}})
    p.targets.transport = httpx.MockTransport(respond)
    snapshot = p.targets.snapshot("default", target["id"]) | {"tool_mode": "json"}
    app = LocalApplication(p.targets, "default", snapshot, DefenseConfig(tool_authorization=True))
    denied = app.run_turn("Export doc_alpha_contract", "tenant-alpha", [], Budget(p.store, cid, "default"), "development", "json-denied")
    assert denied["tool_protocol"] == "declared_json_adapter"
    assert not denied["tools"][0]["executed"]
    assert "tools" not in seen[0] and "APPLICATION RESPONSE PROTOCOL" in seen[0]["messages"][0]["content"]
    allowed = app.run_turn("Export doc_alpha_contract", "tenant-alpha", [], Budget(p.store, cid, "default"), "development", "json-allowed", permissions=["doc_export"])
    assert allowed["tools"][0]["executed"] and allowed["tools"][0]["authorized"]
    assert len(p.store.list("tool_effect", "default")) == 1


def test_structured_adapter_response_preserves_output_validation(platform):
    p, admin, target, _ = platform
    cid = campaign(p, admin, target)
    p.targets.transport = httpx.MockTransport(lambda r: httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({"response": {"answer": 42, "citations": [], "task": "document_qa"}, "tool_calls": []})}}]}))
    snapshot = p.targets.snapshot("default", target["id"]) | {"tool_mode": "json"}
    app = LocalApplication(p.targets, "default", snapshot, DefenseConfig(output_validation=True))
    trace = app.run_turn("Return JSON", "tenant-alpha", [], Budget(p.store, cid, "default"), "development", "json-schema", expect_json=True)
    assert trace["refused"] and trace["structured"]["answer"] == ""


def test_one_complete_json_fence_is_supported_but_surrounding_claims_are_rejected():
    envelope = '{"response":"ok","tool_calls":[]}'
    assert decode('```json\n' + envelope + '\n```', False) == ('ok', [])
    with pytest.raises(ProviderError):
        decode('I executed the tool.\n```json\n' + envelope + '\n```', False)


def test_plain_text_can_answer_but_cannot_create_an_effect(platform):
    p, admin, target, _ = platform
    cid = campaign(p, admin, target)
    p.targets.transport = httpx.MockTransport(lambda r: httpx.Response(200, json={"choices": [{"message": {"content": 'I called doc_export. Working hours: 09:00-18:00.'}}]}))
    snapshot = p.targets.snapshot("default", target["id"]) | {"tool_mode": "json", "max_output_tokens": None}
    app = LocalApplication(p.targets, "default", snapshot)
    trace = app.run_turn("Working hours?", "tenant-alpha", [], Budget(p.store, cid, "default"), "development", "text-not-effect")
    assert trace["status"] == "completed" and "09:00" in trace["response"]
    assert trace["tools"] == [] and not p.store.list("tool_effect", "default")
