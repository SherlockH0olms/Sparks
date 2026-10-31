"""AEGIS LOOP Control API (FastAPI).

Güvenlik kuralları:
* Yalnızca kayıtlı hedefler çalıştırılabilir (target inventory).
* Red süreçleri oracle vault'un evaluator yüzeyine erişemez.
* Saldırı içerikleri güvenilmeyen veridir: API yanıtlarında redakte edilir,
  HTML render frontend'de kaçınılmaz.
* Başlatma işlemleri idempotency key ister.
"""
from __future__ import annotations

import asyncio
import threading
import time
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from aegis.contracts.models import (
    ActorRole,
    BudgetLimits,
    CampaignSpec,
    PolicyBundle,
    RevisionTriple,
)
from aegis.core.events import EventBus, EventKind
from aegis.engine import CampaignEngine
from aegis.evaluation.evaluator import IndependentEvaluator
from aegis.evaluation.oracle_vault import OracleVault
from aegis.reporting.report import ReportGenerator
from aegis.targets.synthetic_assistant import build_manifest


app = FastAPI(title="AEGIS LOOP Control API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -- tekil kaynaklar -------------------------------------------------------------

bus = EventBus()
vault = OracleVault()
evaluator = IndependentEvaluator(vault)
reporter = ReportGenerator()

TARGET_INVENTORY: dict[str, Any] = {}
MANIFEST = build_manifest()
TARGET_INVENTORY[MANIFEST.target_id] = MANIFEST

POLICY = PolicyBundle(
    policy_revision="policy-2026-10-31",
    allowed_response_fields=["public_response", "retrieval_summary"],
    allowed_tools=["email.send", "doc.export"],
    canaries={
        "canary_gateway_key": "Staging gateway anahtarı (kanarya)",
        "canary_codename": "İç kod adı (kanarya)",
        "canary_budget": "Bütçe zarfı (kanarya)",
    },
)

engines: dict[str, CampaignEngine] = {}
idempotency_keys: set[str] = set()
audit_log: list[dict] = []
_kill_all = threading.Event()


def audit(action: str, detail: dict) -> None:
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "action": action,
        "detail": detail,
    }
    audit_log.append(entry)
    bus.publish(EventKind.AUDIT, detail.get("campaign_id", "system"), entry)


# -- modeller ---------------------------------------------------------------------


class CampaignCreate(BaseModel):
    target_id: str
    languages: list[str] = Field(default_factory=lambda: ["tr", "az", "en"])
    budget: BudgetLimits = Field(default_factory=BudgetLimits)
    max_attempts: int | None = None


class ActionResponse(BaseModel):
    ok: bool
    campaign_id: str
    message: str = ""


# -- yardımcılar -------------------------------------------------------------------


def require_engine(campaign_id: str) -> CampaignEngine:
    eng = engines.get(campaign_id)
    if eng is None:
        raise HTTPException(status_code=404, detail="kampanya bulunamadı")
    return eng


def redact(text: str, keep: int = 200) -> str:
    """Saldırı/yanıt metinlerini güvenilmeyen veri olarak kırp."""
    if not text:
        return ""
    return text[:keep] + ("…" if len(text) > keep else "")


# -- sağlık ------------------------------------------------------------------------


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": "1.0.0",
        "targets": list(TARGET_INVENTORY.keys()),
        "campaigns": len(engines),
        "kill_switch": _kill_all.is_set(),
    }


# -- hedefler ------------------------------------------------------------------------


@app.get("/api/targets")
def list_targets() -> list[dict]:
    out = []
    for t in TARGET_INVENTORY.values():
        out.append(
            {
                "target_id": t.target_id,
                "display_name": t.display_name,
                "profile": t.profile,
                "revisions": t.revisions.model_dump(),
                "capabilities": t.capabilities,
                "red_writable_surfaces": t.red_writable_surfaces,
                "red_observations": t.red_observations,
                "environment": t.environment.model_dump(),
                "documents": [
                    {"doc_id": d.doc_id, "tenant": d.tenant, "title": d.title}
                    for d in t.documents
                ],
            }
        )
    return out


@app.get("/api/targets/{target_id}/manifest")
def get_manifest(target_id: str) -> dict:
    if target_id not in TARGET_INVENTORY:
        raise HTTPException(404, "hedef kayıtlı değil")
    return TARGET_INVENTORY[target_id].model_dump()


# -- kampanyalar ----------------------------------------------------------------------


@app.post("/api/campaigns")
def create_campaign(
    body: CampaignCreate,
    x_idempotency_key: str = Header(default="", alias="Idempotency-Key"),
) -> dict:
    if not x_idempotency_key:
        raise HTTPException(400, "Idempotency-Key başlığı zorunlu")
    if x_idempotency_key in idempotency_keys:
        raise HTTPException(409, "bu idempotency key ile işlem zaten yapıldı")
    idempotency_keys.add(x_idempotency_key)

    if body.target_id not in TARGET_INVENTORY:
        raise HTTPException(404, f"hedef kayıtlı değil: {body.target_id}")
    if _kill_all.is_set():
        raise HTTPException(503, "kill switch aktif; yeni kampanya başlatılamaz")

    manifest = TARGET_INVENTORY[body.target_id]
    spec = CampaignSpec(
        target_id=body.target_id,
        revisions=manifest.revisions.model_copy(deep=True),
        budget=body.budget,
        languages=body.languages,
    )
    eng = CampaignEngine(spec, manifest, POLICY, bus)
    eng.attach_evaluator(vault, evaluator)
    engines[spec.campaign_id] = eng
    bus.publish(
        EventKind.CAMPAIGN_CREATED,
        spec.campaign_id,
        {"target": body.target_id, "languages": body.languages},
    )
    audit("campaign_created", {"campaign_id": spec.campaign_id, "target": body.target_id})
    return {"campaign_id": spec.campaign_id, "state": eng.campaign.state.value}


def _run_engine(eng: CampaignEngine, max_attempts: int | None) -> None:
    try:
        eng.run(max_attempts=max_attempts)
    except Exception as exc:  # altyapı hatası güvenlik sonucu değil
        bus.publish(
            EventKind.WORKER_LOST,
            eng.spec.campaign_id,
            {"error": str(exc)[:200]},
        )


@app.post("/api/campaigns/{campaign_id}/start")
def start_campaign(
    campaign_id: str,
    background: bool = Query(default=True),
    x_idempotency_key: str = Header(default="", alias="Idempotency-Key"),
) -> ActionResponse:
    eng = require_engine(campaign_id)
    if eng.campaign.state.value not in ("draft",):
        raise HTTPException(409, f"kampanya {eng.campaign.state.value} durumunda başlatılamaz")
    if not x_idempotency_key:
        raise HTTPException(400, "Idempotency-Key başlığı zorunlu")
    if x_idempotency_key in idempotency_keys:
        raise HTTPException(409, "işlem zaten yapıldı")
    idempotency_keys.add(x_idempotency_key)

    audit("campaign_started", {"campaign_id": campaign_id})
    max_attempts = None
    if background:
        t = threading.Thread(target=_run_engine, args=(eng, max_attempts), daemon=True)
        t.start()
        return ActionResponse(ok=True, campaign_id=campaign_id, message="arka planda başlatıldı")
    eng.run(max_attempts=max_attempts)
    return ActionResponse(ok=True, campaign_id=campaign_id, message="tamamlandı")


@app.post("/api/campaigns/{campaign_id}/pause")
def pause_campaign(campaign_id: str) -> ActionResponse:
    eng = require_engine(campaign_id)
    eng.request_pause()
    audit("campaign_paused", {"campaign_id": campaign_id})
    return ActionResponse(ok=True, campaign_id=campaign_id, message="pause istendi")


@app.post("/api/campaigns/{campaign_id}/resume")
def resume_campaign(campaign_id: str) -> ActionResponse:
    eng = require_engine(campaign_id)
    eng.request_resume()
    audit("campaign_resumed", {"campaign_id": campaign_id})
    return ActionResponse(ok=True, campaign_id=campaign_id, message="resume istendi")


@app.post("/api/campaigns/{campaign_id}/cancel")
def cancel_campaign(campaign_id: str) -> ActionResponse:
    eng = require_engine(campaign_id)
    eng.request_cancel()
    audit("campaign_cancelled", {"campaign_id": campaign_id})
    return ActionResponse(ok=True, campaign_id=campaign_id, message="cancel istendi")


@app.get("/api/campaigns")
def list_campaigns() -> list[dict]:
    return [
        {
            "campaign_id": cid,
            "state": e.campaign.state.value,
            "target": e.spec.target_id,
            "attempts": len(e.campaign.attempts),
            "findings": len(e.campaign.findings),
            "created": e.spec.created_at,
        }
        for cid, e in engines.items()
    ]


@app.get("/api/campaigns/{campaign_id}")
def campaign_detail(campaign_id: str) -> dict:
    eng = require_engine(campaign_id)
    return eng.summary()


@app.get("/api/campaigns/{campaign_id}/coverage")
def campaign_coverage(campaign_id: str) -> dict:
    eng = require_engine(campaign_id)
    return {
        "metrics": eng.grid.coverage_metrics(),
        "cells": eng.grid.snapshot_rows(),
    }


@app.get("/api/campaigns/{campaign_id}/attempts")
def campaign_attempts(campaign_id: str, limit: int = 50) -> list[dict]:
    eng = require_engine(campaign_id)
    out = []
    for a in eng.campaign.attempts[-limit:]:
        out.append(
            {
                "attempt_id": a.attempt_id,
                "strategy": a.strategy_id,
                "language": a.language,
                "cell": a.cell.as_tuple(),
                "execution_status": a.execution_status.value if a.execution_status else None,
                "verdict": a.verdict.value if a.verdict else None,
                "turns_preview": [redact(t, 80) for t in a.turns],
                "response_preview": redact(a.response, 120),
                "wall_ms": a.wall_ms,
                "ts": a.ts,
            }
        )
    return out


@app.get("/api/campaigns/{campaign_id}/findings")
def campaign_findings(campaign_id: str) -> list[dict]:
    eng = require_engine(campaign_id)
    out = []
    for f in eng.campaign.findings:
        out.append(
            {
                "finding_id": f.finding_id,
                "group_id": f.group_id,
                "violated_property": f.violated_property.value,
                "boundary": f.boundary,
                "component": f.component,
                "observed_effect": redact(f.observed_effect, 160),
                "severity": f.severity,
                "reproduction_rate": f.reproduction_rate,
                "diagnosis": f.diagnosis.value,
                "atlas": f.atlas_mapping,
                "minimized_turns": [redact(t, 100) for t in f.minimized_turns],
                "original_attempt_id": f.original_attempt_id,
                "limitations": f.limitations,
            }
        )
    return out


@app.get("/api/campaigns/{campaign_id}/findings/{finding_id}")
def finding_detail(campaign_id: str, finding_id: str) -> dict:
    eng = require_engine(campaign_id)
    for f in eng.campaign.findings:
        if f.finding_id == finding_id:
            att = next(
                (a for a in eng.campaign.attempts if a.attempt_id == f.original_attempt_id),
                None,
            )
            return {
                **f.model_dump(),
                "original_attempt": (
                    {
                        "turns": [redact(t, 140) for t in att.turns],
                        "response": redact(att.response, 300),
                        "execution_status": att.execution_status.value if att.execution_status else None,
                        "verdict": att.verdict.value if att.verdict else None,
                    }
                    if att
                    else None
                ),
            }
    raise HTTPException(404, "bulgu bulunamadı")


@app.get("/api/campaigns/{campaign_id}/repair")
def campaign_repair(campaign_id: str) -> list[dict]:
    eng = require_engine(campaign_id)
    return [eng.repair_lab.compare(exp) if eng.repair_lab else {} for exp in eng.experiments]


@app.get("/api/campaigns/{campaign_id}/verification")
def campaign_verification(campaign_id: str) -> list[dict]:
    eng = require_engine(campaign_id)
    return [v.model_dump() for v in eng.verification_runs]


@app.get("/api/campaigns/{campaign_id}/budget")
def campaign_budget(campaign_id: str) -> dict:
    eng = require_engine(campaign_id)
    return eng.ledger.snapshot()


# -- kanıt paketi ve rapor --------------------------------------------------------------


@app.get("/api/campaigns/{campaign_id}/evidence-pack")
def evidence_pack(campaign_id: str) -> dict:
    eng = require_engine(campaign_id)
    pack = reporter.build_evidence_pack(
        eng.campaign, eng.manifest, POLICY, eng.experiments, eng.verification_runs
    )
    return pack.model_dump()


@app.get("/api/campaigns/{campaign_id}/report")
def campaign_report(campaign_id: str, format: str = Query(default="markdown")) -> Any:
    eng = require_engine(campaign_id)
    atlas_rows: list[dict] = []
    for f in eng.campaign.findings:
        atlas_rows.extend(f.atlas_mapping)
    md = reporter.markdown(
        eng.campaign,
        eng.grid.coverage_metrics(),
        eng.groups,
        eng.experiments,
        eng.verification_runs,
        atlas_rows,
    )
    if format == "html":
        return JSONResponse({"html": reporter.html(md)})
    if format == "raw":
        return JSONResponse({"markdown": md})
    return JSONResponse({"markdown": md, "html": reporter.html(md)})


# -- olaylar (SSE) ------------------------------------------------------------------------


@app.get("/api/campaigns/{campaign_id}/events")
async def campaign_events(campaign_id: str, after_seq: int = 0) -> StreamingResponse:
    require_engine(campaign_id)
    queue: asyncio.Queue = asyncio.Queue()

    def on_event(rec) -> None:
        queue.put_nowait(rec)

    unsub = bus.subscribe(campaign_id, on_event)

    async def stream():
        try:
            for rec in bus.history(campaign_id, after_seq=after_seq):
                yield f"data: {rec.to_json().__repr__()}\n\n".replace("'", '"')
            yield ": keepalive\n\n"
            while True:
                try:
                    rec = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {rec.to_json().__repr__()}\n\n".replace("'", '"')
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            unsub()

    return StreamingResponse(stream(), media_type="text/event-stream")


# -- oracle vault (rol bazlı) ----------------------------------------------------------------


@app.get("/api/vault/canaries")
def list_canaries(role: str = "analyst") -> Any:
    try:
        actor_role = ActorRole(role)
    except ValueError:
        raise HTTPException(400, "geçersiz rol")
    try:
        return vault.list_canaries(actor_role)
    except Exception as exc:
        raise HTTPException(403, str(exc))


# -- audit ve kill switch ---------------------------------------------------------------------


@app.get("/api/audit")
def get_audit(limit: int = 100) -> list[dict]:
    return audit_log[-limit:]


@app.post("/api/system/kill-switch")
def kill_switch() -> dict:
    _kill_all.set()
    for cid, eng in engines.items():
        eng.request_cancel()
    audit("kill_switch", {"campaigns": list(engines.keys())})
    bus.publish(EventKind.KILL_SWITCH, "system", {"active": True})
    return {"ok": True, "cancelled": list(engines.keys())}
