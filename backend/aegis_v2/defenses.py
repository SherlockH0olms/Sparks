"""Executable defense controls and their evidence-backed deployment guidance."""
from __future__ import annotations

import base64
import codecs
import json
import re
import unicodedata
from jsonschema import Draft202012Validator

OWASP = "https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html"
JSONSCHEMA = "https://python-jsonschema.readthedocs.io/"


def control(name, layer, properties, requires, implementation, steps, limitations, *, tool=None):
    return {"name": name, "layer": layer, "properties": properties, "requires": requires,
            "implementation": implementation, "deployment_steps": steps, "limitations": limitations,
            "sources": [JSONSCHEMA if tool == "jsonschema" else OWASP], "tool": tool}


CONTROLS = {
    "tenant_filter": control("Tenant retrieval authorization", "retrieval", ["tenant_isolation", "secret_confidentiality", "session_isolation"], ["rag", "multi_tenant"],
        "Filter document candidates by the authenticated tenant before ranking.",
        ["Derive tenant identity from trusted authentication.", "Apply the tenant filter before retrieval and ranking.", "Retest both authorized and cross-tenant questions."],
        ["Protects the registered retrieval layer; external retrieval services need equivalent enforcement."]),
    "tool_authorization": control("Trusted tool authorization", "tool_gateway", ["tool_authorization", "data_instruction_separation"], ["tools"],
        "Authorize tool effects using trusted permissions and tenant-owned destinations.",
        ["Keep permissions outside model-generated arguments.", "Enforce permissions before every tool effect.", "Retest authorized operations and spoofed role claims."],
        ["The built-in email/export sinks are simulated; production gateways require the same checks."]),
    "data_separation": control("Untrusted document boundary", "prompt", ["data_instruction_separation", "task_constraint"], ["rag"],
        "Declare retrieved documents as untrusted reference data.",
        ["Keep the application policy in a system message.", "Label document blocks as data with no authority.", "Test direct and indirect injections after the change."],
        ["A prompt boundary depends on model behavior and must be paired with enforceable access controls."]),
    "output_validation": control("Complete response schema", "output", ["output_integrity"], ["structured_output"],
        "Validate the complete response with JSON Schema Draft 2020-12 and reject duplicate keys.",
        ["Define the expected response contract.", "Validate before returning output to the caller.", "Treat rejected legitimate answers as utility failures."],
        ["Contract validity alone does not establish factual accuracy."], tool="jsonschema"),
    "input_filter": control("Injection pattern filter", "input", ["task_constraint", "data_instruction_separation"], [],
        "Detect a documented set of injection instruction patterns.",
        ["Run pattern checks before inference.", "Measure false blocks on normal tasks.", "Include paraphrase and encoding variants in verification."],
        ["Lexical detection is bypassable and is never a general injection guarantee."]),
    "task_policy": control("Explicit task and authority policy", "prompt", ["task_constraint", "data_instruction_separation", "tool_authorization"], [],
        "Add explicit task, document authority, and tool permission rules.",
        ["State intended behavior and trust boundaries.", "Keep policy separate from user and document content.", "Evaluate compliance with the independent Judge."],
        ["Prompt changes do not replace retrieval and gateway authorization."]),
    "tool_schema_validation": control("Tool argument contracts", "tool_gateway", ["tool_authorization", "output_integrity"], ["tools"],
        "Validate tool names and complete argument schemas before evaluating permissions.",
        ["Register allowed tool schemas.", "Reject unknown tools, duplicate keys, missing fields, and wrong types.", "Retest allowed tool calls with valid arguments."],
        ["Syntactically valid arguments still require authorization."], tool="jsonschema"),
    "secret_redaction": control("Protected secret output gate", "output", ["secret_confidentiality", "session_isolation"], [],
        "Mask server-owned confidential markers belonging to other tenants before public output and tool effects.",
        ["Identify secrets through trusted data ownership metadata.", "Inspect response and effect arguments before disclosure.", "Verify authorized information remains useful."],
        ["Protects known registered markers; it does not identify every possible secret."]),
    "citation_validation": control("Citation ownership and provenance", "output", ["output_integrity", "tenant_isolation"], ["rag", "structured_output"],
        "Require citations to identify retrieved, authorized documents.",
        ["Bind response citations to the retrieved document set.", "Reject foreign, missing, or fabricated document identifiers.", "Retest valid cited answers."],
        ["A valid citation does not prove that the answer accurately represents its source."]),
    "unicode_normalization": control("Unicode instruction normalization", "input", ["task_constraint", "data_instruction_separation"], [],
        "Normalize compatibility characters and remove invisible format characters from user instructions.",
        ["Normalize the text used by input controls.", "Record a content hash of the normalized input.", "Include multilingual normal-use regression tests."],
        ["Normalization can change formatting; it is not semantic injection detection."]),
    "encoded_input_filter": control("Encoded instruction detection", "input", ["task_constraint", "data_instruction_separation"], [],
        "Check normalized text and bounded base64, hex, and ROT13 interpretations for injection patterns.",
        ["Analyze supported encoding forms before inference.", "Keep decoding bounded and record the detected form.", "Retest ordinary encoded data to measure false blocks."],
        ["Only the declared decoding forms are covered; novel encodings can evade detection."]),
    "structured_context": control("Structured document envelopes", "prompt", ["data_instruction_separation"], ["rag"],
        "Serialize reference documents into typed JSON envelopes with explicit untrusted authority labels.",
        ["Preserve document IDs and ownership in the context envelope.", "Serialize instead of interpolating unescaped document delimiters.", "Retest delimiter breakout and document instructions."],
        ["The envelope is defense in depth and depends on the model's interpretation."]),
    "guardrails_validation": control("Guardrails AI schema gate", "output", ["output_integrity"], ["structured_output"],
        "Execute the installed Guardrails AI validate_payload implementation in an isolated environment.",
        ["Install the isolated defense tools.", "Apply the declared schema through the Guardrails validator.", "Retest complete, malformed, and duplicate-key outputs."],
        ["This integration executes schema validation; it does not claim other Guardrails Hub validators are installed."], tool="guardrails_ai"),
    "pii_redaction": control("Presidio personal-data gate", "output", ["secret_confidentiality"], [],
        "Run registered Presidio PatternRecognizers for email and phone-like identifiers, then mask matching public output.",
        ["Review whether the application may legitimately disclose personal data.", "Enable the registered pattern recognizers only for the declared use case.", "Measure legitimate disclosure failures and false positives."],
        ["Only the registered patterns run; no NLP model or comprehensive multilingual PII coverage is claimed."], tool="presidio"),
}

OUTPUT_SCHEMA = {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object",
    "properties": {"answer": {"type": "string"}, "citations": {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
                   "task": {"const": "document_qa"}}, "required": ["answer", "citations", "task"], "additionalProperties": False}
OUTPUT_VALIDATOR = Draft202012Validator(OUTPUT_SCHEMA)
INJECTION_RE = re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior|system)|(?:reveal|print|show)\s+(?:the\s+)?system\s+prompt|"
    r"(?:override|bypass)\s+(?:the\s+)?(?:policy|instructions|permissions)|\u00f6nceki.*yok\s+say|\u0259vv\u0259lki.*n\u0259z\u0259r\u0259\s+alma", re.I)


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs)


def normalize_instruction(text):
    return "".join(c for c in unicodedata.normalize("NFKC", text) if unicodedata.category(c) != "Cf")


def injection_forms(text):
    normalized = normalize_instruction(text)
    if INJECTION_RE.search(normalized):
        return ["normalized_text"]
    interpretations = [("rot13", codecs.decode(normalized, "rot13"))]
    for match in re.finditer(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{16,}={0,2}(?![A-Za-z0-9+/])", normalized):
        try:
            decoded = base64.b64decode(match.group(), validate=True).decode("utf-8")
            interpretations.append(("base64", decoded))
        except (ValueError, UnicodeError):
            pass
    for match in re.finditer(r"(?:\\x[0-9a-fA-F]{2}){8,}|\b(?:[0-9a-fA-F]{2}){8,}\b", normalized):
        try:
            interpretations.append(("hex", bytes.fromhex(match.group().replace("\\x", "")).decode("utf-8")))
        except (ValueError, UnicodeError):
            pass
    return sorted({name for name, decoded in interpretations if INJECTION_RE.search(normalize_instruction(decoded))})


def mask_secrets(text, markers):
    found = []
    for marker in markers:
        if marker["value"] in text:
            text = text.replace(marker["value"], "[REDACTED_SECRET]")
            found.append(marker["id"])
    return text, found
