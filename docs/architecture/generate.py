"""Generate the README's standalone SVG architecture figures (stdlib only)."""
from __future__ import annotations

from html import escape
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parent
INK = "#12243b"
MUTED = "#50657a"
BLUE = "#245fe8"
TEAL = "#087f82"
AMBER = "#ab6718"


class Figure:
    def __init__(self, height, title, subtitle, description, number):
        self.height = height
        self.parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="{height}" viewBox="0 0 1440 {height}" role="img" aria-labelledby="title description">
<title id="title">{escape(title)}</title><desc id="description">{escape(description)}</desc>
<defs>
  <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#718398"/></marker>
  <filter id="shadow" x="-10%" y="-15%" width="120%" height="140%"><feDropShadow dx="0" dy="3" stdDeviation="5" flood-color="#12243b" flood-opacity=".045"/></filter>
</defs>
<style>text {{font-family: Inter, 'Segoe UI', Arial, sans-serif;}} .heading {{font-weight:700;}} .tag {{font-weight:700;letter-spacing:1.2px;}}</style>
<rect width="1440" height="{height}" fill="#f7f9fc"/>
<rect x="48" y="42" width="5" height="63" rx="2" fill="{TEAL}"/>
''']
        self.text(72, 63, "AEGIS LOOP  /  ARCHITECTURE", 12, TEAL, "tag")
        self.text(72, 104, title, 32, INK, "heading")
        self.text(72, 136, subtitle, 17, MUTED)
        self.text(1326, 89, number, 32, "#b4c4d6", "heading")

    def text(self, x, y, text, size=16, color=MUTED, cls="", anchor="start"):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" class="{cls}" text-anchor="{anchor}">{escape(text)}</text>')

    def panel(self, x, y, width, height, title, color=BLUE, fill="#eef3fb"):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="20" fill="{fill}" stroke="#d7e1ed"/>')
        self.text(x + 24, y + 35, title, 13, color, "tag")

    def card(self, x, y, width, height, title, body, tag="", color=BLUE):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="14" fill="#fff" stroke="#dbe3ed" filter="url(#shadow)"/>')
        self.parts.append(f'<rect x="{x}" y="{y + 18}" width="4" height="{height - 36}" rx="2" fill="{color}"/>')
        top = y + 26
        if tag:
            self.text(x + 20, top, tag, 11, color, "tag")
            top += 29
        self.text(x + 20, top, title, 20, INK, "heading")
        top += 28
        lines = []
        for line in body:
            lines.extend(textwrap.wrap(line, width=int((width - 40) / 7.2)) or [""])
        if top + max(0, len(lines) - 1) * 23 > y + height - 13:
            raise ValueError(f"Card text exceeds height: {title}")
        for i, line in enumerate(lines):
            self.text(x + 20, top + i * 23, line, 15)

    def arrow(self, points, both=False, dashed=False):
        d = "M " + " L ".join(f"{x} {y}" for x, y in points)
        extra = ' marker-start="url(#arrow)"' if both else ""
        if dashed:
            extra += ' stroke-dasharray="6 5"'
        self.parts.append(f'<path d="{d}" fill="none" stroke="#718398" stroke-width="2" stroke-linejoin="round" marker-end="url(#arrow)"{extra}/>')

    def footer(self, text):
        self.text(48, self.height - 23, text, 13, MUTED)
        self.text(1392, self.height - 23, "AEGIS v2", 13, TEAL, "heading", "end")

    def save(self, filename):
        (ROOT / filename).write_text("\n".join(self.parts) + "\n</svg>\n", encoding="utf-8")


def system_overview():
    f = Figure(1140, "One workspace. Three model roles. Recorded evidence.",
        "A versioned application adapter connects autonomous testing to an existing inference server.",
        "Operator uses the Next.js workspace and FastAPI API. A persistent controller orchestrates Red, the target adapter and evaluation. External Red/Judge providers and an independent target API connect to it. Campaign records, a local FTS5 corpus and report artifacts are stored separately.", "01")
    f.card(48, 184, 260, 126, "Operator", ["Register scope and start.", "Review evidence and results."], "USER WORKSPACE", TEAL)
    f.card(360, 184, 420, 126, "Next.js web workspace", ["English guide, campaign pages, charts.", "Server-side /api proxy; HttpOnly session."], "PRESENTATION", TEAL)
    f.card(832, 184, 560, 126, "FastAPI + validated contracts", ["Authenticated REST, SSE, exports, workspace roles.", "Versioned targets, campaign scope and execution controls."], "APPLICATION API", BLUE)
    f.arrow([(308, 246), (360, 246)])
    f.arrow([(780, 246), (832, 246)])
    f.panel(48, 386, 860, 438, "AEGIS BACKEND  /  TRUSTED APPLICATION BOUNDARIES")
    f.panel(952, 386, 440, 438, "EXTERNAL MODEL CONNECTIONS", TEAL, "#eef7f6")
    f.card(72, 451, 812, 126, "Persistent campaign controller", ["Phases, coverage scheduling, leases, heartbeat and checkpoints.", "Recorded model operations, retries, usage and optional budgets."], "ORCHESTRATION", BLUE)
    f.card(72, 632, 236, 154, "Red agent", ["Inspect, select, compose.", "Registered library tools.", "Submit candidate."], "GENERATE", BLUE)
    f.card(356, 632, 244, 154, "Target adapter", ["Documents and retrieval.", "Policy, schemas, defenses.", "Simulated tool effects."], "EXECUTE", TEAL)
    f.card(648, 632, 236, 154, "Evaluation", ["Deterministic oracles.", "Semantic Judge.", "Utility and final pairs."], "ASSESS", BLUE)
    f.card(976, 451, 392, 126, "Red + Judge providers", ["Foundry / Azure OpenAI / compatible API.", "Separate roles and recorded requests."], "GENERATION & SEMANTIC ASSESSMENT", TEAL)
    f.card(976, 632, 392, 154, "Existing target model API", ["OpenAI-compatible chat or native Ollama.", "Local, LAN, Tailscale or HTTPS tunnel.", "Registration does not install weights."], "INFERENCE", TEAL)
    f.arrow([(1112, 310), (1112, 346), (478, 346), (478, 451)])
    for x in (190, 478, 766):
        f.arrow([(x, 577), (x, 632)])
    f.arrow([(884, 515), (976, 515)], both=True)
    f.arrow([(478, 786), (478, 846), (1172, 846), (1172, 786)], both=True)
    f.text(660, 839, "Recorded target request / response", 13)
    f.panel(48, 899, 1344, 187, "PERSISTED DATA & REVIEWABLE ARTIFACTS", TEAL, "#f0f5f7")
    f.card(72, 956, 384, 106, "Campaign / evidence store", ["SQLite/PostgreSQL; encrypted private records.", "Events, checkpoints, snapshots and hashes."], color=TEAL)
    f.card(480, 956, 412, 106, "Local attack library", ["Indexed resources, tactics and provenance.", "SQLite FTS5; isolated transformation workers."], color=BLUE)
    f.card(916, 956, 452, 106, "Reports + configuration artifacts", ["PDF, PPTX, HTML, JSON / NDJSON and ZIP.", "Final verdict, eligibility, hashes and rollback."], color=TEAL)
    f.footer("Model API hosting, application enforcement, corpus search and evidence storage have distinct responsibilities.")
    f.save("system-overview.svg")


def red_provenance():
    f = Figure(1300, "From source material to a target-specific candidate.",
        "Real tool results and server-owned provenance connect attack generation to auditable evidence.",
        "Authorized target manifest feeds the Red provider. The agent calls registered tools to select methods, search indexed resources, compose tactics and execute isolated transforms. Validated submission contains exact transformed text; the server records provenance and permits bounded target feedback.", "02")
    f.card(48, 181, 1344, 122, "Authorized target manifest + selected scope cell", ["Task policy, real tool schemas, accessible documents, language, property and writable surface.", "Foreign-tenant document bodies and private oracle/canary values are excluded."], "TRUSTED CONTEXT", TEAL)
    f.panel(48, 378, 470, 634, "RED MODEL & TOOL CONVERSATION", BLUE)
    f.panel(574, 378, 818, 634, "REGISTERED LIBRARY & ISOLATED UPSTREAM COMPONENTS", TEAL, "#eef7f6")
    f.card(72, 451, 422, 152, "Red provider", ["Generates and adapts candidates.", "Native function calls or explicit JSON mode.", "No arbitrary shell, browser or network tool."], "MODEL ROLE", BLUE)
    f.card(72, 684, 422, 156, "AEGIS tool dispatcher", ["Validates registered tool names/arguments.", "Returns actual role=tool results.", "Candidate correction and recorded replay."], "SERVER ENFORCEMENT", BLUE)
    f.arrow([(430, 303), (430, 451)])
    f.arrow([(283, 603), (283, 684)], both=True)
    f.text(310, 650, "Function call / result", 13)
    f.card(598, 451, 770, 121, "Methods and rotating bundles", ["Less-used compatible methods, source selection and resource offsets.", "list/get methods, list sources, get_attack_bundle."], "SELECT", TEAL)
    f.card(598, 615, 770, 158, "Indexed source records + tactic composition", ["SQLite FTS5 search, full-record reads, source/path/version/hash metadata.", "TensorTrust, WildTeaming, PyRIT, Garak, BIPIA and other declared imports.", "compose_attack_tactics supplies real selected tactics and guidance."], "SEARCH / READ / COMPOSE", TEAL)
    f.card(598, 816, 770, 155, "Actual local transformation outputs", ["PyRIT 32 / Garak 2 / Promptfoo 11 / DeepTeam 4 registered transforms.", "Isolated workers execute upstream APIs, not model-written code.", "insertion_token preserves exact text and supports chaining."], "TRANSFORM", TEAL)
    f.arrow([(983, 572), (983, 615)], both=True)
    f.arrow([(983, 773), (983, 816)], both=True)
    f.arrow([(494, 760), (546, 760), (546, 694), (598, 694)], both=True)
    f.card(72, 889, 422, 89, "Permitted observations", ["Target response, refusal and allowed feedback."], color=BLUE)
    f.arrow([(283, 889), (283, 840)], dashed=True)
    f.panel(48, 1073, 1344, 165, "CANDIDATE DELIVERY & INTEGRITY", TEAL, "#f0f5f7")
    f.card(72, 1125, 610, 89, "Validated submit_attack", ["Materialized payload checked against scope, depth and configured caps."], color=BLUE)
    f.card(740, 1125, 628, 89, "Server-owned red_strategy", ["Actual resources, methods, tactics, composition hashes and transform use."], color=TEAL)
    f.arrow([(494, 804), (538, 804), (538, 1041), (377, 1041), (377, 1125)])
    f.arrow([(682, 1170), (740, 1170)])
    f.footer("Source read, transformation applied, candidate accepted and target violation are separate observations.")
    f.save("red-provenance.svg")


def verification_lifecycle():
    f = Figure(1260, "Discover. Reproduce. Repair. Verify.",
        "A configuration selected in development is frozen before the independent final experiment.",
        "Versioned scope and utility baseline lead to autonomous discovery and fresh-session reproduction. Supported defense candidates are compared during development. An immutable selected configuration is tested on paired replay, unseen, adaptive and utility suites. Final verdict and matching hashes control deployment eligibility.", "03")
    for x, title, body, tag in [
        (48, "Register scope", ["Pinned target/application revision.", "Capabilities and attacker access."], "01  PREFLIGHT"),
        (394, "Establish utility", ["Registered legitimate tasks.", "Recorded normal behavior."], "02  BASELINE"),
        (740, "Generate attacks", ["Autonomous cell selection.", "Actual target execution."], "03  DISCOVERY"),
        (1086, "Reproduce effect", ["Fresh sessions and minimization.", "Evidence-backed finding."], "04  REPRODUCTION"),
    ]:
        f.card(x, 188, 302 if x != 1086 else 306, 147, title, body, tag, BLUE)
    for x in (350, 696, 1042):
        f.arrow([(x, 261), (x + 44, 261)])
    f.panel(48, 426, 600, 476, "05  DEVELOPMENT / SUPPORTED CONFIGURATIONS")
    f.card(72, 498, 552, 152, "Compare control candidates", ["A baseline / B policy / C focused / D combined.", "Applicable E encoding/provenance, F Guardrails, G Presidio.", "Configuration diffs, prerequisites and artifact hashes."], "EXECUTABLE REMEDIATION", BLUE)
    f.card(72, 701, 552, 162, "Security + legitimate-use gates", ["Related replays and shared fresh development inputs.", "Utility floor, false blocks and allowed utility drop.", "Qualification and automatic candidate selection."], "DEVELOPMENT EVIDENCE", BLUE)
    f.arrow([(348, 650), (348, 701)])
    f.arrow([(1239, 335), (1239, 381), (348, 381), (348, 426)])
    f.card(720, 426, 672, 153, "Freeze selected configuration", ["Immutable artifact/hash and target revision fixed before final generation.", "Final cases remain separated from discovery/development inputs.", "A development winner alone is not deployment approval."], "06  FREEZE", TEAL)
    f.arrow([(624, 782), (684, 782), (684, 502), (720, 502)])
    f.panel(720, 650, 672, 374, "07  FINAL BASELINE / CANDIDATE PAIRS", TEAL, "#eef7f6")
    f.arrow([(1056, 579), (1056, 650)])
    f.card(744, 720, 300, 122, "Known replay", ["Reproduced attack inputs.", "Same inputs on both configs."], color=TEAL)
    f.card(1068, 720, 300, 122, "Unseen attacks", ["New, distinct final inputs.", "Recorded generation provenance."], color=TEAL)
    f.card(744, 872, 300, 122, "Adaptive attacks", ["Permitted candidate feedback.", "Paired baseline execution."], color=TEAL)
    f.card(1068, 872, 300, 122, "Legitimate utility", ["Registered normal tasks.", "Completeness and utility gates."], color=TEAL)
    f.card(48, 942, 600, 82, "Paired protocol v4", ["Complete evaluable baseline and candidate evidence is required."], color=TEAL)
    f.panel(48, 1096, 1344, 116, "08  FINAL DECISION & ARTIFACT ELIGIBILITY", TEAL, "#f0f5f7")
    f.arrow([(1056, 1024), (1056, 1096)])
    f.text(72, 1161, "Validated in scope", 20, TEAL, "heading")
    f.text(72, 1187, "Matching selected hash/revision required for eligibility.", 15)
    f.text(618, 1161, "Rejected", 20, AMBER, "heading")
    f.text(618, 1187, "A measured requirement failed.", 15)
    f.text(1000, 1161, "Inconclusive", 20, MUTED, "heading")
    f.text(1000, 1187, "Insufficient evaluable evidence.", 15)
    f.footer("Reports preserve scope, comparisons, evidence, verdict, rollback plans and integrity hashes.")
    f.save("verification-lifecycle.svg")


if __name__ == "__main__":
    system_overview()
    red_provenance()
    verification_lifecycle()
    print("Generated 3 standalone SVG architecture figures.")
