from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from .budget import Budget, BudgetExceeded
from .contracts import new_id, now
from .runtime import ControlSignal, TERMINAL
from .storage import Conflict


class Workers:
    def __init__(self, platform):
        self.p = platform
        self.owner = new_id("worker")
        self.stop_event = threading.Event()
        self.executor = ThreadPoolExecutor(max_workers=platform.settings.workers, thread_name_prefix="aegis")
        self.active = {}
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self.loop, daemon=True, name="aegis-controller")
        self.thread.start()

    def claim(self, workspace, job_id):
        recovered = False
        def take(p):
            nonlocal recovered
            if p["state"] == "running" and p["lease_until"] < now():
                recovered = True
            elif p["state"] != "queued":
                raise Conflict("Job is not claimable.")
            p.update(state="running", owner=self.owner, lease_until=now()+self.p.settings.lease_seconds, heartbeat=now())
            return p
        job = self.p.store.mutate(job_id, workspace, take)
        if recovered:
            Budget(self.p.store,job["campaign_id"],workspace).reconcile_interrupted()
            self.p.store.event(workspace,job["campaign_id"],"worker_recovered",{"owner":self.owner,"recovery":"preserved checkpoint; ambiguous calls charged conservatively"})
        return job

    def loop(self):
        while not self.stop_event.wait(.2):
            for key,future in list(self.active.items()):
                if future.done():
                    self.active.pop(key,None)
            if len(self.active) >= self.p.settings.workers:
                continue
            for workspace in self.p.store.workspaces():
                if workspace == "auth":continue
                for job in self.p.store.list("job",workspace,limit=1000):
                    key=(workspace,job["id"])
                    if key in self.active:continue
                    if job["state"] != "queued" and not (job["state"]=="running" and job["lease_until"]<now()):continue
                    try:claimed=self.claim(workspace,job["id"])
                    except Conflict:continue
                    self.active[key]=self.executor.submit(self.run,workspace,claimed)
                    if len(self.active)>=self.p.settings.workers:break
                if len(self.active)>=self.p.settings.workers:break

    def heartbeat(self,workspace,job_id,done):
        while not done.wait(max(2,self.p.settings.lease_seconds/3)):
            def renew(p):
                if p["owner"]!=self.owner or p["state"]!="running":raise Conflict("Lease was lost.")
                return p|{"lease_until":now()+self.p.settings.lease_seconds,"heartbeat":now()}
            try:self.p.store.mutate(job_id,workspace,renew)
            except Conflict:return

    def run(self,workspace,job):
        cid=job["campaign_id"];job_id=job["id"];done=threading.Event()
        beat=threading.Thread(target=self.heartbeat,args=(workspace,job_id,done),daemon=True)
        beat.start()
        self.p.worker_context.owner=self.owner
        self.p.worker_context.campaign=cid
        self.p.worker_context.stopping=self.stop_event
        final_job_state="queued"
        try:
            c=self.p.store.get(cid,workspace)
            self.p.store.mutate(cid,workspace,lambda p:p|{"state":p["phase"]})
            self.p.store.event(workspace,cid,"worker_started",{"owner":self.owner})
            while not self.stop_event.is_set():
                c=self.p.store.get(cid,workspace)
                if c["state"] in TERMINAL:
                    final_job_state=c["state"]
                    break
                self.p.step(workspace,cid)
        except ControlSignal as signal:
            if signal.action=="lease_lost":
                return
            if signal.action=="shutdown":
                self.p.store.mutate(cid,workspace,lambda p:p|{"state":"queued",
                    "checkpoint":{"phase":p["phase"],"progress":p["progress"],"saved_at":now()}})
                self.p.store.event(workspace,cid,"worker_checkpointed",{"reason":"graceful shutdown"})
                return
            state="paused" if signal.action=="pause" else "cancelled"
            self.p.store.mutate(cid,workspace,lambda p:p|{"state":state,"finished_at":now() if state=="cancelled" else p["finished_at"],
                                  "checkpoint":{"phase":p["phase"],"progress":p["progress"],"saved_at":now()}})
            self.p.store.event(workspace,cid,"campaign_"+state,{"phase":self.p.store.get(cid,workspace)["phase"]})
            final_job_state=state
        except Exception as exc:
            state="budget_exhausted" if isinstance(exc,BudgetExceeded) else "failed"
            self.p.store.mutate(cid,workspace,lambda p:p|{"state":state,"error":{"type":type(exc).__name__,"message":str(exc)[:500]},
                                  "finished_at":now(),"checkpoint":{"phase":p["phase"],"progress":p["progress"],"saved_at":now()}})
            self.p.store.event(workspace,cid,"campaign_"+state,{"type":type(exc).__name__,"message":str(exc)[:500]})
            final_job_state=state
        finally:
            done.set()
            def release(p):
                if p["owner"]!=self.owner:return p
                return p|{"state":final_job_state,"owner":None,"lease_until":0,"heartbeat":now()}
            self.p.store.mutate(job_id,workspace,release)

    def status(self):
        return {"configured_workers":self.p.settings.workers,"active_jobs":len(self.active),
                "controller_alive":bool(self.thread and self.thread.is_alive())}

    def close(self):
        self.stop_event.set()
        if self.thread:self.thread.join(timeout=2)
        self.executor.shutdown(wait=True,cancel_futures=True)

