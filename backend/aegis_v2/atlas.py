from __future__ import annotations
import json
from pathlib import Path
from .contracts import Property

CATALOG = json.loads((Path(__file__).parent / "catalogs" / "atlas.json").read_text(encoding="utf-8"))


def mapping(assessment: dict, surface: str):
    prop = assessment["property"]
    technique = None
    if prop == Property.INSTRUCTION.value and assessment.get("effect") in {"untrusted_instruction_executed", "policy_diversion"}:
        technique = "AML.T0051.001" if surface == "assigned_document" else "AML.T0051.000"
    elif prop == Property.TASK.value and assessment.get("effect") == "policy_diversion":
        technique = "AML.T0054"
    elif prop == Property.SECRET.value and assessment.get("effect") == "confidential_output":
        technique = "AML.T0024"
    elif prop == Property.TOOL.value and assessment.get("effect") == "unauthorized_tool_effect":
        technique = "AML.T0086"
    if technique not in CATALOG["techniques"]:
        return {"technique_id": None, "name": "Unmapped", "reason": "No supported ATLAS mechanism was established by this evidence.",
                "catalog_commit": CATALOG["commit"]}
    item = CATALOG["techniques"][technique]
    return {"technique_id": technique, "name": item["name"], "url": item["url"],
            "reason": assessment.get("effect", ""), "catalog_commit": CATALOG["commit"]}

