from pathlib import Path
import concurrent.futures
import pytest
from cryptography.fernet import Fernet

from aegis_v2.storage import Store, NotFound, PrivateAccess, Conflict
from aegis_v2.contracts import ResourceLimits, Role, Actor, DefenseConfig
from aegis_v2.auth import Auth, require_permission
from aegis_v2.budget import Budget, BudgetExceeded

@pytest.fixture
def store(tmp_path):
    s = Store("sqlite:///" + str(tmp_path / "test.db"), Fernet.generate_key().decode())
    yield s
    s.close()

def test_restart_workspace_and_encrypted_private_records(tmp_path):
    url = "sqlite:///" + str(tmp_path / "persistent.db")
    key = Fernet.generate_key().decode()
    s = Store(url, key)
    identifier = s.create("final", "one", {"secret": "hidden-test"}, private=True)
    s.close()
    reopened = Store(url, key)
    assert reopened.get(identifier, "one", private_access=True)["secret"] == "hidden-test"
    with pytest.raises(PrivateAccess): reopened.get(identifier, "one")
    with pytest.raises(NotFound): reopened.get(identifier, "two")
    assert b"hidden-test" not in (tmp_path / "persistent.db").read_bytes()
    reopened.close()

def test_permissions_are_derived_from_authenticated_keys(store):
    auth = Auth(store, "a" * 40)
    admin = auth.authenticate_key("a" * 40)
    token, viewer = auth.issue_key(admin, "Reader", Role.VIEWER, "private-workspace")
    assert auth.authenticate_key(token).workspace == "private-workspace"
    with pytest.raises(PermissionError): require_permission(viewer, "campaign")
    with pytest.raises(PermissionError): auth.authenticate_key("made-up-admin")
    session, actor = auth.login(token)
    assert auth.session_actor(session).role == Role.VIEWER
    auth.logout(session)
    with pytest.raises(PermissionError): auth.session_actor(session)

def test_budget_reserves_atomically_and_protects_final_allocation(store):
    budget = Budget.create(store, "c", "w", ResourceLimits(target_calls=100))
    def reserve(i):
        try:
            budget.reserve(str(i), "discovery", {"target_calls": 1}, "request")
            return True
        except BudgetExceeded: return False
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        assert sum(pool.map(reserve, range(60))) == 36
    budget.reserve("final-call", "final", {"target_calls": 1}, "verification")
    budget.settle("final-call", {"target_calls": 1})
    snap = budget.snapshot()
    assert snap["used"]["target_calls"] == 1
    assert snap["reserved"]["target_calls"] == 36
    with pytest.raises(Conflict): budget.reserve("final-call", "final", {"target_calls": 1}, "again")

def test_budget_settles_ambiguous_calls_conservatively(store):
    b = Budget.create(store, "c", "w", ResourceLimits())
    b.reserve("a", "discovery", {"target_calls": 1, "tokens": 100}, "target")
    b.reconcile_interrupted()
    assert b.snapshot()["used"]["tokens"] == 100
    assert b.snapshot()["operations"]["a"]["status"] == "interrupted"

def test_only_allowlisted_boolean_configuration_can_be_patched():
    with pytest.raises(ValueError): DefenseConfig().patch({"arbitrary_path": True})
    with pytest.raises(ValueError): DefenseConfig().patch({"tenant_filter": "true"})
    assert DefenseConfig().patch({"tenant_filter": True}).tenant_filter

def test_idempotency_returns_the_same_result_and_rejects_changed_body(store):
    result = store.once("w", "op", "key", {"x": 1}, lambda: {"id": "only-one"})
    assert store.once("w", "op", "key", {"x": 1}, lambda: pytest.fail("duplicate")) == result
    with pytest.raises(Conflict): store.once("w", "op", "key", {"x": 2}, lambda: {})

