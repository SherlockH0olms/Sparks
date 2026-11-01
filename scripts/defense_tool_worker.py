"""Execute only declared local validators; no model or provider calls."""
from __future__ import annotations
import json
import os
import sys
from importlib.metadata import version

os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["GUARDRAILS_DISABLE_TELEMETRY"] = "true"


def execute(request):
    tool = request["tool"]
    if tool == "guardrails_ai":
        from guardrails.schema.validator import validate_payload, SchemaValidationError
        try:
            validate_payload(request["payload"], request["schema"])
            valid = True
        except SchemaValidationError:
            valid = False
        return {"tool": tool, "version": version("guardrails-ai"), "valid": valid}
    if tool == "presidio":
        from presidio_analyzer import Pattern, PatternRecognizer
        patterns = [
            ("EMAIL_ADDRESS", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
            ("PHONE_NUMBER", r"(?<!\w)\+\d[\d .()-]{7,}\d(?!\w)"),
        ]
        text = request["text"]
        spans = []
        for entity, regex in patterns:
            recognizer = PatternRecognizer(supported_entity=entity, patterns=[Pattern(name=entity, regex=regex, score=0.85)])
            spans.extend(recognizer.analyze(text=text, entities=[entity]))
        for span in sorted(spans, key=lambda r: r.start, reverse=True):
            text = text[:span.start] + "[REDACTED_" + span.entity_type + "]" + text[span.end:]
        return {"tool": tool, "version": version("presidio-analyzer"), "text": text,
                "matches": [{"entity": s.entity_type, "start": s.start, "end": s.end} for s in spans]}
    raise ValueError("Unknown local defense tool")


if __name__ == "__main__":
    if "--serve" in sys.argv:
        for line in sys.stdin:
            try:
                response = execute(json.loads(line))
            except Exception as exc:
                response = {"error": type(exc).__name__}
            print(json.dumps(response, ensure_ascii=True), flush=True)
        raise SystemExit(0)
    try:
        print(json.dumps(execute(json.load(sys.stdin)), ensure_ascii=True))
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__}), file=sys.stderr)
        raise SystemExit(1)
