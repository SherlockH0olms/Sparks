from __future__ import annotations

import html
import json
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
        attempts=store.list("attempt",workspace,parent=campaign_id,limit=1000,private_access=True)
        # Export all execution and assessment records, including failed calls.
        calls=store.list("call",workspace,parent=campaign_id,limit=1000,private_access=True)
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
            pack["final_protocols"]=[f for f in store.list("final",workspace,parent=campaign_id,limit=100,private_access=True) if f["state"]=="closed"]
        if sensitive:
            pack["target_snapshot"]=self.p.snapshot_for(c,workspace)
            pack["oracle"]=self.p.targets.canaries(workspace,c["target_id"])
        else:
            pack=json.loads(self.p.redact(workspace,c["target_id"],pack))
            for experiment in pack["experiments"]:
                for candidate in experiment["candidates"]:
                    candidate["artifact"].pop("path",None)
        pack["content_hash"]=digest(pack)
        return pack

    def markdown(self, workspace, campaign_id):
        c=self.p.store.get(campaign_id,workspace);summary=self.p.summary(workspace,campaign_id)
        rows=["# AEGIS LOOP security experiment","",
              "**Campaign:** "+campaign_id,"**State:** "+c["state"],"**Target revision:** "+c["target_revision"],"",
              "Completion describes workflow progress. The measured scope, uncertainties and individual candidate verdicts follow.","",
              "## Scope","",f"Applicable cells: {summary['coverage']['applicable']}. Completed: {summary['coverage']['completed']}. Coverage: {summary['coverage']['coverage_pct']}.",
              f"Discovery attempts: {summary['attempts']}. Confirmed defect groups: {summary['groups']}.","",
              "## Findings",""]
        for fid in c["findings"]:
            finding=self.p.store.get(fid,workspace,private_access=True)
            rows += ["### "+finding["property"],"","Boundary: "+finding["boundary"],"Effect: "+finding["effect"],
                     "Fresh-session reproduction: "+str(finding["reproduction_rate"]),"Diagnosis: "+finding["diagnosis"],
                     "ATLAS: "+str(finding["atlas"].get("technique_id") or "unmapped")+" — "+finding["atlas"]["name"],""]
        rows += ["## Paired baseline and candidate verification","","| Run | Suite | Baseline ASR / utility | Candidate ASR / utility | Candidate status |",
                 "|---|---|---|---|---|"]
        for vid in c["verification_runs"]:
            result=self.p.store.get(vid,workspace)
            for suite in ("replay","unseen","adaptive","utility"):
                base=result["suites"]["baseline"][suite];candidate=result["suites"]["candidate"][suite]
                metric="utility" if suite=="utility" else "asr"
                rows.append(f"| {vid} | {suite} | {base.get(metric)} | {candidate.get(metric)} | {candidate['status']} |")
            rows += ["","Final verdict: **"+result["verdict"]+"**. Protocol: "+result["protocol_revision"]+". Test revision: "+str(result["set_revision"])+".",""]
        rows += ["## Actual resources","","| Resource | Limit | Used | Reserved |","|---|---|---|---|"]
        budget=summary["budget"]
        for resource in budget["limits"]:
            rows.append(f"| {resource} | {budget['limits'][resource]} | {budget['used'][resource]} | {budget['reserved'][resource]} |")
        rows += ["","## Gaps, errors and limitations","",
                 "Uncompleted applicable cells: "+str(summary["coverage"]["applicable"]-summary["coverage"]["completed"]),
                 "No evaluable observations, infrastructure failures and missing semantic judges cannot establish defense success.",
                 "Adaptive pairs use candidate feedback; their rates are descriptive and do not imply unbiased population estimates.",
                 "Validation applies only to the frozen target, declared access profile, exact datasets and budget.",
                 "Raw operator evidence contains confidential test data and is available only to an administrator after the experiment closes."]
        if c["error"]:rows += ["","Workflow error: "+str(c["error"])]
        return self.p.redact(workspace,c["target_id"],"\n".join(rows))

    def html(self, markdown):
        # Evidence is plain escaped text. No remote resources, scripts or links.
        return "<!doctype html><html lang='en'><meta charset='utf-8'><title>AEGIS LOOP report</title><style>body{max-width:1100px;margin:40px auto;background:#0b1220;color:#e2e8f0;font:15px system-ui;padding:20px}pre{white-space:pre-wrap;line-height:1.65}</style><body><pre>"+html.escape(markdown)+"</pre></body></html>"

