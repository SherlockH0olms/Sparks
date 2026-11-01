from __future__ import annotations

import html
import json
import hashlib
import io
import zipfile
from datetime import datetime, timezone
from .standards import campaign_crosswalk, remediation_plan
from .report_design import html_report, pdf_report, powerpoint_report, rate, label, metric_rows
from .report_evidence import evidence_story, risk_story
from .budget import Budget
from .contracts import digest, now
from .scenarios import coverage
from .runtime import TERMINAL


class Reporting:
    def __init__(self, platform):
        self.p = platform

    def build(self, workspace, campaign_id, *, sensitive=False, include_final=False):
        store=self.p.store;c=store.get(campaign_id,workspace)
        findings=[store.get(fid,workspace,private_access=True) for fid in c["findings"]]
        experiments=[store.get(eid,workspace,private_access=True) for eid in c["experiments"]]
        verification=[store.get(vid,workspace) for vid in c["verification_runs"]]
        attempts=list(store.iter_records("attempt",workspace,parent=campaign_id,private_access=True))
        # Export all execution and assessment records, including failed calls.
        calls=list(store.iter_records("call",workspace,parent=campaign_id,private_access=True))
        operation_ids=set(Budget(store,campaign_id,workspace).snapshot()["operations"])
        calls=[call for call in calls if call["id"].removeprefix("call_") in operation_ids]
        if not include_final:
            attempts=[a for a in attempts if a["phase"] not in {"final","utility"}]
        metadata=self.p.targets.store.get(c["target_id"],workspace)
        pack={"schema_version":"2","campaign":self.p.summary(workspace,campaign_id),"target":metadata,
              "scope":c["cells"],"attempts":attempts,
              "assessments":[{"attempt_id":a["id"],"turn":s["index"],"assessment":s["assessment"]} for a in attempts for s in a["steps"]],
              "findings":findings,"experiments":experiments,"verification":verification,
              "budget":Budget(store,campaign_id,workspace).snapshot(),"calls":calls if sensitive else [{"id":call["id"],"status":call["status"],"model":call["model"],"provenance":call["provenance"]} for call in calls],
              "generated_at":now(),"disclosure":"raw_operator_evidence" if sensitive else "redacted",
              "limitations":["No result implies security outside the fixed scope and revision.",
                             "External model identity and sampling behavior must be pinned by the operator."]}
        if include_final:
            pack["final_protocols"]=[f for f in store.iter_records("final",workspace,parent=campaign_id,private_access=True) if f["state"]=="closed"]
        if sensitive:
            pack["target_snapshot"]=self.p.snapshot_for(c,workspace)
            for key in ("api_key", "access_client_id", "access_client_secret"):
                pack["target_snapshot"].pop(key, None)
            pack["oracle"]=self.p.targets.canaries(workspace,c["target_id"])
        else:
            pack=json.loads(self.p.redact(workspace,c["target_id"],pack))
            for experiment in pack["experiments"]:
                for candidate in experiment["candidates"]:
                    candidate["artifact"].pop("path",None)
        pack["content_hash"]=digest(pack)
        return pack

    def model(self, workspace, campaign_id):
        c = self.p.store.get(campaign_id, workspace)
        summary = self.p.summary(workspace, campaign_id)
        target = self.p.targets.store.get(c["target_id"], workspace)
        findings = [self.p.store.get(fid, workspace, private_access=True) for fid in c["findings"]]
        experiments = [self.p.store.get(eid, workspace, private_access=True) for eid in c["experiments"]]
        verification = [self.p.store.get(vid, workspace) for vid in c["verification_runs"]]
        # Older records stored zero for incomplete utility suites. Present them
        # as unmeasured without rewriting the immutable execution evidence.
        for run in verification:
            incomplete = False
            for suites in run["suites"].values():
                metric = suites["utility"]
                if not metric["questions"] or metric["valid"] != metric["questions"]:
                    metric["utility"] = None
                    incomplete = True
            if incomplete:
                run["utility_delta"] = None
        validated = sum(v["verdict"] == "validated_in_scope" for v in verification)
        decision = (f"{validated} of {len(verification)} evaluated defense candidates validated within the recorded scope."
                    if verification else "No defense candidate has received final validation.")
        if c["state"] not in TERMINAL:
            decision = "Campaign in progress: this report is a snapshot. " + decision
        titles = {"tool_authorization": "Unauthorized tool effects", "tenant_isolation": "Cross-tenant document access",
                  "secret_confidentiality": "Confidential information disclosure", "output_integrity": "Output contract violation",
                  "data_instruction_separation": "Untrusted data treated as instructions", "task_constraint": "Task policy diversion",
                  "session_isolation": "Session confidentiality violation"}
        impacts = {"tool_authorization": "The registered gateway recorded an effect without trusted authorization. Production impact depends on the connected tools.",
                   "tenant_isolation": "Documents owned by another tenant entered the retrieval result set.",
                   "secret_confidentiality": "A protected server-owned marker appeared in the public response.",
                   "output_integrity": "The response violated the declared application contract and could disrupt a downstream consumer.",
                   "data_instruction_separation": "Untrusted reference text crossed the instruction boundary.",
                   "task_constraint": "The target deviated from its declared task policy.",
                   "session_isolation": "Protected information crossed the declared session confidentiality boundary."}
        risks = []
        tenant = self.p.snapshot_for(c, workspace)["tenant"] if findings else None
        for finding in findings:
            exp = next((e for e in experiments if e["finding_id"] == finding["id"]), None)
            selected = next((cand for cand in exp["candidates"] if cand["id"] == exp["winner"]), None) if exp and exp.get("winner") else None
            run = next((v for v in verification if exp and v["experiment_id"] == exp["id"]), None)
            plan = selected.get("plan") if selected else None
            plan = plan or (exp or {}).get("diagnosis") or remediation_plan(finding, {})
            original = self.p.store.get(finding["original_attempt_id"], workspace, private_access=True)
            excerpt = json.dumps({"minimized_input": finding["minimized_candidate"], "observations": [
                {"input": s["message"], "response": s["trace"].get("response", ""), "assessment": s["assessment"]}
                for s in original["steps"]]}, indent=2, ensure_ascii=False)
            rows = [[cand["label"], ", ".join(label(k) for k, value in cand["patch"].items() if value) or "Baseline reference",
                     label(cand["state"]), rate(cand.get("gates", {}).get("security", {}).get("asr")),
                     rate(cand.get("gates", {}).get("utility", {}).get("utility"))] for cand in (exp or {}).get("candidates", [])]
            risks.append({"id": finding["id"], "title": titles.get(finding["property"], label(finding["property"])),
                "property": finding["property"], "severity": finding["severity"], "boundary": finding["boundary"], "effect": finding["effect"],
                "impact_rationale": impacts.get(finding["property"], "Review the recorded effect in the target's operational context."),
                "reproduction_rate": finding["reproduction_rate"], "original_attempt_id": finding["original_attempt_id"],
                "diagnosis": plan["diagnosis"], "atlas": finding["atlas"], "nist": plan["nist"],
                "selected_candidate": selected, "candidate_rows": rows,
                "disposition": label(run["verdict"]) if run else "Awaiting independent verification" if selected else "No qualifying candidate" if exp else "Remediation not evaluated",
                "deployment_steps": plan["deployment"]["steps"],
                "rollback_guidance": "Restore the recorded baseline configuration and target revision if utility, false-block, startup, or connectivity criteria fail.",
                "residual_risks": plan["residual_risks"] + ["Results apply to the registered application adapter and tested target version."],
                "evidence_excerpt": excerpt,
                "evidence_story": evidence_story(finding["minimized_candidate"], original["steps"], finding["property"],
                    tenant, finding["original_attempt_id"])})
        budget = summary["budget"]
        limitations = [
            f"{summary['coverage']['applicable'] - summary['coverage']['completed']} applicable discovery cells remain incomplete.",
            "A source library resource count is not an executed test count or an attack success rate.",
            "Timeouts, invalid tests, connection failures, and unavailable semantic assessments do not establish defense success.",
            "Generated and adaptive cases can be correlated. Rates, confidence intervals, and paired statistics describe this experiment and do not certify population-wide resilience.",
            "The operator must pin external model weights, sampling behavior, and application versions.",
            "The email/export gateway is simulated. Controls must be implemented and retested at actual production tool boundaries.",
            "NIST mappings document supporting evidence and plans. Organizational governance, legal compliance, fairness, and production monitoring were not audited.",
            "Deployment of an artifact to an external application requires application-owner review and destination-environment verification."]
        if target.get("tool_mode") == "json":
            limitations.append("Tool requests use the declared JSON application adapter. These are real model-produced requests through the registered gateway, not native API function calls.")
        if c.get("error"):
            limitations.append("Recorded workflow issue: " + c["error"]["type"] + ": " + c["error"]["message"])
        stamp = now()
        report = {"report_revision": "remediation-evidence-v4", "campaign_id": campaign_id, "state": c["state"],
            "generated_at": stamp, "generated_label": datetime.fromtimestamp(stamp, timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "fixture_environment": self.p.red_client.provenance == "fixture", "target": target, "scope": summary["coverage"],
            "executive_summary": {"decision": decision, "findings": len(findings), "validated": validated,
                "final_valid_tests": sum(v["suites"]["candidate"][suite].get("valid", 0) for v in verification for suite in ("replay", "unseen", "adaptive")),
                "interpretation": ("Validated candidates passed the recorded security and normal-use requirements. Validation applies only within this scope."
                                   if validated else "No candidate met all final validation requirements. Review rejected and incomplete suites before deployment. A completed workflow alone does not establish a successful remedy.")},
            "scope_rows": [["Target", target["name"]], ["Model / pinned version", target["model"] + " / " + target["model_revision"]],
                ["Application version", target["application_revision"]], ["Target snapshot", c["target_revision"]],
                ["Connection", target.get("connection_kind", "local") + " / " + target["endpoint"]],
                ["Tool protocol", target.get("tool_mode", "native")],
                ["Languages", ", ".join(c["spec"]["languages"])], ["Security properties", ", ".join(label(p) for p in c["spec"]["properties"])],
                ["Attack families", ", ".join(label(f) for f in c["spec"]["families"])],
                ["Discovery cells", str(summary["coverage"]["completed"]) + " / " + str(summary["coverage"]["applicable"])],
                ["Verification protocol", c["spec"].get("remediation_profile", "legacy") + "; " + c["spec"].get("verification_scope", "finding") + " scope"],
                ["Fresh / adaptive cases per cell", str(c["spec"]["final_cases_per_property"]) + " / " + str(c["spec"]["adaptive_attempts"])]],
            "risk_register": risks, "verification": verification, "standards": campaign_crosswalk(c, findings, verification),
            "resource_rows": [[label(resource), limit if limit is not None else "Unlimited", round(budget["used"][resource], 3),
                               round(budget["reserved"][resource], 3)] for resource, limit in budget["limits"].items()],
            "limitations": limitations,
            "references": sorted({"https://atlas.mitre.org/", "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf",
                "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf",
                "https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html"})}
        report = json.loads(self.p.redact(workspace, c["target_id"], report))
        for risk in report["risk_register"]:
            if risk["selected_candidate"]:
                risk["selected_candidate"]["artifact"].pop("path", None)
        report["content_hash"] = digest(report)
        return report

    def bundle(self, workspace, campaign_id):
        campaign = self.p.store.get(campaign_id, workspace)
        files = {}
        for eid in campaign["experiments"]:
            experiment = self.p.store.get(eid, workspace, private_access=True)
            verification = self.p.store.get(experiment["verification_id"], workspace) if experiment.get("verification_id") else None
            for candidate in experiment["candidates"]:
                # Verify the persisted artifact before including any configuration.
                from .repair import RepairService
                config = RepairService(self.p).read_config(candidate, campaign["target_revision"])
                base = eid + "/" + candidate["label"]
                selected = candidate["id"] == experiment["winner"]
                eligible = bool(selected and experiment["state"] == "validated_in_scope" and verification
                    and verification["verdict"] == "validated_in_scope" and verification["independent"]
                    and verification["candidate_id"] == candidate["id"]
                    and verification["candidate_hash"] == candidate["artifact"]["hash"]
                    and verification["target_revision"] == campaign["target_revision"])
                files[base + "-configuration.json"] = json.dumps({"target_revision": campaign["target_revision"],
                    "configuration": config.model_dump()}, indent=2, sort_keys=True).encode()
                files[base + "-plan.json"] = json.dumps({"candidate_id": candidate["id"], "state": candidate["state"],
                    "artifact_hash": candidate["artifact"]["hash"], "selected": selected,
                    "deployment_eligible": eligible,
                    "verification_verdict": (verification["verdict"] if verification else "not_completed") if selected else "not_selected",
                    "verification_id": verification["id"] if selected and verification else None,
                    "plan": candidate.get("plan"), "rollback": candidate["rollback"],
                    "rejection_reasons": candidate["rejection_reasons"]}, indent=2).encode()
        files["README.md"] = ("# AEGIS remediation bundle\n\nApply only a selected candidate validated in the recorded scope. "
            "The selected plan must have deployment_eligible=true. Pending, rejected, or inconclusive verification cannot authorize deployment. "
            "These configurations control the AEGIS application adapter; implement equivalent controls at production retrieval, "
            "output, and tool boundaries before deployment. Review every plan and run destination-environment tests. "
            "Rollback restores the recorded baseline configuration. Credentials and model weights are excluded.\n").encode()
        manifest = {"schema_version": "3", "campaign_id": campaign_id, "campaign_state": campaign["state"], "target_revision": campaign["target_revision"],
            "generated_at": now(), "files": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}
        files["manifest.json"] = json.dumps(manifest, indent=2).encode()
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        return buffer.getvalue()

    def ndjson(self, workspace, campaign_id, *, sensitive=False):
        campaign = self.p.store.get(campaign_id, workspace)
        checksum = hashlib.sha256()
        counts = {}
        def line(value):
            encoded = (json.dumps(value, ensure_ascii=False) if sensitive else self.p.redact(workspace, campaign["target_id"], value)) + "\n"
            checksum.update(encoded.encode("utf-8"))
            return encoded
        manifest = {"kind": "manifest", "schema_version": "3", "campaign_id": campaign_id,
            "campaign": self.p.summary(workspace, campaign_id), "scope": campaign["cells"],
            "target": self.p.targets.store.get(campaign["target_id"], workspace),
            "budget": Budget(self.p.store, campaign_id, workspace).snapshot(), "generated_at": now(),
            "disclosure": "raw_operator_evidence" if sensitive else "redacted",
            "snapshot_notice": "Live exports can include records added during traversal; closed campaigns provide a stable evidence set."}
        if sensitive:
            snapshot = self.p.snapshot_for(campaign, workspace)
            for key in ("api_key", "access_client_id", "access_client_secret"):
                snapshot.pop(key, None)
            manifest["target_snapshot"] = snapshot
            manifest["oracle"] = self.p.targets.canaries(workspace, campaign["target_id"])
        yield line(manifest)
        for kind in ("attempt", "call", "experiment", "finding", "verification", "final"):
            if kind == "final" and not sensitive:
                continue
            for record in self.p.store.iter_records(kind, workspace, parent=campaign_id, private_access=True):
                if not sensitive and kind == "attempt" and record["phase"] in {"final", "utility"}:
                    continue
                if kind == "call" and not sensitive:
                    record = {key: record[key] for key in ("id", "status", "model", "provenance")}
                if kind == "experiment":
                    for candidate in record["candidates"]:
                        candidate["artifact"].pop("path", None)
                value = {"kind": kind, "record": record}
                counts[kind] = counts.get(kind, 0) + 1
                yield line(value)
        yield json.dumps({"kind": "integrity", "counts": counts, "sha256": checksum.hexdigest(),
                          "hash_scope": "UTF-8 bytes of all preceding lines including LF; excludes this trailer"}) + "\n"

    def pdf(self, report):
        return pdf_report(report)

    def powerpoint(self, report):
        return powerpoint_report(report)

    def markdown(self, workspace, campaign_id, report=None):
        report = report or self.model(workspace, campaign_id)
        rows = ["# AEGIS LOOP AI Security and Remediation Review", "", "Campaign: " + campaign_id,
                "Target: " + report["target"]["name"], "State: " + label(report["state"]), ""]
        if report["fixture_environment"]:
            rows += ["**TEST FIXTURE: simulated models; no real-model resilience measurement.**", ""]
        rows += ["## Executive decision", "", report["executive_summary"]["decision"], report["executive_summary"]["interpretation"], "",
                 "## Scope and identity", "", "| Field | Recorded value |", "|---|---|"]
        def cell(value):
            return str(value).replace("|", "/").replace("\n", " ")
        rows += ["| " + cell(name) + " | " + cell(value) + " |" for name, value in report["scope_rows"]]
        rows += ["", "## Findings and remediation", ""]
        for risk in report["risk_register"]:
            rows += ["### " + risk["title"], "", "Finding: " + risk["id"], "Severity: " + label(risk["severity"]),
                     "Boundary: " + risk["boundary"], "Effect: " + risk["effect"], "Impact: " + risk["impact_rationale"],
                     "Fresh-session reproduction: " + rate(risk["reproduction_rate"]), "Disposition: " + risk["disposition"],
                     "Diagnosis: " + risk["diagnosis"], "ATLAS: " + str(risk["atlas"].get("technique_id") or "Unmapped") + " / " + risk["atlas"]["name"],
                     ""]
            evidence = risk_story(risk)
            rows += ["#### What actually happened", "", evidence["observed_result"], "",
                     "**Expected behavior:** " + evidence["expected_behavior"], "",
                     "**Why this is the finding:** " + evidence["interpretation"], ""]
            for item in evidence["inputs"] + [{"label": "Recorded target output", **evidence["target_output"]}]:
                if item["text"]:
                    rows += ["**" + item["label"] + " (short excerpt):**", "", "> " + item["text"], ""]
            rows += [evidence["evidence_notice"], "Evidence reference: " + str(evidence["attempt_id"]), "",
                     "| Candidate | Controls | Verdict | Development ASR | Utility |", "|---|---|---|---|---|"]
            rows += ["| " + " | ".join(cell(item) for item in row) + " |" for row in risk["candidate_rows"]]
            rows += ["", "Deployment steps:"] + [str(i) + ". " + step for i, step in enumerate(risk["deployment_steps"], 1)]
            rows += ["Rollback: " + risk["rollback_guidance"], "", "Residual risks:"] + ["- " + x for x in risk["residual_risks"]] + [""]
        rows += ["## Paired independent verification", "", "| Suite | Baseline | Candidate | Valid candidate tests | Status |", "|---|---|---|---|---|"]
        rows += ["| " + " | ".join(cell(item) for item in row) + " |" for row in metric_rows(report)]
        rows += ["", "## NIST evidence crosswalk", "", report["standards"]["disclaimer"], "", "| Framework | Reference | Outcome | Evidence status |", "|---|---|---|---|"]
        rows += ["| " + " | ".join(cell(row[key]) for key in ("framework", "id", "name", "status")) + " |" for row in report["standards"]["rows"]]
        rows += ["", "## Actual resources", "", "| Resource | Limit | Used | Reserved |", "|---|---|---|---|"]
        rows += ["| " + " | ".join(cell(item) for item in row) + " |" for row in report["resource_rows"]]
        rows += ["", "## Gaps, errors and limitations", ""] + ["- " + x for x in report["limitations"]]
        rows += ["", "## Authoritative references", ""] + report["references"]
        rows += ["", "Report content fingerprint: " + report["content_hash"]]
        return "\n".join(rows)

    def html(self, report):
        return html_report(report)
