from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from .auth import Auth, require_permission
from .budget import Budget, BudgetExceeded
from .config import Settings
from .contracts import Actor, CampaignCreate, Role, TargetCreate, digest, now
from .providers import ProviderError
from .red_library import installed_library, LibraryError
from .reporting import Reporting
from .runtime import Platform, TERMINAL
from .scenarios import coverage, target_template
from .storage import Store, Conflict, NotFound, PrivateAccess
from .workers import Workers
from .defenses import CONTROLS
from .defense_tools import available, tool_catalog
from .scenarios import build_cells


class LoginBody(BaseModel):
    key: str = Field(min_length=1, max_length=1000, repr=False)


class UserCreate(BaseModel):
    name: str = Field(min_length=1,max_length=100)
    role: Role
    workspace: str = Field(default="default",min_length=1,max_length=100,pattern=r"^[a-zA-Z0-9_-]+$")


class KillBody(BaseModel):
    active: bool


def create_app(settings: Settings | None = None, *, platform: Platform | None = None, start_workers=True):
    settings=settings or Settings.load()
    owns_store=platform is None
    if platform is None:
        platform=Platform(Store(settings.database_url,settings.vault_key,settings.runtime_dir),settings)
    auth=Auth(platform.store,settings.admin_token,settings.session_hours)
    workers=Workers(platform)
    reporting=Reporting(platform)
    limits=defaultdict(deque)

    @asynccontextmanager
    async def lifespan(app):
        if start_workers:workers.start()
        yield
        workers.close()
        if owns_store:platform.store.close()

    app=FastAPI(title="AEGIS LOOP",version="2.0.0",lifespan=lifespan)
    app.state.platform=platform;app.state.workers=workers;app.state.auth=auth
    app.add_middleware(CORSMiddleware,allow_origins=list(settings.allowed_origins),
                       allow_credentials=True,allow_methods=["GET","POST"],allow_headers=["Content-Type","Authorization","Idempotency-Key"])

    def actor(request: Request):
        origin=request.headers.get("origin")
        if request.method not in {"GET","HEAD","OPTIONS"} and origin and origin not in settings.allowed_origins:
            raise HTTPException(403,"Request origin is not allowed.")
        bearer=request.headers.get("authorization","")
        try:
            if bearer.startswith("Bearer "):return auth.authenticate_key(bearer[7:])
            token=request.cookies.get("aegis_session","")
            if token:return auth.session_actor(token)
            raise PermissionError("Authentication is required.")
        except PermissionError as exc:
            raise HTTPException(401,str(exc)) from None

    def throttle(who: Actor):
        q=limits[who.id];current=time.monotonic()
        while q and q[0] < current-60:q.popleft()
        if len(q)>=30:raise HTTPException(429,"Control request rate limit reached; retry shortly.")
        q.append(current)

    def camp(cid,who):
        return platform.store.get(cid,who.workspace)

    def safe(who,target_id,value):
        return json.loads(platform.redact(who.workspace,target_id,value))

    def budget_view(value):
        return {k:v for k,v in value.items() if k not in {"operations","_version","_created"}}

    @app.exception_handler(NotFound)
    async def not_found(_,exc):return JSONResponse({"detail":"Resource not found in your workspace."},status_code=404)
    @app.exception_handler(Conflict)
    async def conflict(_,exc):return JSONResponse({"detail":str(exc)},status_code=409)
    @app.exception_handler(BudgetExceeded)
    async def budget_exceeded(_,exc):return JSONResponse({"detail":str(exc)},status_code=409)
    @app.exception_handler(PrivateAccess)
    async def private(_,exc):return JSONResponse({"detail":"Evaluator-only record is not available to this role."},status_code=403)
    @app.exception_handler(PermissionError)
    async def forbidden(_,exc):return JSONResponse({"detail":str(exc)},status_code=403)
    @app.exception_handler(ProviderError)
    async def provider_error(_,exc):return JSONResponse({"detail":str(exc),"execution_status":exc.status.value},status_code=502)
    @app.exception_handler(ValueError)
    async def invalid(_,exc):return JSONResponse({"detail":str(exc)},status_code=422)

    @app.get("/api/health")
    def health():
        return {"status":"ok","version":"2.0.0","auth_configured":len(settings.admin_token)>=32,
                "red":settings.red.public(),"judge":settings.judge.public(),
                "red_attack_library":installed_library().summary(),
                "local_defaults":{"endpoint":settings.local_endpoint,"model":settings.local_model},
                "workers":workers.status(),"server_time":now(),
                "fixture_environment":platform.red_client.provenance=="fixture",
                "configuration_notice":None if len(settings.admin_token)>=32 else "Set AEGIS_ADMIN_TOKEN to at least 32 random characters in .env."}

    @app.post("/api/auth/login")
    def login(body: LoginBody,request: Request,response: Response):
        origin=request.headers.get("origin")
        if origin and origin not in settings.allowed_origins:raise HTTPException(403,"Request origin is not allowed.")
        if len(settings.admin_token) < 32 and not platform.store.list("user","default"):
            raise HTTPException(503,"Platform access is not configured. Fill AEGIS_ADMIN_TOKEN in .env.")
        try:token,who=auth.login(body.key)
        except PermissionError as exc:raise HTTPException(401,str(exc)) from None
        response.set_cookie("aegis_session",token,httponly=True,secure=settings.cookie_secure,
                            samesite="strict",max_age=settings.session_hours*3600,path="/")
        platform.store.event(who.workspace,"system","session_started",{"actor":who.id})
        return who.model_dump(mode="json")

    @app.get("/api/red/library")
    def red_library(who: Actor=Depends(actor)):
        return installed_library().list_methods()

    @app.get("/api/red/library/sources")
    def red_sources(who: Actor=Depends(actor)):
        return installed_library().sources()

    @app.get("/api/red/library/resources")
    def red_resources(query: str="", framework: str | None=None, kind: str | None=None,
                      offset: int=Query(0,ge=0), limit: int=Query(10,ge=1,le=50), who: Actor=Depends(actor)):
        try:
            return installed_library().search(query=query, framework=framework, kind=kind, offset=offset, limit=limit)
        except LibraryError as exc:
            raise HTTPException(400,str(exc)) from None

    @app.get("/api/red/library/resource/{resource_id}")
    def red_resource(resource_id: str, who: Actor=Depends(actor)):
        try:
            return installed_library().get_resource(resource_id)
        except LibraryError as exc:
            raise HTTPException(404,str(exc)) from None

    @app.post("/api/auth/logout")
    def logout(request: Request,response: Response,who: Actor=Depends(actor)):
        auth.logout(request.cookies.get("aegis_session",""))
        response.delete_cookie("aegis_session",path="/")
        return {"ok":True}

    @app.get("/api/auth/me")
    def me(who: Actor=Depends(actor)):return who.model_dump(mode="json")

    @app.get("/api/setup/target-template")
    def template(who: Actor=Depends(actor)):
        require_permission(who,"target")
        return target_template(settings.local_endpoint,settings.local_model)

    @app.get("/api/repair/catalog")
    def defense_catalog(who: Actor=Depends(actor)):
        return {"controls": [{"id": key, **value, "available": available(value["tool"])} for key, value in CONTROLS.items()],
                "tools": tool_catalog().get("tools", []),
                "references_only": [{"name": "NeMo Guardrails", "url": "https://github.com/NVIDIA/NeMo-Guardrails"},
                                    {"name": "LLM Guard", "url": "https://github.com/protectai/llm-guard"}]}

    @app.post("/api/campaigns/estimate")
    def estimate(body: CampaignCreate, who: Actor=Depends(actor)):
        snapshot = platform.targets.snapshot(who.workspace, body.target_id)
        cells = [cell for cell in build_cells(body, snapshot) if cell["applicable"]]
        by_property = {str(prop): sum(c["property"] == prop for c in cells) for prop in body.properties}
        return {"applicable_cells": len(cells), "cells_per_property": by_property,
                "minimum_discovery_tests": len(cells) * body.minimum_tests_per_cell,
                "development_fresh_per_property": {key: count * body.development_fresh_cases for key, count in by_property.items()},
                "final_pairs_per_property": {key: (count if body.verification_scope == "property" else 1) *
                    (body.final_cases_per_property + body.adaptive_attempts) for key, count in by_property.items()},
                "notice": "Final counts are per selected finding group and exclude replay and utility. Each pair tests baseline and candidate; tool-reading calls and multiple turns add calls. This is a protocol count, not a runtime prediction."}

    @app.get("/api/targets")
    def list_targets(limit: int=Query(100,ge=1,le=200),offset: int=Query(0,ge=0),who: Actor=Depends(actor)):
        return platform.store.list("target",who.workspace,limit=limit,offset=offset)

    @app.post("/api/targets",status_code=201)
    def create_target(body: TargetCreate,who: Actor=Depends(actor),key: str=Header("",alias="Idempotency-Key")):
        require_permission(who,"target");throttle(who)
        return platform.store.once(who.workspace,"target",key,body.model_dump(mode="json"),
                                   lambda:platform.targets.create(who.workspace,body,who.id))

    @app.get("/api/targets/{target_id}")
    def get_target(target_id: str,who: Actor=Depends(actor)):
        return platform.store.get(target_id,who.workspace)

    @app.post("/api/targets/{target_id}/preflight")
    def preflight(target_id: str,who: Actor=Depends(actor)):
        require_permission(who,"target");throttle(who)
        result=platform.targets.preflight(who.workspace,target_id)
        platform.store.event(who.workspace,"system","target_preflight",{"actor":who.id,"target_id":target_id,"connected":result["connected"]})
        return result

    @app.get("/api/campaigns")
    def campaigns(limit: int=Query(50,ge=1,le=200),offset: int=Query(0,ge=0),who: Actor=Depends(actor)):
        rows=platform.store.list("campaign",who.workspace,limit=limit,offset=offset)
        return [{"id":c["id"],"state":c["state"],"phase":c["phase"],"target_id":c["target_id"],
                 "target_revision":c["target_revision"],"created_at":c["_created"],"attempts":len(c["discovery_attempts"]),
                 "findings":len(c["findings"]),"coverage":coverage(c["cells"])} for c in rows]

    @app.post("/api/campaigns",status_code=201)
    def create_campaign(body: CampaignCreate,who: Actor=Depends(actor),key: str=Header("",alias="Idempotency-Key")):
        require_permission(who,"campaign");throttle(who)
        if system_state(who)["kill_switch"]:raise HTTPException(409,"Kill switch is active.")
        return platform.store.once(who.workspace,"campaign",key,body.model_dump(mode="json"),
                                   lambda:platform.create_campaign(who,body))

    @app.get("/api/campaigns/{campaign_id}")
    def campaign(campaign_id: str,who: Actor=Depends(actor)):
        summary=platform.summary(who.workspace,campaign_id);summary["budget"]=budget_view(summary["budget"])
        summary["worker"]=platform.store.get("job_"+campaign_id,who.workspace)
        return summary

    def campaign_action(campaign_id,action,who,key):
        require_permission(who,"campaign");throttle(who)
        if action in {"start","resume"} and system_state(who)["kill_switch"]:
            raise HTTPException(409,"Kill switch is active.")
        result=platform.store.once(who.workspace,"control:"+campaign_id+":"+action,key,{"action":action},
                         lambda:platform.control(who,campaign_id,action))
        result["budget"]=budget_view(result["budget"])
        return result

    @app.post("/api/campaigns/{campaign_id}/start")
    def start(campaign_id: str,who: Actor=Depends(actor),key: str=Header("",alias="Idempotency-Key")):
        return campaign_action(campaign_id,"start",who,key)
    @app.post("/api/campaigns/{campaign_id}/pause")
    def pause(campaign_id: str,who: Actor=Depends(actor),key: str=Header("",alias="Idempotency-Key")):
        return campaign_action(campaign_id,"pause",who,key)
    @app.post("/api/campaigns/{campaign_id}/resume")
    def resume(campaign_id: str,who: Actor=Depends(actor),key: str=Header("",alias="Idempotency-Key")):
        return campaign_action(campaign_id,"resume",who,key)
    @app.post("/api/campaigns/{campaign_id}/cancel")
    def cancel(campaign_id: str,who: Actor=Depends(actor),key: str=Header("",alias="Idempotency-Key")):
        return campaign_action(campaign_id,"cancel",who,key)

    @app.get("/api/campaigns/{campaign_id}/coverage")
    def cells(campaign_id: str,who: Actor=Depends(actor)):
        c=camp(campaign_id,who)
        return {"metrics":coverage(c["cells"]),"cells":c["cells"],
                "red_diversity":platform.red_diversity(who.workspace,c)}

    @app.get("/api/campaigns/{campaign_id}/attempts")
    def attempts(campaign_id: str,phase: str|None=None,limit: int=Query(50,ge=1,le=200),offset: int=Query(0,ge=0),who: Actor=Depends(actor)):
        c=camp(campaign_id,who)
        rows=platform.store.iter_records("attempt",who.workspace,parent=campaign_id,private_access=True)
        if phase:rows=[a for a in rows if a["phase"]==phase]
        # Final inputs stay evaluator-only. Public progress uses aggregate results.
        rows=sorted((a for a in rows if a["phase"] not in {"final","utility"}),key=lambda a:(a["_created"],a["id"]))
        return safe(who,c["target_id"],[{"id":a["id"],"phase":a["phase"],"cell":a["cell"],"candidate_digest":a["candidate_digest"],
               "execution_status":a["execution_status"],"verdict":(a["assessment"] or {}).get("verdict"),
               "turns":len(a["candidate"]["turns"]),"response_preview":a["steps"][-1]["trace"].get("response","")[:160] if a["steps"] else "",
               "created_at":a["_created"]} for a in rows[offset:offset+limit]])

    @app.get("/api/campaigns/{campaign_id}/attempts/{attempt_id}")
    def attempt_detail(campaign_id: str,attempt_id: str,who: Actor=Depends(actor)):
        require_permission(who,"evidence");c=camp(campaign_id,who)
        a=platform.store.get(attempt_id,who.workspace,private_access=True)
        if a["campaign_id"]!=campaign_id:raise NotFound(attempt_id)
        if a["phase"] in {"final","utility"}:raise PrivateAccess("Final inputs are evaluator-only.")
        return safe(who,c["target_id"],a)

    @app.get("/api/campaigns/{campaign_id}/findings")
    def findings(campaign_id: str,who: Actor=Depends(actor)):
        c=camp(campaign_id,who)
        rows=[platform.store.get(fid,who.workspace,private_access=True) for fid in c["findings"]]
        return [{"id":f["id"],"property":f["property"],"boundary":f["boundary"],"effect":f["effect"],"severity":f["severity"],
                 "reproduction_rate":f["reproduction_rate"],"diagnosis":f["diagnosis"],"atlas":f["atlas"],"status":f["status"]} for f in rows]

    @app.get("/api/campaigns/{campaign_id}/findings/{finding_id}")
    def finding(campaign_id: str,finding_id: str,who: Actor=Depends(actor)):
        require_permission(who,"evidence");c=camp(campaign_id,who)
        f=platform.store.get(finding_id,who.workspace,private_access=True)
        if f["campaign_id"]!=campaign_id:raise NotFound(finding_id)
        original=platform.store.get(f["original_attempt_id"],who.workspace,private_access=True)
        return safe(who,c["target_id"],f|{"original_attempt":original})

    @app.post("/api/campaigns/{campaign_id}/findings/{finding_id}/reproduce")
    def reproduce(campaign_id: str,finding_id: str,who: Actor=Depends(actor),key: str=Header("",alias="Idempotency-Key")):
        require_permission(who,"campaign");throttle(who)
        c=camp(campaign_id,who)
        if c["state"]!="completed":raise Conflict("Manual reproduction is available after the campaign completes.")
        f=platform.store.get(finding_id,who.workspace,private_access=True)
        if f["campaign_id"]!=campaign_id:raise NotFound(finding_id)
        original=platform.store.get(f["original_attempt_id"],who.workspace,private_access=True)
        def run():
            result=platform.execute_attempt(who.workspace,campaign_id,"manual_repro_"+digest(key)[:20],
                                             original["candidate"],original["cell"],"reproduction")
            return safe(who,c["target_id"],{"attempt_id":result["id"],"execution_status":result["execution_status"],"assessment":result["assessment"]})
        return platform.store.once(who.workspace,"reproduce:"+finding_id,key,{"finding_id":finding_id},run)

    @app.get("/api/campaigns/{campaign_id}/repair")
    def repair(campaign_id: str,who: Actor=Depends(actor)):
        c=camp(campaign_id,who)
        rows=[platform.store.get(eid,who.workspace,private_access=True) for eid in c["experiments"]]
        for row in rows:
            for candidate in row["candidates"]:
                candidate["artifact"].pop("path",None)
        return safe(who,c["target_id"],rows)

    @app.get("/api/campaigns/{campaign_id}/verification")
    def verification(campaign_id: str,who: Actor=Depends(actor)):
        c=camp(campaign_id,who)
        return [platform.store.get(vid,who.workspace) for vid in c["verification_runs"]]

    @app.get("/api/campaigns/{campaign_id}/budget")
    def budget(campaign_id: str,offset: int=Query(0,ge=0),limit: int=Query(100,ge=1,le=500),who: Actor=Depends(actor)):
        camp(campaign_id,who)
        value=Budget(platform.store,campaign_id,who.workspace).snapshot()
        operations=list(value["operations"].items())
        return budget_view(value)|{"operations":[{"operation_id":oid,**op} for oid,op in operations[offset:offset+limit]],"total_operations":len(operations)}

    @app.get("/api/campaigns/{campaign_id}/report")
    def report(campaign_id: str,format: str="json",who: Actor=Depends(actor)):
        c=camp(campaign_id,who)
        model=reporting.model(who.workspace,campaign_id)
        markdown=reporting.markdown(who.workspace,campaign_id,model)
        if format=="markdown":return PlainTextResponse(markdown,headers={"Content-Disposition":'attachment; filename="aegis-report.md"'})
        if format=="html":return HTMLResponse(reporting.html(model),headers={"Content-Disposition":'attachment; filename="aegis-report.html"'})
        if format=="pdf":return Response(reporting.pdf(model),media_type="application/pdf",headers={"Content-Disposition":'attachment; filename="aegis-report.pdf"'})
        if format=="pptx":return Response(reporting.powerpoint(model),media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",headers={"Content-Disposition":'attachment; filename="aegis-report.pptx"'})
        if format!="json":raise HTTPException(422,"Choose json, markdown, html, pdf, or pptx.")
        return {"markdown":markdown,"report":model,"html":reporting.html(model),"summary":platform.summary(who.workspace,campaign_id)|{"budget":budget_view(Budget(platform.store,campaign_id,who.workspace).snapshot())},
                "verification":[platform.store.get(vid,who.workspace) for vid in c["verification_runs"]]}

    @app.get("/api/campaigns/{campaign_id}/evidence-pack")
    def evidence(campaign_id: str,sensitive: bool=False,who: Actor=Depends(actor)):
        require_permission(who,"evidence");c=camp(campaign_id,who)
        if sensitive:
            require_permission(who,"admin")
            if c["state"] not in TERMINAL:raise Conflict("Raw evidence can be exported only after the experiment closes.")
        pack=reporting.build(who.workspace,campaign_id,sensitive=sensitive,include_final=sensitive)
        platform.store.event(who.workspace,campaign_id,"evidence_exported",{"actor":who.id,"sensitive":sensitive,"content_hash":pack["content_hash"]})
        return JSONResponse(pack,headers={"Content-Disposition":'attachment; filename="aegis-evidence.json"'})

    @app.get("/api/campaigns/{campaign_id}/evidence.ndjson")
    def evidence_stream(campaign_id: str,sensitive: bool=False,who: Actor=Depends(actor)):
        require_permission(who,"evidence");c=camp(campaign_id,who)
        if sensitive:
            require_permission(who,"admin")
            if c["state"] not in TERMINAL:raise Conflict("Raw evidence requires a closed experiment.")
        platform.store.event(who.workspace,campaign_id,"evidence_exported",{"actor":who.id,"sensitive":sensitive,"format":"ndjson"})
        return StreamingResponse(reporting.ndjson(who.workspace,campaign_id,sensitive=sensitive),
            media_type="application/x-ndjson",headers={"Content-Disposition":'attachment; filename="aegis-evidence.ndjson"'})

    @app.get("/api/campaigns/{campaign_id}/remediation-bundle")
    def remediation_bundle(campaign_id: str,who: Actor=Depends(actor)):
        require_permission(who,"evidence");camp(campaign_id,who)
        bundle=reporting.bundle(who.workspace,campaign_id)
        platform.store.event(who.workspace,campaign_id,"remediation_bundle_exported",{"actor":who.id,"bytes":len(bundle)})
        return Response(bundle,media_type="application/zip",headers={"Content-Disposition":'attachment; filename="aegis-remediation.zip"'})

    @app.get("/api/campaigns/{campaign_id}/events")
    async def event_stream(request: Request,campaign_id: str,after_seq: int=Query(0,ge=0),once: bool=False,who: Actor=Depends(actor)):
        camp(campaign_id,who)
        try:cursor=max(after_seq,int(request.headers.get("last-event-id","0")))
        except ValueError:raise HTTPException(400,"Invalid event cursor.")
        async def stream():
            nonlocal cursor
            while True:
                for event in platform.store.event_history(who.workspace,campaign_id,after=cursor,limit=100):
                    cursor=event["seq"]
                    yield "id: "+str(cursor)+"\ndata: "+json.dumps(event,ensure_ascii=False)+"\n\n"
                if once or await request.is_disconnected():return
                yield ": heartbeat\n\n"
                await asyncio.sleep(.5)
        return StreamingResponse(stream(),media_type="text/event-stream",headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

    def system_state(who):
        identifier="system_"+digest(who.workspace)[:24]
        try:return platform.store.get(identifier,who.workspace)
        except NotFound:
            platform.store.create("system",who.workspace,{"kill_switch":False},id=identifier)
            return platform.store.get(identifier,who.workspace)

    @app.get("/api/system")
    def system(who: Actor=Depends(actor)):
        return system_state(who)|{"workers":workers.status()}

    @app.post("/api/system/kill-switch")
    def kill(body: KillBody,who: Actor=Depends(actor)):
        require_permission(who,"admin")
        state=system_state(who)
        platform.store.mutate(state["id"],who.workspace,lambda p:p|{"kill_switch":body.active})
        if body.active:
            for c in platform.store.list("campaign",who.workspace,limit=1000):
                if c["state"] not in TERMINAL:platform.control(who,c["id"],"cancel")
        platform.store.event(who.workspace,"system","kill_switch_changed",{"actor":who.id,"active":body.active})
        return {"active":body.active}

    @app.get("/api/audit")
    def audit(after_seq: int=Query(0,ge=0),limit: int=Query(100,ge=1,le=500),latest: bool=False,who: Actor=Depends(actor)):
        require_permission(who,"admin")
        return platform.store.event_history(who.workspace,after=after_seq,limit=limit,latest=latest)

    @app.get("/api/users")
    def users(who: Actor=Depends(actor)):
        require_permission(who,"admin")
        return platform.store.list("user",who.workspace,limit=200)

    @app.post("/api/users",status_code=201)
    def user(body: UserCreate,who: Actor=Depends(actor)):
        require_permission(who,"admin")
        if body.workspace!=who.workspace and who.id!="bootstrap-admin":raise PermissionError("Workspace creation requires bootstrap administration.")
        token,new_actor=auth.issue_key(who,body.name,body.role,body.workspace)
        return {"actor":new_actor.model_dump(mode="json"),"access_key":token,"notice":"Shown once. The server stores only its hash."}

    @app.post("/api/users/{user_id}/revoke")
    def revoke(user_id: str,who: Actor=Depends(actor)):
        require_permission(who,"admin")
        platform.store.mutate(user_id,who.workspace,lambda p:p|{"revoked":True})
        platform.store.event(who.workspace,"system","access_revoked",{"actor":who.id,"user_id":user_id})
        return {"ok":True}

    return app


app = create_app()

