import io
import json
from copy import deepcopy

import pytest
from pypdf import PdfReader
from pptx import Presentation

from aegis_v2.report_evidence import evidence_story, output_excerpt
from aegis_v2.reporting import Reporting
from tests_v2.test_discovery import platform, campaign
from tests_v2.test_verification import run_to_completion


@pytest.mark.parametrize("property,effect", [
    ("tenant_isolation", "unauthorized_retrieval"),
    ("tool_authorization", "unauthorized_tool_effect"),
    ("secret_confidentiality", "confidential_output"),
    ("output_integrity", "invalid_output_contract"),
    ("data_instruction_separation", "untrusted_instruction_executed"),
    ("task_constraint", "policy_diversion"),
    ("session_isolation", "confidential_output"),
])
def test_readable_evidence_bounds_quotes_for_every_property(property, effect):
    tail = "FULL-EVIDENCE-TAIL-SENTINEL"
    candidate = {"language": "en", "turns": ["Recorded test input. " * 1000 + tail]}
    steps = [{"trace": {"response": "Recorded target response. " * 1000 + tail, "tools": []},
              "assessment": {"verdict": "violation", "effect": effect, "oracle": "test-oracle",
                             "evidence": [{"id": "doc_other", "tenant": "tenant-beta"}]}}]
    result = evidence_story(candidate, steps, property, "tenant-alpha", "attempt-1")
    assert result["expected_behavior"] and result["observed_result"]
    assert result["inputs"][0]["shortened"] and len(result["inputs"][0]["text"]) <= 302
    assert result["target_output"]["shortened"] and len(result["target_output"]["text"]) <= 362
    assert tail not in json.dumps(result)
    assert candidate["turns"][0].endswith(tail) and steps[0]["trace"]["response"].endswith(tail)
    if property == "tenant_isolation":
        assert result["executed_tool_effects"] == 0
        assert "does not claim a successful export" in result["interpretation"]
        assert result["proof_rows"][0][2] == "doc_other"


def test_output_excerpt_uses_declared_answer_and_marks_protocol_diagnostic():
    quote = output_excerpt(json.dumps({"answer": "Recorded user-facing answer.", "metadata": "private presentation noise"}))
    assert quote["text"] == "Recorded user-facing answer."
    quote = output_excerpt("<arg_missing>document_id required</arg_missing>\n\nRecorded visible output.")
    assert quote["text"] == "Recorded visible output." and "protocol diagnostic" in quote["note"]


def test_multiturn_and_document_inputs_remain_bounded_and_source_use_is_not_invented():
    candidate = {"language": "en", "turns": ["First input", "Middle input", "Last input"],
                 "document_body": "Document content " * 1000,
                 "red_strategy": {"method_id": "wild_repetition", "resources": [
                     {"id": "same-resource", "framework": "wildteaming"}, {"id": "same-resource", "framework": "wildteaming"}],
                     "tactic_ids": ["tactic-1", "tactic-1"], "transformations": []}}
    result = evidence_story(candidate, [], "data_instruction_separation")
    assert [item["label"] for item in result["inputs"]] == ["Attack turn 1", "Attack turn 3", "Assigned document input"]
    assert result["omitted_input_turns"] == 1 and result["inputs"][-1]["shortened"]
    assert result["sources"] == ["WildTeaming"] and result["resource_count"] == result["tactic_count"] == 1
    assert result["transformation_count"] == 0 and result["executed_tool_effects"] is None


@pytest.mark.parametrize("legacy", [False, True])
def test_all_presentations_quote_evidence_without_printing_full_json(platform, legacy):
    p, admin, target, _ = platform
    cid = campaign(p, admin, target)
    run_to_completion(p, cid)
    reporting = Reporting(p)
    report = reporting.model("default", cid)
    risk = report["risk_register"][0]
    tail = "FULL-EVIDENCE-TAIL-SENTINEL"
    candidate = {"language": "en", "turns": ["Example recorded request. " * 1000 + tail]}
    steps = [{"input": candidate["turns"][0], "response": "Example recorded response. " * 1000 + tail,
              "assessment": {"verdict": "violation", "effect": "unauthorized_tool_effect", "evidence": []}}]
    risk["evidence_excerpt"] = json.dumps({"minimized_input": candidate, "observations": steps})
    if legacy:
        risk.pop("evidence_story")
    else:
        risk["evidence_story"] = evidence_story(candidate, steps, risk["property"], attempt_id=risk["original_attempt_id"])
    original = deepcopy(report)
    html = reporting.html(report)
    markdown = reporting.markdown("default", cid, report)
    pdf = PdfReader(io.BytesIO(reporting.pdf(report)))
    pdf_text = "\n".join(page.extract_text() for page in pdf.pages)
    deck = Presentation(io.BytesIO(reporting.powerpoint(report)))
    slides = "\n".join(shape.text for slide in deck.slides for shape in slide.shapes if shape.has_text_frame)
    for content in (html, markdown, pdf_text, slides):
        assert "What actually happened" in content and "Example recorded request" in content
        assert "Example recorded response" in content and tail not in content
        assert '"minimized_input"' not in content and '"observations"' not in content
        assert "JSON/NDJSON" in content
    assert report == original and tail in risk["evidence_excerpt"]
    assert max(len(page.extract_text()) for page in pdf.pages) < 7000
