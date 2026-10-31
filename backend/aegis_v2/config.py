from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ProviderSettings:
    provider: str = "foundry"
    endpoint: str = ""
    api_key: str = field(default="", repr=False)
    model: str = ""
    deployment: str = ""
    api_version: str = "2024-05-01-preview"
    timeout: float | None = None
    max_output_tokens: int | None = None
    tool_mode: str = "auto"

    def issues(self) -> list[str]:
        out = []
        if self.provider not in {"foundry", "azure_openai", "openai_compatible"}:
            out.append("Unsupported provider type.")
        if self.tool_mode not in {"auto", "native", "json"}:
            out.append("Tool mode must be auto, native or json.")
        if not self.endpoint:
            out.append("Endpoint is missing.")
        elif urlsplit(self.endpoint).scheme != "https" and not (
            self.provider == "openai_compatible" and urlsplit(self.endpoint).hostname in {"localhost", "127.0.0.1", "::1"}
        ):
            out.append("A remote provider must use HTTPS.")
        if not self.api_key:
            out.append("API key is missing.")
        if not self.model and not (self.provider == "azure_openai" and self.deployment):
            out.append("Model or deployment is missing.")
        if self.provider == "azure_openai" and not self.deployment:
            out.append("Azure OpenAI deployment is missing.")
        return out

    def public(self) -> dict:
        return {"provider": self.provider, "configured": not self.issues(),
                "model": self.model or self.deployment or None, "issues": self.issues(),
                "max_output_tokens": self.max_output_tokens, "timeout_seconds": self.timeout,
                "tool_mode": self.tool_mode}


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///./data/aegis.db"
    admin_token: str = field(default="", repr=False)
    vault_key: str = field(default="", repr=False)
    workers: int = 2
    lease_seconds: int = 90
    session_hours: int = 8
    cookie_secure: bool = False
    allowed_origins: tuple[str, ...] = ("http://localhost:3000", "http://127.0.0.1:3000")
    local_endpoint: str = "http://127.0.0.1:11434/v1"
    local_model: str = ""
    local_api_key: str = field(default="", repr=False)
    local_allowed_hosts: tuple[str, ...] = ("localhost", "127.0.0.1", "::1", "host.docker.internal")
    target_timeout: float = 45
    target_max_output_tokens: int = 800
    red: ProviderSettings = field(default_factory=ProviderSettings)
    judge: ProviderSettings = field(default_factory=ProviderSettings)
    runtime_dir: Path = field(default_factory=lambda: ROOT / ".runtime")

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv(ROOT / ".env", override=False)
        load_dotenv(ROOT / "backend" / ".env", override=False)
        def optional_number(name: str, cast):
            raw = os.getenv(name, "0").strip().lower()
            if raw in {"", "0", "none", "null", "unlimited"}:
                return None
            value = cast(raw)
            if value <= 0:
                raise ValueError(name + " must be positive or 0 for no application limit.")
            return value
        def provider(prefix: str) -> ProviderSettings:
            return ProviderSettings(
                provider=os.getenv(prefix + "_PROVIDER", "foundry"),
                endpoint=os.getenv(prefix + "_ENDPOINT", "").rstrip("/"),
                api_key=os.getenv(prefix + "_API_KEY", ""),
                model=os.getenv(prefix + "_MODEL", ""),
                deployment=os.getenv(prefix + "_DEPLOYMENT", ""),
                api_version=os.getenv(prefix + "_API_VERSION", "2024-05-01-preview"),
                timeout=optional_number(prefix + "_TIMEOUT_SECONDS", float),
                max_output_tokens=optional_number(prefix + "_MAX_OUTPUT_TOKENS", int),
                tool_mode=os.getenv(prefix + "_TOOL_MODE", "auto").lower(),
            )
        database_url = os.getenv("AEGIS_DATABASE_URL", "sqlite:///./data/aegis.db")
        if database_url.startswith("sqlite:///./"):
            database_url = "sqlite:///" + str(ROOT / database_url.removeprefix("sqlite:///./"))
        return cls(
            database_url=database_url, admin_token=os.getenv("AEGIS_ADMIN_TOKEN", ""),
            vault_key=os.getenv("AEGIS_VAULT_KEY", ""),
            workers=max(1, min(8, int(os.getenv("AEGIS_WORKERS", "2")))),
            lease_seconds=max(30, int(os.getenv("AEGIS_LEASE_SECONDS", "90"))),
            session_hours=max(1, int(os.getenv("AEGIS_SESSION_HOURS", "8"))),
            cookie_secure=os.getenv("AEGIS_COOKIE_SECURE", "false").lower() == "true",
            allowed_origins=tuple(x.strip() for x in os.getenv("AEGIS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if x.strip()),
            local_endpoint=os.getenv("AEGIS_LOCAL_ENDPOINT", "http://127.0.0.1:11434/v1").rstrip("/"),
            local_model=os.getenv("AEGIS_LOCAL_MODEL", ""), local_api_key=os.getenv("AEGIS_LOCAL_API_KEY", ""),
            local_allowed_hosts=tuple(x.strip() for x in os.getenv("AEGIS_LOCAL_ALLOWED_HOSTS", "localhost,127.0.0.1,::1,host.docker.internal").split(",") if x.strip()),
            target_timeout=float(os.getenv("AEGIS_TARGET_TIMEOUT_SECONDS", "45")),
            target_max_output_tokens=int(os.getenv("AEGIS_TARGET_MAX_OUTPUT_TOKENS", "800")),
            red=provider("AEGIS_RED"), judge=provider("AEGIS_JUDGE"),
        )

