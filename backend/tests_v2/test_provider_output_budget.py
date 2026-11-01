"""No configured output ceiling must work with gateways that reject null."""
import json

import httpx
import pytest

from aegis_v2.config import ProviderSettings
from aegis_v2.providers import ChatClient


@pytest.mark.parametrize("maximum", [None, 256])
def test_openai_compatible_target_omits_an_unconfigured_output_budget(maximum):
    def gateway(request):
        body = json.loads(request.content)
        if "max_tokens" in body and body["max_tokens"] is None:
            return httpx.Response(400, json={"error": {"message": "output budget"}})
        if maximum is None:
            assert "max_tokens" not in body
        else:
            assert body["max_tokens"] == maximum
        return httpx.Response(200, json={"choices": [{"message": {"content": "READY"}, "finish_reason": "stop"}]})

    client = ChatClient(ProviderSettings(provider="openai_compatible", endpoint="https://target.example/v1",
                        model="arch01", max_output_tokens=maximum),
                        transport=httpx.MockTransport(gateway), local=True)
    assert client.chat([{"role": "user", "content": "Reply with READY."}]).content == "READY"
