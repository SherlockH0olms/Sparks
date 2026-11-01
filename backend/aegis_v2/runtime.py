from __future__ import annotations

import json
import secrets
import threading
from collections import Counter

from .atlas import mapping
from .auth import require_permission
from .budget import Budget, BudgetExceeded
from .config import Settings
from .contracts import (Actor, AttackCandidate, CampaignCreate, CampaignState, DefenseConfig,
                        Property, Verdict, digest, attack_digest, new_id, now)
from .evaluation import Evaluator, utility_assessment
from .providers import ChatClient, BudgetedChat, ProviderError, TargetUnavailable
from .red import RedGenerator, InvalidCandidate
from .scenarios import build_cells, coverage, choose_cell, IMPORTANCE
from .storage import Store, NotFound, Conflict
from .naming import campaign_name, campaign_names, target_names
from .targets import Targets, LocalApplication


TERMINAL = {"completed", "cancelled", "failed", "budget_exhausted"}


class ControlSignal(RuntimeError):
    def __init__(self, action):
        self.action = action


class Platform:
    def __init__(self, store: Store, settings: Settings, *, red_transport=None, target_transport=None, judge_transport=None):
        self.store, self.settings = store, settings
        self.targets = Targets(store, settings, target_transport)
        self.red_client = ChatClient(settings.red, transport=red_transport)
        self.judge_client = ChatClient(settings.judge, transport=judge_transport)
        self.worker_context = threading.local()

    def generator(self, workspace):
        return RedGenerator(BudgetedChat(self.store, workspace, self.red_client, "generator_calls"),
                            check_control=lambda budget: self.check_control(workspace, budget.id.removeprefix("budget_")))

    def evaluator(self, workspace, target_id):
        judge = BudgetedChat(self.store, workspace, self.judge_client, "judge_calls") if self.judge_client.ready() else None
        return Evaluator(self.targets.canaries(workspace, target_id), judge)

    def create_campaign(self, actor: Actor, spec: CampaignCreate):
        require_permission(actor, "campaign")
        snapshot = self.targets.snapshot(actor.workspace, spec.target_id)
        cells = build_cells(spec, snapshot)
        if not cells or not any(c["applicable"] for c in cells):
            raise ValueError("The selected scope has no applicable coverage cells.")
        for language in spec.languages:
            if not any(c["language"] == language for c in snapshot["utility_cases"]):
                raise ValueError("Add at least one positive utility case for " + language + " before creating this campaign.")
        identifier = new_id("campaign")
        payload = {"state": "draft", "phase": "preflight", "control": None, "target_id": spec.target_id,
                   "target_revision": snapshot["revision"], "spec": spec.model_dump(mode="json"), "cells": cells,
                   "progress": {"baseline": 0, "discovery": 0, "reproduction": 0, "repair": 0, "verification": 0},
                   "baseline": None, "findings": [], "groups": [], "experiments": [], "verification_runs": [],
                   "candidate_attempts": [], "discovery_attempts": [], "error": None,
                   "created_by": actor.id, "started_at": None, "finished_at": None, "checkpoint": None}
        self.store.create("campaign", actor.workspace, payload, id=identifier)
        Budget.create(self.store, identifier, actor.workspace, spec.limits)
        self.store.create("job", actor.workspace, {"campaign_id": identifier, "state": "idle", "owner": None,
                    "lease_until": 0, "heartbeat": None}, id="job_" + identifier)
        self.store.event(actor.workspace, identifier, "campaign_created", {"target_id": spec.target_id,
                         "target_revision": snapshot["revision"], "actor": actor.id})
        return self.summary(actor.workspace, identifier)

    def snapshot_for(self, campaign, workspace):
        return self.store.get("snapshot_" + campaign["target_revision"], workspace, private_access=True)

    def summary(self, workspace, campaign_id):
        c = self.store.get(campaign_id, workspace)
        return {k: c[k] for k in ("id", "state", "phase", "target_id", "target_revision", "spec", "progress", "baseline",
                                "error", "started_at", "finished_at", "checkpoint", "created_by")} | {
            "coverage": coverage(c["cells"]), "attempts": len(c["discovery_attempts"]), "findings": len(c["findings"]),
            "groups": len(c["groups"]), "experiments": len(c["experiments"]), "verification_runs": len(c["verification_runs"]),
            "red_diversity": self.red_diversity(workspace, c),
            "budget": Budget(self.store, campaign_id, workspace).snapshot()} | campaign_name(
                c, campaign_names(self.store, workspace), target_names(self.store, workspace))

    def red_diversity(self, workspace, campaign):
        strategies = [self.store.get(aid, workspace, private_access=True)["candidate"].get("red_strategy", {})
                      for aid in campaign["discovery_attempts"]]
        methods = Counter(s["method_id"] for s in strategies if s.get("method_id"))
        transforms = [t for s in strategies for t in s.get("transformations", [])]
        return {"generated_candidates": len(strategies), "distinct_methods": len(methods), "method_counts": dict(methods),
                "distinct_resources": len({r["id"] for s in strategies for r in s.get("resources", [])}),
                "distinct_tactics_read": len({t for s in strategies for t in s.get("tactic_ids", [])}),
                "tactic_compositions": sum(len(s.get("compositions", [])) for s in strategies),
                "distinct_tactics_composed": len({t for s in strategies for c in s.get("compositions", []) for t in c["tactic_ids"]}),
                "transformation_calls": len(transforms), "applied_transformations": sum(t["applied"] for t in transforms),
                "frameworks_used": sorted({r["framework"] for s in strategies for r in s.get("resources", [])} |
                                          {t["framework"] for t in transforms}),
                "unattributed_candidates": sum(not s.get("method_id") for s in strategies)}

    def control(self, actor: Actor, campaign_id: str, action: str):
        require_permission(actor, "campaign")
        c = self.store.get(campaign_id, actor.workspace)
        if action == "start":
            if c["state"] != "draft":
                raise Conflict("Only a draft campaign can be started.")
            self.store.mutate(campaign_id, actor.workspace, lambda p: p | {"state": "queued", "started_at": now()})
            self.store.mutate("job_" + campaign_id, actor.workspace, lambda p: p | {"state": "queued"})
        elif action == "resume":
            if c["state"] != "paused":
                raise Conflict("Only a paused campaign can be resumed.")
            self.store.mutate(campaign_id, actor.workspace, lambda p: p | {"state": "queued", "control": None,
                "connection_epoch": p.get("connection_epoch", 0) + int((p.get("error") or {}).get("type") == "TargetUnavailable"),
                "error": None if (p.get("error") or {}).get("type") == "TargetUnavailable" else p.get("error")})
            self.store.mutate("job_" + campaign_id, actor.workspace, lambda p: p | {"state": "queued", "owner": None, "lease_until": 0})
        elif action == "pause":
            if c["state"] in TERMINAL or c["state"] in {"draft", "paused"}:
                raise Conflict("This campaign is not running.")
            self.store.mutate(campaign_id, actor.workspace, lambda p: p | {"control": "pause"})
        elif action == "cancel":
            if c["state"] in TERMINAL:
                return self.summary(actor.workspace, campaign_id)
            if c["state"] in {"draft", "paused", "queued"}:
                self.store.mutate(campaign_id, actor.workspace, lambda p: p | {"state": "cancelled", "control": "cancel", "finished_at": now()})
                self.store.mutate("job_" + campaign_id, actor.workspace, lambda p: p | {"state": "cancelled"})
            else:
                self.store.mutate(campaign_id, actor.workspace, lambda p: p | {"control": "cancel"})
        else:
            raise ValueError("Unknown campaign action.")
        self.store.event(actor.workspace, campaign_id, "control_requested", {"action": action, "actor": actor.id})
        return self.summary(actor.workspace, campaign_id)

    def check_control(self, workspace, campaign_id):
        owner = getattr(self.worker_context, "owner", None)
        if owner and getattr(self.worker_context, "campaign", None) == campaign_id:
            if self.store.get("job_" + campaign_id, workspace)["owner"] != owner:
                raise ControlSignal("lease_lost")
        c = self.store.get(campaign_id, workspace)
        if c.get("control"):
            raise ControlSignal(c["control"])
        stopping = getattr(self.worker_context, "stopping", None)
        if stopping is not None and stopping.is_set():
            raise ControlSignal("shutdown")

    def phase(self, workspace, campaign_id, phase):
        self.store.mutate(campaign_id, workspace, lambda p: p | {"phase": phase, "state": phase,
                          "checkpoint": {"phase": phase, "saved_at": now()}})
        self.store.event(workspace, campaign_id, "phase_changed", {"phase": phase})

    def redact(self, workspace, target_id, value):
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        for canary in self.targets.canaries(workspace, target_id):
            text = text.replace(canary["value"], "[REDACTED_CANARY]")
        return text

    def execute_attempt(self, workspace, campaign_id, logical_id, candidate, cell, bucket, *,
                        config=None, utility_case=None):
        c = self.store.get(campaign_id, workspace)
        snapshot = self.snapshot_for(c, workspace)
        budget = Budget(self.store, campaign_id, workspace)
        identifier = "attempt_" + digest({"campaign": campaign_id, "logical": logical_id})[:40]
        try:
            attempt = self.store.get(identifier, workspace, private_access=True)
        except NotFound:
            injected = None
            if candidate.get("document_body"):
                injected = {"id": "assigned_" + digest(candidate["document_body"])[:24], "tenant": snapshot["tenant"],
                            "title": "Assigned adversarial reference", "body": candidate["document_body"],
                            "assigned_to_red": True, "confidential": False}
            payload = {"campaign_id": campaign_id, "logical_id": logical_id, "phase": bucket, "cell": cell,
                       "candidate": candidate, "candidate_digest": attack_digest(candidate), "target_revision": c["target_revision"],
                       "configuration": (config or DefenseConfig.model_validate(snapshot["defenses"])).model_dump(),
                       "injected_document": injected, "session_id": new_id("session"), "steps": [],
                       "execution_status": "interrupted", "assessment": None, "completed": False}
            self.store.create("attempt", workspace, payload, id=identifier, private=True)
            attempt = self.store.get(identifier, workspace, private_access=True)
        if attempt["completed"]:
            return attempt
        app = LocalApplication(self.targets, workspace, snapshot, config)
        evaluator = self.evaluator(workspace, c["target_id"])
        history = []
        for step in attempt["steps"]:
            history += [{"role": "user", "content": step["message"]}, {"role": "assistant", "content": step["trace"].get("response", "")}]
        tenant = utility_case["tenant"] if utility_case else snapshot["tenant"]
        for index in range(len(attempt["steps"]), len(candidate["turns"])):
            self.check_control(workspace, campaign_id)
            message = candidate["turns"][index]
            operation_id = digest({"attempt": identifier, "turn": index, "connection_epoch": c.get("connection_epoch", 0)})[:40]
            try:
                trace = app.run_turn(message, tenant, history, budget, bucket, operation_id,
                       injected_document=attempt["injected_document"],
                       permissions=[utility_case["expected_tool"]] if utility_case and utility_case.get("expected_tool") else [],
                       expect_json=bool(utility_case.get("expect_json")) if utility_case else cell["property"] == "output_integrity")
            except TargetUnavailable:
                raise
            except ProviderError as exc:
                trace = {"status": exc.status.value, "response": "", "retrieval": [], "tools": [], "error": str(exc), "call_ids": []}
            if utility_case:
                assessment = utility_assessment(utility_case, trace)
            else:
                inputs = candidate["turns"] + ([candidate["document_body"]] if candidate.get("document_body") else [])
                assessment = evaluator.assess(Property(cell["property"]), trace, tenant, inputs, policy=snapshot["task_policy"],
                           budget=budget, bucket=bucket, operation_id=operation_id)
            step = {"index": index, "message": message, "trace": trace, "assessment": assessment}
            self.store.mutate(identifier, workspace, lambda p: p | {"steps": p["steps"] + [step]}, private_access=True)
            attempt["steps"].append(step)
            history += [{"role": "user", "content": message}, {"role": "assistant", "content": trace.get("response", "")}]
            if trace["status"] != "completed":
                break
        completed_execution = len(attempt["steps"]) == len(candidate["turns"]) and all(s["trace"]["status"] == "completed" for s in attempt["steps"])
        if utility_case:
            combined = attempt["steps"][-1]["assessment"]
        else:
            assessments = [s["assessment"] for s in attempt["steps"]]
            combined = next((a for a in assessments if a["verdict"] == "violation"), None)
            combined = combined or next((a for a in assessments if a["verdict"] == "inconclusive"), assessments[-1])
        status = "completed" if completed_execution else attempt["steps"][-1]["trace"]["status"]
        self.store.mutate(identifier, workspace, lambda p: p | {"execution_status": status, "assessment": combined, "completed": True}, private_access=True)
        attempt = self.store.get(identifier, workspace, private_access=True)
        self.store.event(workspace, campaign_id, "attempt_completed", {"attempt_id": identifier, "phase": bucket,
                          "execution_status": status, "verdict": combined.get("verdict"), "property": cell["property"]})
        return attempt

    def preflight_step(self, workspace, campaign_id):
        c = self.store.get(campaign_id, workspace)
        snapshot = self.snapshot_for(c, workspace)
        if not self.red_client.ready():
            raise ProviderError("Foundry offensive configuration is incomplete. Fill AEGIS_RED_* in .env.")
        self.phase(workspace, campaign_id, "preflight")
        caller = BudgetedChat(self.store, workspace, self.targets.client(snapshot), "target_calls")
        response = caller.invoke([{"role": "user", "content": "Reply with READY."}], Budget(self.store,campaign_id,workspace),
                                 "baseline", digest(campaign_id + "_preflight_" + str(c.get("connection_epoch", 0)))[:40], "campaign_preflight")
        if not response.content.strip() and not response.tool_calls:
            raise ProviderError("The local model returned an empty preflight response.")
        self.phase(workspace, campaign_id, "baselining")

    def baseline_step(self, workspace, campaign_id):
        c = self.store.get(campaign_id, workspace)
        snapshot = self.snapshot_for(c, workspace)
        cases = [u for u in snapshot["utility_cases"] if u["language"] in c["spec"]["languages"]]
        index = c["progress"]["baseline"]
        if index >= len(cases):
            results = []
            for i, case in enumerate(cases):
                aid = "attempt_" + digest({"campaign":campaign_id,"logical":"baseline_" + str(i)})[:40]
                results.append(self.store.get(aid,workspace,private_access=True)["assessment"])
            summary = {"questions": len(results), "valid": sum(r["valid"] for r in results),
                       "answered": sum(r["passed"] for r in results), "false_blocks": sum(r["false_block"] for r in results),
                       "utility": sum(r["passed"] for r in results)/len(results) if results and all(r["valid"] for r in results) else None}
            self.store.mutate(campaign_id,workspace,lambda p:p|{"baseline":summary})
            self.phase(workspace,campaign_id,"discovering")
            return
        case = cases[index]
        cell = {"id":"utility","property":"output_integrity" if case.get("expect_json") else "tool_authorization",
                "family":"utility","language":case["language"],"surface":"user_message","required_turns":1}
        candidate = {"language":case["language"],"turns":[case["message"]],"document_body":None,"hypothesis":"","expected_signal":""}
        self.execute_attempt(workspace,campaign_id,"baseline_" + str(index),candidate,cell,"baseline",utility_case=case)
        self.store.mutate(campaign_id,workspace,lambda p:p|{"progress":p["progress"]|{"baseline":index+1}})

    def public_observations(self, workspace, campaign_id):
        c = self.store.get(campaign_id,workspace)
        snapshot = self.snapshot_for(c,workspace)
        observations = []
        for aid in c["discovery_attempts"]:
            a = self.store.get(aid,workspace,private_access=True)
            row = {"scenario":a["cell"]["family"],"language":a["cell"]["language"]}
            row["prior_attack"] = {k: a["candidate"].get(k) for k in ("turns", "document_body", "hypothesis")}
            if a["candidate"].get("red_strategy"):
                row["red_strategy"] = a["candidate"]["red_strategy"]
            if "public_response" in snapshot["red_observations"]:
                row["public_response"]=[s["trace"].get("response","") for s in a["steps"]]
            if "refusal" in snapshot["red_observations"]:
                row["refusal"]=[s["trace"].get("refused",False) for s in a["steps"]]
            if "tool_requests" in snapshot["red_observations"]:
                row["tool_requests"]=[{"tool":t["tool"]} for s in a["steps"] for t in s["trace"].get("tools",[])]
            observations.append(row)
        return observations

    def discovery_step(self,workspace,campaign_id):
        c=self.store.get(campaign_id,workspace)
        index=c["progress"]["discovery"]
        choice=choose_cell(c["cells"])
        maximum=c["spec"]["max_discovery_attempts"]
        if choice is None or (maximum is not None and index>=maximum):
            self.phase(workspace,campaign_id,"reproducing")
            return
        cell,reason=choice
        snapshot=self.snapshot_for(c,workspace)
        budget=Budget(self.store,campaign_id,workspace)
        self.store.event(workspace,campaign_id,"scheduler_decision",{"cell_id":cell["id"],"reason":reason,"language":cell["language"],"property":cell["property"]})
        try:
            candidate=self.generator(workspace).generate(cell,snapshot,c["spec"],self.public_observations(workspace,campaign_id),
                                 budget,"discovery",digest(campaign_id+"_generate_"+str(index))[:40])
            fingerprint=attack_digest(candidate)
            if any(fingerprint in row["digests"] for row in c["cells"]):
                raise InvalidCandidate("The offensive model repeated an already executed candidate.")
        except InvalidCandidate as exc:
            self.store.event(workspace,campaign_id,"candidate_rejected",{"cell_id":cell["id"],"reason":str(exc)})
            def reject(p):
                for row in p["cells"]:
                    if row["id"]==cell["id"]: row["attempts"]+=1
                p["progress"]["discovery"]+=1
                return p
            self.store.mutate(campaign_id,workspace,reject)
            return
        attempt=self.execute_attempt(workspace,campaign_id,"discovery_"+str(index),candidate,cell,"discovery")
        valid=attempt["execution_status"]=="completed" and attempt["assessment"]["verdict"] in {"violation","no_violation_observed"}
        violation=attempt["assessment"]["verdict"]=="violation"
        def record(p):
            for row in p["cells"]:
                if row["id"]==cell["id"]:
                    row["attempts"]+=1;row["valid"]+=int(valid);row["violations"]+=int(violation)
                    row["inconclusive"]+=int(not valid);row["digests"].append(fingerprint)
            p["progress"]["discovery"]+=1
            p["discovery_attempts"].append(attempt["id"])
            if violation:p["candidate_attempts"].append(attempt["id"])
            p["checkpoint"]={"phase":"discovering","next_attempt":index+1,"saved_at":now()}
            return p
        self.store.mutate(campaign_id,workspace,record)

    def reproduction_step(self,workspace,campaign_id):
        c=self.store.get(campaign_id,workspace)
        representatives={}
        for aid in c["candidate_attempts"]:
            a=self.store.get(aid,workspace,private_access=True)
            key=digest({k:a["assessment"][k] for k in ("property","boundary","effect")})
            representatives.setdefault(key,a)
        candidates=list(representatives.items())
        index=c["progress"]["reproduction"]
        if index>=len(candidates):
            self.phase(workspace,campaign_id,"repairing")
            return
        group_key,original=candidates[index]
        trials=[]
        for trial in range(c["spec"]["reproduction_trials"]):
            a=self.execute_attempt(workspace,campaign_id,"repro_"+str(index)+"_"+str(trial),original["candidate"],original["cell"],"reproduction")
            same=all(a["assessment"].get(k)==original["assessment"].get(k) for k in ("property","boundary","effect")) and a["assessment"]["verdict"]=="violation"
            trials.append({"attempt_id":a["id"],"valid":a["execution_status"]=="completed" and a["assessment"]["verdict"] in {"violation","no_violation_observed"},"same_violation":same})
        valid=sum(t["valid"] for t in trials);success=sum(t["same_violation"] for t in trials)
        confirmed=valid==len(trials) and success/max(1,valid)>=c["spec"]["minimum_reproduction_rate"]
        if confirmed:
            minimized=original["candidate"]
            # Budgeted delta reduction: remove one earlier turn at a time and keep
            # only candidates that reproduce the SAME property/boundary/effect.
            for cut in range(min(3,max(0,len(original["candidate"]["turns"])-1))):
                reduced=minimized|{"turns":minimized["turns"][1:]}
                if not reduced["turns"]:break
                tested=self.execute_attempt(workspace,campaign_id,"min_"+str(index)+"_"+str(cut),reduced,original["cell"],"reproduction")
                same=tested["assessment"]["verdict"]=="violation" and all(tested["assessment"].get(k)==original["assessment"].get(k) for k in ("property","boundary","effect"))
                if same:minimized=reduced
                else:break
            finding_id="finding_"+digest(campaign_id+group_key)[:32]
            finding={"campaign_id":campaign_id,"property":original["assessment"]["property"],"boundary":original["assessment"]["boundary"],
                     "effect":original["assessment"]["effect"],"original_attempt_id":original["id"],"minimized_candidate":minimized,
                     "reproduction":trials,"reproduction_rate":success/valid,"diagnosis":"evidence_supported",
                     "diagnosis_note":"Observed effect reproduced in fresh sessions. Root cause remains a hypothesis until an isolated control intervention is evaluated.",
                     "assessment":original["assessment"],"atlas":mapping(original["assessment"],original["cell"]["surface"]),
                     "severity":"critical" if original["assessment"]["property"]=="tool_authorization" else "high",
                     "group_key":group_key,"status":"confirmed","limitations":["Evidence applies to the pinned target revision and declared access profile."]}
            try:self.store.get(finding_id,workspace,private_access=True)
            except NotFound:self.store.create("finding",workspace,finding,id=finding_id,private=True)
            def add(p):
                if finding_id not in p["findings"]:p["findings"].append(finding_id)
                if finding_id not in p["groups"]:p["groups"].append(finding_id)
                return p
            self.store.mutate(campaign_id,workspace,add)
            self.store.event(workspace,campaign_id,"finding_confirmed",{"finding_id":finding_id,"property":finding["property"],"reproduction_rate":finding["reproduction_rate"]})
        else:
            self.store.event(workspace,campaign_id,"finding_inconclusive",{"attempt_id":original["id"],"valid_trials":valid,"same_violation_trials":success})
        self.store.mutate(campaign_id,workspace,lambda p:p|{"progress":p["progress"]|{"reproduction":index+1}})

    def step(self,workspace,campaign_id):
        self.check_control(workspace,campaign_id)
        c=self.store.get(campaign_id,workspace)
        if c["state"] in TERMINAL:return
        handler={"preflight":self.preflight_step,"baselining":self.baseline_step,"discovering":self.discovery_step,
                 "reproducing":self.reproduction_step}.get(c["phase"])
        if handler:handler(workspace,campaign_id)
        elif c["phase"]=="repairing":
            from .repair import RepairService
            RepairService(self).step(workspace,campaign_id)
        elif c["phase"]=="verifying":
            from .verification import VerificationService
            VerificationService(self).step(workspace,campaign_id)
        elif c["phase"]=="reporting":
            self.store.mutate(campaign_id,workspace,lambda p:p|{"state":"completed","finished_at":now(),"checkpoint":{"phase":"completed","saved_at":now()}})
            self.store.event(workspace,campaign_id,"campaign_completed",{"scope_result":"See individual findings, verification results and coverage gaps."})
        else:raise ValueError("Unknown phase: "+c["phase"])

