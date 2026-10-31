from __future__ import annotations

from .contracts import ResourceLimits, now
from .storage import Store, Conflict

ALLOCATION_SHARES = {"baseline": .08, "discovery": .36, "reproduction": .12,
                     "development": .18, "final": .18, "utility": .08}


class BudgetExceeded(RuntimeError):
    pass


class OperationInFlight(RuntimeError):
    pass


class Budget:
    def __init__(self, store: Store, campaign_id: str, workspace: str):
        self.store, self.id, self.workspace = store, "budget_" + campaign_id, workspace

    @classmethod
    def create(cls, store: Store, campaign_id: str, workspace: str, limits: ResourceLimits):
        totals = limits.model_dump()
        buckets = {b: {r: v * share if v is not None else None for r, v in totals.items()}
                   for b, share in ALLOCATION_SHARES.items()}
        payload = {"limits": totals, "allocations": buckets, "used": {r: 0 for r in totals},
                   "operations": {}, "overrun": False}
        store.create("budget", workspace, payload, id="budget_" + campaign_id)
        return cls(store, campaign_id, workspace)

    def reserve(self, operation_id: str, bucket: str, resources: dict[str, float], purpose: str):
        def change(p):
            if p["overrun"]:
                raise BudgetExceeded("Measured provider usage exceeded the conservative reservation; campaign stopped.")
            if operation_id in p["operations"]:
                op = p["operations"][operation_id]
                if op["status"] == "reserved":
                    raise OperationInFlight("An interrupted operation must be reconciled before another call.")
                raise Conflict("This operation already executed.")
            if bucket not in p["allocations"] or any(v < 0 for v in resources.values()):
                raise ValueError("Invalid budget allocation.")
            for resource, requested in resources.items():
                if resource not in p["limits"]:
                    raise ValueError("Unknown resource.")
                committed = sum(o["reserved"].get(resource, 0) for o in p["operations"].values() if o["status"] == "reserved")
                bucket_committed = sum((o["reserved"] if o["status"] == "reserved" else o["actual"]).get(resource, 0)
                                       for o in p["operations"].values() if o["bucket"] == bucket)
                limit = p["limits"][resource]
                allocation = p["allocations"][bucket][resource]
                if limit is not None and p["used"][resource] + committed + requested > limit + 1e-6:
                    raise BudgetExceeded(resource + " total limit exhausted.")
                if allocation is not None and bucket_committed + requested > allocation + 1e-6:
                    raise BudgetExceeded(resource + " " + bucket + " allocation exhausted.")
            p["operations"][operation_id] = {"bucket": bucket, "purpose": purpose, "reserved": resources,
                      "actual": {}, "status": "reserved", "started": now(), "finished": None}
            return p
        self.store.mutate(self.id, self.workspace, change)

    def settle(self, operation_id: str, actual: dict[str, float] | None = None, status="completed"):
        def change(p):
            op = p["operations"][operation_id]
            if op["status"] != "reserved":
                return p
            measured = actual or op["reserved"]
            if any(r not in op["reserved"] or v < 0 for r, v in measured.items()):
                raise ValueError("Invalid measured resources.")
            if any(p["limits"][r] is not None and measured.get(r, 0) > op["reserved"][r] + 1e-6 for r in measured):
                p["overrun"] = True
            op.update(actual=measured, status=status, finished=now())
            for r, value in measured.items():
                p["used"][r] += value
            return p
        self.store.mutate(self.id, self.workspace, change)

    def reconcile_interrupted(self):
        p = self.store.get(self.id, self.workspace)
        for oid, op in p["operations"].items():
            if op["status"] == "reserved":
                self.settle(oid, status="interrupted")

    def available(self, bucket: str, resource: str):
        p = self.store.get(self.id, self.workspace)
        allocation = p["allocations"][bucket][resource]
        limit = p["limits"][resource]
        if allocation is None or limit is None:
            return None
        committed = sum(o["reserved"].get(resource, 0) for o in p["operations"].values() if o["status"] == "reserved")
        bucket_used = sum((o["reserved"] if o["status"] == "reserved" else o["actual"]).get(resource, 0)
                          for o in p["operations"].values() if o["bucket"] == bucket)
        return max(0, min(allocation - bucket_used, limit - p["used"][resource] - committed))

    def snapshot(self):
        p = self.store.get(self.id, self.workspace)
        reserved = {r: sum(o["reserved"].get(r, 0) for o in p["operations"].values() if o["status"] == "reserved") for r in p["limits"]}
        p["reserved"] = reserved
        p["remaining"] = {r: max(0, v - p["used"][r] - reserved[r]) if v is not None else None
                          for r, v in p["limits"].items()}
        return p

