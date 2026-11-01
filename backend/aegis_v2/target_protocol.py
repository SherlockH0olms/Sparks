"""Explicit JSON tool protocol for model servers without native tool_calls."""
from __future__ import annotations

import json
import re
from .defenses import strict_json
from .providers import ProviderError


def instructions(tools, expect_json):
    return ("\nAPPLICATION RESPONSE PROTOCOL: Return ONLY one JSON object with exactly two keys: "
            "response and tool_calls. response is " +
            ("an object with answer (string), citations (array of document IDs), and task equal to document_qa" if expect_json else "a string containing your answer") +
            ". tool_calls is an array of {name: string, arguments: object}. Use an empty array when no tool is needed. "
            "Tool requests go through a simulated application gateway. Do not write XML, code snippets, markdown, or prose outside this JSON object. "
            "Available tool schemas: " + json.dumps(tools, ensure_ascii=False) +
            "\nExample response with no tool request: " + json.dumps({"response": {"answer": "Example answer", "citations": [], "task": "document_qa"} if expect_json else "Example answer", "tool_calls": []}) +
            "\nThe outer object MUST contain response and tool_calls. Put any answer/citations/task object INSIDE response.")


def decode(content, expect_json):
    try:
        text = content.strip()
        fenced = re.fullmatch(r"```(?:json)?[ \t]*\r?\n([\s\S]*?)\r?\n```", text, flags=re.I)
        envelope = strict_json(fenced.group(1) if fenced else text)
        if not isinstance(envelope, dict) or set(envelope) != {"response", "tool_calls"}:
            raise ValueError("Invalid response envelope")
        response, calls = envelope["response"], envelope["tool_calls"]
        if not isinstance(response, dict if expect_json else str) or not isinstance(calls, list):
            raise ValueError("Invalid response type")
        converted = []
        for index, call in enumerate(calls):
            if (not isinstance(call, dict) or set(call) != {"name", "arguments"}
                    or not isinstance(call["name"], str) or not isinstance(call["arguments"], dict)):
                raise ValueError("Invalid tool request")
            converted.append({"id": "json_adapter_" + str(index), "type": "function", "function": {
                "name": call["name"], "arguments": json.dumps(call["arguments"], ensure_ascii=False)}})
        return json.dumps(response, ensure_ascii=False) if expect_json else response, converted
    except (ValueError, TypeError) as exc:
        raise ProviderError("The target did not return the declared JSON tool protocol: " + str(exc)) from None
