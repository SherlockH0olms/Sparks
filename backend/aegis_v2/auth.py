from __future__ import annotations

import hashlib
import hmac
import secrets
from .contracts import Actor, Role, now
from .storage import Store, NotFound


def token_hash(token: str):
    return hashlib.sha256(token.encode()).hexdigest()


PERMISSIONS = {
    Role.VIEWER: {"read"},
    Role.ANALYST: {"read", "campaign", "evidence"},
    Role.MAINTAINER: {"read", "campaign", "evidence", "target", "repair"},
    Role.ADMIN: {"read", "campaign", "evidence", "target", "repair", "admin"},
}


def require_permission(actor: Actor, permission: str):
    if permission not in PERMISSIONS[actor.role]:
        raise PermissionError("Your role cannot perform this action.")


class Auth:
    def __init__(self, store: Store, admin_token: str, session_hours=8):
        self.store = store
        self.admin_token = admin_token
        self.session_hours = session_hours

    def authenticate_key(self, token: str) -> Actor:
        if not token:
            raise PermissionError("Authentication is required.")
        if len(self.admin_token) >= 32 and hmac.compare_digest(token_hash(token), token_hash(self.admin_token)):
            return Actor(id="bootstrap-admin", name="Administrator", role=Role.ADMIN)
        try:
            record = self.store.get("key_" + token_hash(token), "auth", private_access=True)
        except NotFound:
            raise PermissionError("Invalid access key.") from None
        if record.get("revoked"):
            raise PermissionError("Access key was revoked.")
        actor = Actor.model_validate(record["actor"])
        if self.store.get(actor.id, actor.workspace).get("revoked"):
            raise PermissionError("Access key was revoked.")
        return actor

    def login(self, key: str) -> tuple[str, Actor]:
        actor = self.authenticate_key(key)
        session = secrets.token_urlsafe(40)
        self.store.create("session", "auth", {"actor": actor.model_dump(mode="json"),
                "expires": now() + self.session_hours * 3600}, id="session_" + token_hash(session), private=True)
        return session, actor

    def session_actor(self, token: str) -> Actor:
        try:
            record = self.store.get("session_" + token_hash(token), "auth", private_access=True)
        except NotFound:
            raise PermissionError("Session is invalid or expired.") from None
        if record["expires"] <= now() or record.get("revoked"):
            raise PermissionError("Session is invalid or expired.")
        actor = Actor.model_validate(record["actor"])
        if actor.id != "bootstrap-admin":
            user = self.store.get(actor.id, actor.workspace)
            if user.get("revoked"):
                raise PermissionError("Access was revoked.")
        return actor

    def logout(self, token: str):
        try:
            self.store.mutate("session_" + token_hash(token), "auth", lambda p: p | {"revoked": True}, private_access=True)
        except NotFound:
            pass

    def issue_key(self, administrator: Actor, name: str, role: Role, workspace: str) -> tuple[str, Actor]:
        require_permission(administrator, "admin")
        if role == Role.ADMIN and administrator.id != "bootstrap-admin":
            raise PermissionError("Only the bootstrap administrator may issue administrator keys.")
        token = secrets.token_urlsafe(40)
        identifier = self.store.create("user", workspace, {"name": name, "role": role.value, "revoked": False})
        actor = Actor(id=identifier, name=name, role=role, workspace=workspace)
        self.store.create("access_key", "auth", {"actor": actor.model_dump(mode="json"), "revoked": False},
                          id="key_" + token_hash(token), private=True)
        self.store.event(workspace, "system", "access_key_issued", {"actor": administrator.id, "user": actor.id, "role": role.value})
        return token, actor

