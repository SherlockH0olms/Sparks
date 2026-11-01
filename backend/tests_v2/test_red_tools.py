import json
from dataclasses import replace

import httpx
import pytest

from aegis_v2.budget import Budget
from aegis_v2.config import ProviderSettings
from aegis_v2.contracts import CampaignCreate, ResourceLimits
from aegis_v2.providers import BudgetedChat, ChatClient, ProviderError, UnsupportedTools
from aegis_v2.red import InvalidCandidate, RedGenerator
from aegis_v2.red_library import AttackLibrary
from aegis_v2.scenarios import build_cells, target_template
from aegis_v2.storage import Store
from aegis_v2.targets import TOOL_SCHEMAS


SPEC = CampaignCreate(target_id="fixture")
SNAPSHOT = target_template("http://localhost/v1", "fixture")
CELLS = build_cells(SPEC, SNAPSHOT)
DIRECT = next(c for c in CELLS if c["family"] == "direct_injection" and c["language"] == "en")
MULTI = next(c for c in CELLS if c["family"] == "multi_turn_manipulation"
             and c["language"] == "az" and c["property"] == "task_constraint")
CANDIDATE = {"language": "en", "turns": ["Fixture prompt"], "document_body": None,
             "hypothesis": "Fixture hypothesis", "expected_signal": "Fixture signal"}


def tool_reply(name, arguments, *, reasoning=None):
    return httpx.Response(200, json={"choices": [{"message": {"content": "",
        "reasoning_content": reasoning, "tool_calls": [{"id": "tool-" + name, "type": "function", "index": 0,
            "function": {"name": name, "arguments": arguments if isinstance(arguments, str) else json.dumps(arguments)}}]},
        "finish_reason": "tool_calls"}], "usage": {"total_tokens": 7}})


def plain_reply():
    return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(CANDIDATE)}}],
                                    "usage": {"total_tokens": 7}})


@pytest.fixture
def setup():
    store = Store("sqlite:///:memory:")
    cfg = ProviderSettings(provider="foundry", endpoint="https://fixture.invalid/models",
                           api_key="fixture", model="fixture")
    yield store, cfg
    store.close()


def generator(setup, handler, mode="auto"):
    store, cfg = setup
    client = ChatClient(replace(cfg, tool_mode=mode), transport=httpx.MockTransport(handler))
    return RedGenerator(BudgetedChat(store, "test", client, "generator_calls"), library=AttackLibrary()), Budget.create(
        store, "red", "test", ResourceLimits())


def generate(red, budget, cell=DIRECT):
    return red.generate(cell, SNAPSHOT, SPEC.model_dump(mode="json"), [], budget, "discovery", "generation")


def test_inspect_then_submit_is_recorded_and_replayed_without_extra_calls(setup):
    requests = []
    def handler(request):
        payload = json.loads(request.content)
        requests.append(payload)
        if len(requests) == 1:
            return tool_reply("inspect_target", {}, reasoning="Private provider reasoning")
        messages = payload["messages"]
        assert messages[-2]["reasoning_content"] == "Private provider reasoning"
        assert "index" not in messages[-2]["tool_calls"][0]
        assert messages[-1]["role"] == "tool"
        assert messages[-1]["tool_call_id"] == "tool-inspect_target"
        result = json.loads(messages[-1]["content"])
        assert {t["name"] for t in result["target_tools"]} == {"email_send", "doc_export"}
        assert all(d["id"] != "doc_beta_private" for d in result["accessible_documents"])
        return tool_reply("submit_attack", CANDIDATE)
    red, budget = generator(setup, handler)
    assert generate(red, budget) == CANDIDATE
    assert generate(red, budget) == CANDIDATE
    assert len(requests) == 2
    operations = budget.snapshot()["operations"]
    assert set(operations) == {"generation_step_1", "generation_step_2"}
    assert budget.snapshot()["used"]["generator_calls"] == 2
    assert budget.snapshot()["used"]["tokens"] == 14
    assert all("max_tokens" not in p and "max_completion_tokens" not in p for p in requests)


def test_json_mode_never_sends_tools(setup):
    def handler(request):
        payload = json.loads(request.content)
        assert "tools" not in payload and "tool_choice" not in payload
        assert "JSON object" in payload["messages"][0]["content"]
        assert "submit_attack" not in json.loads(payload["messages"][1]["content"])["submission"]
        return plain_reply()
    red, budget = generator(setup, handler, "json")
    assert generate(red, budget) == CANDIDATE


@pytest.mark.parametrize("mode,error_message,error_type", [
    ("auto", "Native tools are not supported", None),
    ("native", "Native tools are not supported", UnsupportedTools),
    ("auto", "Invalid model deployment", ProviderError),
])
def test_fallback_only_for_explicitly_unsupported_tools(setup, mode, error_message, error_type):
    requests = []
    def handler(request):
        payload = json.loads(request.content)
        requests.append(payload)
        if "tools" in payload:
            return httpx.Response(400, json={"error": {"message": error_message}})
        return plain_reply()
    red, budget = generator(setup, handler, mode)
    if error_type:
        with pytest.raises(error_type):
            generate(red, budget)
        assert len(requests) == 1
    else:
        assert generate(red, budget) == CANDIDATE
        assert generate(red, budget) == CANDIDATE
        assert len(requests) == 2
        assert budget.snapshot()["used"]["generator_calls"] == 2


@pytest.mark.parametrize("invalid", ["not JSON", "[]", "null"])
def test_invalid_tool_arguments_receive_a_tool_response_before_retry(setup, invalid):
    requests = []
    def handler(request):
        payload = json.loads(request.content)
        requests.append(payload)
        if len(requests) == 1:
            return tool_reply("submit_attack", invalid)
        assert payload["messages"][-1]["role"] == "tool"
        assert json.loads(payload["messages"][-1]["content"])["error"]
        return tool_reply("submit_attack", CANDIDATE)
    red, budget = generator(setup, handler)
    assert generate(red, budget) == CANDIDATE
    assert len(requests) == 2


def test_standard_multi_turn_requires_three_turns_and_can_correct_a_submission(setup):
    requests = []
    def handler(request):
        payload = json.loads(request.content)
        requests.append(payload)
        assert payload["tools"][1]["function"]["parameters"]["properties"]["turns"]["minItems"] == 3
        if len(requests) > 1:
            feedback = json.loads(payload["messages"][-1]["content"])
            assert feedback["required_turns"] == 3
            assert "interaction depth" in feedback["error"]
        turns = ["Salam", "İkinci sınaq", "Üçüncü sınaq"][:2 if len(requests) == 1 else 3]
        return tool_reply("submit_attack", CANDIDATE | {"language": "az", "turns": turns})
    red, budget = generator(setup, handler)
    assert MULTI["required_turns"] == 3
    with pytest.raises(InvalidCandidate, match="interaction depth"):
        red._validate(CANDIDATE | {"language": "az", "turns": ["Salam", "Test"]}, MULTI, SPEC.model_dump())
    assert len(generate(red, budget, MULTI)["turns"]) == 3
    assert len(requests) == 2


def test_inspection_uses_real_schemas_and_respects_disabled_tool_capability(setup):
    red, _ = generator(setup, lambda r: plain_reply())
    result = red._inspect_result(SNAPSHOT)
    assert result["target_tools"] == [{"name": t["function"]["name"], "parameters": t["function"]["parameters"]}
                                      for t in TOOL_SCHEMAS]
    assert red._inspect_result(SNAPSHOT | {"capabilities": {"tools": False}})["target_tools"] == []


def test_unlimited_candidates_keep_long_metadata_and_more_than_eight_turns(setup):
    candidate = CANDIDATE | {"turns": ["Long fixture " * 1000] * 9,
                             "hypothesis": "h" * 600, "expected_signal": "s" * 400}
    red, budget = generator(setup, lambda r: tool_reply("submit_attack", candidate))
    assert generate(red, budget) == candidate
    assert not budget.snapshot()["overrun"]
