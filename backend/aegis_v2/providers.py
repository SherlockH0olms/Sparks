from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from urllib.parse import quote, urlsplit

import httpx

from .budget import Budget
from .config import ProviderSettings
from .contracts import ExecutionStatus, digest
from .storage import Store, NotFound


class ProviderError(RuntimeError):
    def __init__(self, message: str, status=ExecutionStatus.INFRASTRUCTURE_ERROR):
        super().__init__(message)
        self.status = status


class UnsupportedTools(ProviderError):
    pass


@dataclass
class ChatResult:
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    finish_reason: str = ""
    provider_request_id: str = ""
    reasoning_content: str | None = None

    def payload(self):
        return {"content": self.content, "tool_calls": self.tool_calls, "usage": self.usage,
                "finish_reason": self.finish_reason, "provider_request_id": self.provider_request_id,
                "reasoning_content": self.reasoning_content}


class ChatClient:
    def __init__(self, settings: ProviderSettings, *, transport=None, local=False):
        self.settings = settings
        self.transport = transport
        self.local = local
        self.provenance = "fixture" if transport else ("local_model" if local else settings.provider)
        self.tool_calling_supported = None

    def ready(self):
        if self.local:
            return bool(self.settings.endpoint and self.settings.model)
        return not self.settings.issues()

    def request_parts(self):
        s = self.settings
        endpoint = s.endpoint.rstrip("/")
        if s.provider == "azure_openai":
            url = endpoint + "/openai/deployments/" + quote(s.deployment, safe="") + "/chat/completions"
            params = {"api-version": s.api_version}
            headers = {"api-key": s.api_key}
        elif s.provider == "foundry":
            url = endpoint + ("" if endpoint.endswith("/chat/completions") else "/chat/completions")
            # Foundry also exposes the GA OpenAI v1 API, which rejects the
            # dated inference API's api-version query parameter.
            params = {} if "/openai/v1" in urlsplit(endpoint).path else {"api-version": s.api_version}
            headers = {"api-key": s.api_key}
        else:
            url = endpoint + ("" if endpoint.endswith("/chat/completions") else "/chat/completions")
            params = {}
            headers = {"Authorization": "Bearer " + s.api_key} if s.api_key else {}
        return url, params, headers

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> ChatResult:
        if not self.ready():
            raise ProviderError("Provider configuration is incomplete.")
        s = self.settings
        url, params, headers = self.request_parts()
        model_name = (s.model or s.deployment).lower()
        token_field = "max_completion_tokens" if model_name.startswith(("o1", "o3", "o4", "gpt-5", "gpt-6")) else "max_tokens"
        payload = {"messages": messages}
        if s.max_output_tokens is not None:
            payload[token_field] = s.max_output_tokens
        if s.provider != "azure_openai":
            payload["model"] = s.model
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        try:
            with httpx.Client(timeout=s.timeout, transport=self.transport, follow_redirects=False, trust_env=False) as client:
                response = client.post(url, params=params, headers=headers, json=payload)
            if response.status_code >= 400:
                if tools and response.status_code in {400, 422}:
                    try:
                        error = response.json().get("error", {})
                        detail = str(error.get("message", "") if isinstance(error, dict) else error).lower()
                    except ValueError:
                        detail = ""
                    if "tool" in detail and any(x in detail for x in ("unsupported", "not supported", "does not support", "unrecognized")):
                        self.tool_calling_supported = False
                        raise UnsupportedTools("This deployment does not support native function calling.")
                raise ProviderError(f"Provider returned HTTP {response.status_code}; request did not complete.")
            data = response.json()
            choice = data["choices"][0]
            message = choice["message"]
            content = message.get("content") or ""
            if isinstance(content, list):
                content = "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
            calls = message.get("tool_calls") or []
            if not isinstance(content, str) or not isinstance(calls, list):
                raise ValueError("Invalid chat message shape.")
            if calls:
                self.tool_calling_supported = True
            reasoning = message.get("reasoning_content")
            return ChatResult(content, calls, data.get("usage", {}),
                              choice.get("finish_reason", ""), response.headers.get("x-request-id", data.get("id", "")),
                              reasoning if isinstance(reasoning, str) else None)
        except httpx.TimeoutException:
            raise ProviderError("Provider timed out; no security result was inferred.", ExecutionStatus.TIMEOUT) from None
        except (httpx.HTTPError, KeyError, ValueError, TypeError, IndexError):
            raise ProviderError("Provider response or connection was invalid.") from None


class BudgetedChat:
    def __init__(self, store: Store, workspace: str, client: ChatClient, resource: str):
        self.store, self.workspace, self.client, self.resource = store, workspace, client, resource

    def invoke(self, messages, budget: Budget, bucket: str, operation_id: str, purpose: str, tools=None):
        call_id = "call_" + operation_id
        request_hash = digest({"messages": messages, "tools": tools, "model": self.client.settings.model,
                               "provider": self.client.settings.provider})
        try:
            prior = self.store.get(call_id, self.workspace, private_access=True)
        except NotFound:
            prior = None
        if prior:
            if prior["request_hash"] != request_hash:
                raise ProviderError("An operation identifier was reused with a different request.")
            if prior["status"] == "completed":
                return ChatResult(**prior["response"])
            raise ProviderError("An interrupted or failed request is preserved and will not be silently repeated.",
                                ExecutionStatus(prior["status"]))
        if not self.client.ready():
            raise ProviderError("Provider configuration is incomplete.")
        # UTF-8 bytes plus message/schema overhead conservatively bound ordinary
        # text tokens, avoiding optimistic character/4 accounting.
        input_bound = len(json.dumps({"messages": messages, "tools": tools}, ensure_ascii=False).encode()) + 32 * len(messages)
        max_output = self.client.settings.max_output_tokens
        timeout = self.client.settings.timeout
        token_reservation = input_bound + (max_output or 0)
        if max_output is None:
            available_tokens = budget.available(bucket, "tokens")
            if available_tokens is not None:
                token_reservation = max(input_bound, available_tokens)
        wall_reservation = timeout if timeout is not None else (budget.available(bucket, "wall_seconds") or 0)
        reserved = {self.resource: 1, "tokens": token_reservation, "wall_seconds": wall_reservation}
        budget.reserve(operation_id, bucket, reserved, purpose)
        self.store.create("call", self.workspace, {"request_hash": request_hash, "messages": messages,
                 "campaign_id": budget.id.removeprefix("budget_"),
                 "tools": tools, "status": "interrupted", "provenance": self.client.provenance,
                 "model": self.client.settings.model or self.client.settings.deployment,
                 "response": None}, id=call_id, private=True)
        started = time.perf_counter()
        try:
            result = self.client.chat(messages, tools)
        except ProviderError as exc:
            budget.settle(operation_id, reserved | {"wall_seconds": time.perf_counter() - started}, status=exc.status.value)
            self.store.mutate(call_id, self.workspace, lambda p: p | {"status": exc.status.value, "error": str(exc)}, private_access=True)
            raise
        elapsed = time.perf_counter() - started
        usage = result.usage
        actual_tokens = usage.get("total_tokens")
        if not isinstance(actual_tokens, int) or actual_tokens < 0:
            actual_tokens = reserved["tokens"]
        actual = {self.resource: 1, "tokens": actual_tokens, "wall_seconds": elapsed}
        budget.settle(operation_id, actual)
        self.store.mutate(call_id, self.workspace, lambda p: p | {"status": "completed", "response": result.payload(),
                          "actual": actual, "wall_seconds": elapsed}, private_access=True)
        return result

