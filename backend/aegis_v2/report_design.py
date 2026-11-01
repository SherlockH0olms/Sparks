"""Standalone, escaped HTML and native PDF/PowerPoint evidence reports."""
from __future__ import annotations

import html
import io
from datetime import datetime, timezone
from pathlib import Path
from .report_evidence import risk_story


def text(value):
    return html.escape(str(value if value is not None else "Not measured"))


def rate(value):
    return "Not measured" if value is None else f"{value * 100:.1f}%"


def label(value):
    return str(value).replace("_", " ").capitalize()


def metric_rows(report):
    rows = []
    for run in report["verification"]:
        for suite in ("replay", "unseen", "adaptive", "utility"):
            before = run["suites"]["baseline"][suite]
            after = run["suites"]["candidate"][suite]
            field = "utility" if suite == "utility" else "asr"
            rows.append([label(suite), rate(before.get(field)), rate(after.get(field)),
                         str(after.get("valid", 0)) + " valid", label(after["status"])])
    return rows


def comparison_rows(run):
    rows = []
    for suite, paired in run.get("paired_comparisons", {}).items():
        interval = run["suites"]["candidate"][suite].get("confidence_interval")
        rows.append([label(suite), paired["valid_pairs"], paired["improved_pairs"], paired["worsened_pairs"],
            f"{paired['p_value']:.3g}", rate(interval["lower"]) + " to " + rate(interval["upper"]) if interval else "Not measured"])
    return rows


def bar_chart(before, after):
    def bar(value, y, color, name):
        width = 0 if value is None else max(0, min(1, value)) * 260
        return f'<text x="0" y="{y + 15}" fill="#576579" font-size="12">{name}</text><rect x="95" y="{y}" width="260" height="22" rx="4" fill="#edf1f5"/><rect x="95" y="{y}" width="{width:.2f}" height="22" rx="4" fill="{color}"/><text x="365" y="{y + 15}" fill="#14273b" font-size="12">{text(rate(value))}</text>'
    return '<svg viewBox="0 0 470 70" role="img" aria-label="Baseline and candidate attack success rates">' + bar(before, 4, "#e56b6f", "Baseline") + bar(after, 40, "#00a994", "Candidate") + '</svg>'


def table(headers, rows):
    return '<div class="table-wrap"><table><thead><tr>' + ''.join('<th>' + text(h) + '</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + text(v) + '</td>' for v in row) + '</tr>' for row in rows) + '</tbody></table></div>'


def evidence_html(story):
    blocks = ['<div class="evidence-story"><p class="overline">OBSERVED EVIDENCE / PLAIN-LANGUAGE REVIEW</p>',
        '<h4>What actually happened</h4><p class="evidence-result">' + text(story["observed_result"]) + '</p>',
        '<div class="evidence-facts"><article><strong>Expected behavior</strong><p>' + text(story["expected_behavior"]) + '</p></article>',
        '<article><strong>Why this is the finding</strong><p>' + text(story["interpretation"]) + '</p></article></div>',
        '<p>' + text(story["summary"]) + '</p>']
    blocks.append(table(["Step", "Evidence", "Recorded item", "Meaning"], story["proof_rows"]))
    blocks.append('<div class="evidence-quotes">')
    for quote in story["inputs"] + [{"label": "Recorded target output", **story["target_output"]}]:
        if not quote["text"]:
            continue
        blocks.append('<article><h4>' + text(quote["label"]) + '</h4><blockquote>' + text(quote["text"]) + '</blockquote>')
        blocks.append('<p class="small">' + text(("Short excerpt; " if quote["shortened"] else "Recorded text; ") +
            str(quote["original_characters"]) + ' original characters.') + '</p></article>')
    blocks.append('</div><p class="small">' + text(story["target_output"]["note"]) + '</p>')
    blocks.append('<p><strong>Source use:</strong> ' + text(', '.join(story["sources"]) or "Not recorded") +
        '; ' + text(story["resource_count"]) + ' resources, ' + text(story["tactic_count"]) + ' tactics, ' +
        text(story["transformation_count"]) + ' recorded transformations.</p>')
    blocks.append('<p class="evidence-reference">' + text(story["evidence_notice"]) + '<br>Evidence reference: ' + text(story["attempt_id"]) + '</p></div>')
    return ''.join(blocks)


def html_report(report):
    summary = report["executive_summary"]
    cover = f'<header class="cover"><div class="brand">AEGIS LOOP <span>SECURITY ASSURANCE</span></div><p class="overline">EVIDENCE REPORT / {text(report["report_revision"])}</p><h1>AI Security &amp;<br>Remediation Review</h1><p>{text(report["target"]["name"])}</p><div class="cover-meta"><span>{text(report["campaign_id"])}</span><span>{text(report["generated_label"])}</span><span>{text(label(report["state"]))}</span></div></header>'
    fixture = '<div class="banner">TEST FIXTURE: simulated model responses. These results demonstrate the workflow and do not measure a real model.</div>' if report["fixture_environment"] else ''
    cards = '<div class="cards">' + ''.join(f'<article><small>{text(name)}</small><strong>{text(value)}</strong></article>' for name, value in [
        ("Confirmed findings", summary["findings"]), ("Validated candidates", summary["validated"]),
        ("Discovery coverage", rate(report["scope"]["coverage_pct"] / 100 if report["scope"]["coverage_pct"] is not None else None)),
        ("Final valid security tests", summary["final_valid_tests"])]) + '</div>'
    body = [cover, '<main>', fixture, '<nav><a href="#summary">Decision</a><a href="#scope">Scope</a><a href="#risks">Findings &amp; remedies</a><a href="#verification">Verification</a><a href="#standards">MITRE / NIST</a><a href="#limits">Limits</a></nav>',
        '<section id="summary"><p class="overline">01 / EXECUTIVE REVIEW</p><h2>Decision and priorities</h2><p class="lead">' + text(summary["decision"]) + '</p>' + cards + '<p>' + text(summary["interpretation"]) + '</p></section>',
        '<section id="scope"><p class="overline">02 / RECORDED EXPERIMENT</p><h2>Scope and identity</h2>' + table(["Field", "Recorded value"], report["scope_rows"]) + '</section>',
        '<section id="risks"><p class="overline">03 / FINDINGS AND RISK RESPONSE</p><h2>Evidence-backed remediation</h2>']
    if not report["risk_register"]:
        body.append('<p>No reproduced findings have been recorded. Review incomplete scope and evaluability before interpreting this result.</p>')
    for risk in report["risk_register"]:
        body += ['<article class="finding"><div class="finding-top"><h3>' + text(risk["title"]) + '</h3><span class="pill">' + text(label(risk["severity"])) + '</span></div>',
            '<p class="mono">' + text(risk["id"]) + '</p><p><strong>Observed boundary:</strong> ' + text(risk["boundary"]) + '</p><p><strong>Effect:</strong> ' + text(risk["effect"]) + '</p>',
            '<p><strong>Impact:</strong> ' + text(risk["impact_rationale"]) + '</p><p><strong>Reproduction:</strong> ' + text(rate(risk["reproduction_rate"])) + '; evidence: ' + text(risk["original_attempt_id"]) + '</p>',
            '<p><strong>Disposition:</strong> ' + text(risk["disposition"]) + '</p>', evidence_html(risk_story(risk)),
            '<h4>Diagnosis and chosen intervention</h4><p>' + text(risk["diagnosis"]) + '</p>']
        if risk["selected_candidate"]:
            selected = risk["selected_candidate"]
            body += ['<p><strong>Candidate:</strong> ' + text(selected["label"]) + '</p><details><summary>Technical configuration and fingerprint</summary><p class="mono">Artifact SHA-256: ' + text(selected["artifact"]["hash"]) + '</p><pre>' + text(selected["diff"] or "No configuration changes") + '</pre></details>']
        body.append(table(["Candidate", "Controls", "Development verdict", "Attack success", "Normal-use pass rate"], risk["candidate_rows"]))
        body.append('<h4>Deployment and rollback</h4><ol>' + ''.join('<li>' + text(step) + '</li>' for step in risk["deployment_steps"]) + '</ol><p><strong>Owner:</strong> Application owner. Production application review is required before deployment.</p>')
        body.append('<p><strong>Rollback:</strong> ' + text(risk["rollback_guidance"]) + '</p><h4>Remaining limitations</h4><ul>' + ''.join('<li>' + text(item) + '</li>' for item in risk["residual_risks"]) + '</ul>')
        body.append('</article>')
    body += ['</section><section id="verification"><p class="overline">04 / PAIRED VALIDATION</p><h2>Security and useful behavior</h2>']
    if not report["verification"]:
        body.append('<p>No final candidate verification is available.</p>')
    for run in report["verification"]:
        body.append('<article class="verification"><h3>' + text(run["id"]) + '</h3><p>Final verdict: <strong>' + text(label(run["verdict"])) + '</strong></p>')
        for suite in ("replay", "unseen", "adaptive"):
            before = run["suites"]["baseline"][suite]; after = run["suites"]["candidate"][suite]
            body.append('<div class="chart"><h4>' + text(label(suite)) + '</h4>' + bar_chart(before.get("asr"), after.get("asr")))
            interval = after.get("confidence_interval")
            if interval:
                body.append('<p class="small">Candidate: ' + text(after["violations"]) + ' violations / ' + text(after["valid"]) + ' valid tests. Descriptive 95% Wilson interval: ' + text(rate(interval["lower"])) + ' to ' + text(rate(interval["upper"])) + '.</p>')
            body.append('</div>')
        body.append(table(["Suite", "Baseline", "Candidate", "Valid candidate tests", "Status"], metric_rows({"verification": [run]})))
        body.append(table(["Suite", "Valid pairs", "Improved", "Worsened", "Exploratory p-value", "Candidate 95% Wilson interval"], comparison_rows(run)))
        body.append('<p class="small">Paired tests are exploratory. Related generated cases may be correlated; these statistics do not establish population-wide security.</p>')
        diversity = run.get("attack_diversity", {})
        body.append('<p><strong>Final generation diversity:</strong> ' + text(diversity.get("distinct_methods", "Not recorded")) + ' methods; ' + text(diversity.get("distinct_resources", "Not recorded")) + ' source resources. Library size is separate from executed tests.</p>')
        body.append(table(["Family", "Language", "Surface", "Fresh valid / required", "Adaptive valid / required"], [
            [label(c["family"]), c["language"], label(c["surface"]), str(c["unseen"]["candidate"]["valid"]) + ' / ' + str(c["unseen"]["candidate"]["minimum"]),
             str(c["adaptive"]["candidate"]["valid"]) + ' / ' + str(c["adaptive"]["candidate"]["minimum"])] for c in run.get("coverage_cells", [])]))
        body.append('<p class="mono">Candidate: ' + text(run["candidate_hash"]) + '<br>Protocol: ' + text(run["protocol_revision"]) + '<br>Test-set revision: ' + text(run["set_revision"]) + '</p></article>')
    body += ['</section><section id="standards"><p class="overline">05 / FRAMEWORK CROSSWALK</p><h2>MITRE ATLAS and NIST evidence</h2><p>' + text(report["standards"]["disclaimer"]) + '</p>',
        table(["Finding", "ATLAS technique", "Mechanism", "Mapping reason"], [[r["id"], r["atlas"].get("technique_id") or "Unmapped", r["atlas"]["name"], r["atlas"].get("reason", "")] for r in report["risk_register"]]),
        table(["Framework", "Reference", "Outcome", "Evidence status"], [[r["framework"], r["id"], r["name"], label(r["status"])] for r in report["standards"]["rows"]]),
        '<p>Unassessed domains: ' + text('; '.join(report["standards"]["unassessed_domains"])) + '</p></section>',
        '<section><p class="overline">06 / ACTUAL CONSUMPTION</p><h2>Resources and execution</h2>' + table(["Resource", "Configured limit", "Used", "Reserved"], report["resource_rows"]) + '</section>',
        '<section id="limits"><p class="overline">07 / INTERPRETATION</p><h2>Gaps, uncertainty and next actions</h2><ul>' + ''.join('<li>' + text(x) + '</li>' for x in report["limitations"]) + '</ul>',
        '<h3>Authoritative references</h3><ul>' + ''.join('<li><a href="' + text(url) + '">' + text(url) + '</a></li>' for url in report["references"] if url.startswith("https://")) + '</ul></section>',
        '<footer>AEGIS LOOP / ' + text(report["report_revision"]) + '<br>Report content fingerprint: <span class="mono">' + text(report["content_hash"]) + '</span></footer></main>']
    css = 'body{margin:0;background:#edf2f6;color:#172b40;font:15px/1.65 Arial,sans-serif}*{box-sizing:border-box}.cover{padding:58px max(6vw,24px);background:linear-gradient(120deg,#0c1d31,#183951);color:white}.brand{font-size:24px;letter-spacing:2px}.brand span{display:block;color:#69dfd0;font-size:10px;letter-spacing:4px}.overline{font-size:11px;letter-spacing:2px;color:#168a80;font-weight:bold}.cover .overline{color:#69dfd0;margin-top:45px}h1{font-size:clamp(34px,5vw,60px);line-height:1.1;letter-spacing:-2px}h2{font-size:29px;line-height:1.25}h3{font-size:21px}h4{font-size:16px;margin-bottom:8px}.cover-meta{display:flex;gap:20px;flex-wrap:wrap;font-size:12px;color:#b6c9d9}main{max-width:1150px;margin:auto;padding:28px}nav{display:flex;gap:22px;flex-wrap:wrap;background:white;padding:20px;border-radius:12px}a{color:#087f8c}section{margin:30px 0;background:white;padding:30px;border:1px solid #dce4eb;border-radius:12px;overflow-wrap:anywhere}.lead{font-size:20px}.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:24px 0}.cards article{background:#eff7f6;padding:20px;border-radius:9px}.cards small{display:block;color:#576579}.cards strong{font-size:32px;color:#007e72}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:12px;margin:18px 0}th,td{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid #dde5eb;overflow-wrap:anywhere}th{background:#f0f4f8;color:#36536a;font-size:11px}.finding,.verification{border-top:3px solid #19a998;margin:25px 0;padding:24px;background:#fafcfd;border-radius:8px}.finding-top{display:flex;justify-content:space-between;align-items:center;gap:16px}.pill{font-size:11px;font-weight:bold;background:#fff0eb;color:#a04d35;padding:6px 10px;border-radius:20px}.mono,pre{font-family:Consolas,monospace;font-size:11px;overflow-wrap:anywhere}pre{white-space:pre-wrap;background:#edf2f6;padding:18px;border-radius:7px}.chart{max-width:600px;margin:20px 0}.chart svg{width:100%;font-family:Arial,sans-serif}.small{font-size:12px;color:#576579}.banner{padding:18px;border:1px solid #e6b44e;background:#fff5d9;margin-bottom:24px}footer{padding:25px;color:#576579;font-size:11px}@media(max-width:650px){main{padding:12px}section{padding:18px}.cards{grid-template-columns:1fr 1fr}.cards article{padding:13px}.finding,.verification{padding:15px}nav{gap:12px}.cover-meta{display:block}.cover-meta span{display:block}}@media print{body{background:white}.cover{background:#0c1d31!important;print-color-adjust:exact}main{padding:0}nav{display:none}section{border:0;break-inside:auto}.finding,.verification{break-inside:avoid}a{color:inherit}.cards{print-color-adjust:exact}}'
    css += '.evidence-story{margin:24px 0;padding:22px;background:#fff;border:1px solid #d8e5ec;border-radius:10px}.evidence-result{font-size:19px;font-weight:bold;color:#16364c}.evidence-facts,.evidence-quotes{display:grid;grid-template-columns:1fr 1fr;gap:16px}.evidence-facts article{background:#edf6f5;border-radius:8px;padding:18px}.evidence-quotes article{background:#f3f6f9;border-radius:8px;padding:18px}blockquote{margin:12px 0;padding-left:14px;border-left:3px solid #169b90;font:14px/1.7 Arial,sans-serif;color:#3c5167}.evidence-reference{background:#eef3f7;padding:14px;font-size:12px;border-radius:6px}@media(max-width:650px){.evidence-facts,.evidence-quotes{grid-template-columns:1fr}.evidence-story{padding:14px}}'
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>AEGIS AI Security &amp; Remediation Review</title><style>' + css + '</style></head><body>' + ''.join(body) + '</body></html>'


def pdf_report(report):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.graphics.shapes import Drawing, Rect, String

    buffer = io.BytesIO()
    font = "Helvetica"
    for regular, bold in ((Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),
                          (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))):
        if regular.exists():
            if "AegisUnicode" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("AegisUnicode", str(regular)))
                pdfmetrics.registerFont(TTFont("AegisUnicodeBold", str(bold if bold.exists() else regular)))
                pdfmetrics.registerFontFamily("AegisUnicode", normal="AegisUnicode", bold="AegisUnicodeBold",
                                              italic="AegisUnicode", boldItalic="AegisUnicodeBold")
            font = "AegisUnicode"
            break
    navy, teal = colors.HexColor("#132e45"), colors.HexColor("#087f82")
    styles = getSampleStyleSheet()
    for name, size, leading in (("BodyText", 10, 14), ("Title", 27, 33), ("Heading1", 23, 29),
                               ("Heading2", 15, 20), ("Heading3", 11, 16)):
        styles[name].fontName = font
        styles[name].fontSize = size
        styles[name].leading = leading
        styles[name].textColor = navy
        styles[name].spaceAfter = 9
    styles.add(ParagraphStyle("AegisSmall", fontName=font, fontSize=8, leading=11,
        textColor=colors.HexColor("#52667a"), wordWrap="CJK", spaceAfter=4))
    styles.add(ParagraphStyle("AegisQuote", fontName=font, fontSize=9, leading=13,
        textColor=colors.HexColor("#40566b"), spaceAfter=0))
    styles.add(ParagraphStyle("AegisTag", fontName=font, fontSize=8, leading=12, textColor=teal, spaceAfter=7))
    styles.add(ParagraphStyle("AegisCover", parent=styles["Title"], textColor=colors.white, spaceAfter=12))
    styles.add(ParagraphStyle("AegisCoverSmall", parent=styles["BodyText"], textColor=colors.HexColor("#c7e4e7")))
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=44, leftMargin=44, topMargin=52, bottomMargin=44,
        title="AEGIS AI Application Security Review", author="AEGIS Loop")
    width = doc.width
    story = []

    def p(value, style="BodyText"):
        return Paragraph(text(value).replace("\n", "<br/>"), styles[style])

    def section(name, tag=None, page=False):
        if page:
            story.append(PageBreak())
        if tag:
            story.append(p(tag, "AegisTag"))
        story.append(p(name, "Heading1"))

    def grid(headers, rows, ratios=None):
        if not rows:
            story.append(p("No additional structured records in this excerpt.", "AegisSmall"))
            return
        ratios = ratios or [1] * len(headers)
        col_widths = [width * r / sum(ratios) for r in ratios]
        data = [[p(h, "AegisSmall") for h in headers]] + [[p(v, "AegisSmall") for v in row] for row in rows]
        table_ = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
        table_.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5f3f1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8fb")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LINEBELOW", (0, 0), (-1, -1), .3, colors.HexColor("#dde6ec"))]))
        story.extend([table_, Spacer(1, 9)])

    def callout(title, value, fill="#edf6f5"):
        box = Table([[p(title, "Heading3")], [p(value)]], colWidths=[width])
        box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(fill)),
            ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
        story.extend([box, Spacer(1, 10)])

    def quote(title, item):
        if not item["text"]:
            return
        note = ("Short excerpt" if item["shortened"] else "Recorded text") + "; " + str(item["original_characters"]) + " original characters."
        box = Table([[p(title, "Heading3")], [p(item["text"], "AegisQuote")], [p(note, "AegisSmall")]], colWidths=[width])
        box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f4f8")),
            ("LINEBEFORE", (0, 0), (0, -1), 2, teal),
            ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        story.extend([KeepTogether([box]), Spacer(1, 9)])

    cover = Table([[p("AEGIS LOOP / APPLICATION SECURITY", "AegisCoverSmall")],
        [p("AI Security &\nRemediation Review", "AegisCover")],
        [p(report["target"]["name"] + "  /  " + report["target"]["model"], "AegisCoverSmall")],
        [p(report["generated_label"], "AegisCoverSmall")]], colWidths=[width])
    cover.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), navy),
        ("LEFTPADDING", (0, 0), (-1, -1), 22), ("RIGHTPADDING", (0, 0), (-1, -1), 22),
        ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
    story += [cover, Spacer(1, 26)]
    if report["fixture_environment"]:
        callout("TEST FIXTURE", "Simulated model responses demonstrate the workflow; they do not measure a live model.", "#fff4df")
    story += [p("01 / EXECUTIVE DECISION", "AegisTag"), p(report["executive_summary"]["decision"], "Heading2"),
        p(report["executive_summary"]["interpretation"]), Spacer(1, 10)]
    grid(["Reproduced findings", "Validated candidates", "Valid final security tests"], [[report["executive_summary"]["findings"],
        report["executive_summary"]["validated"], report["executive_summary"]["final_valid_tests"]]])
    if report["risk_register"]:
        callout("Primary observed risk", report["risk_register"][0]["impact_rationale"])
        story.append(p("The finding pages show expected behavior, the actual application effect, short input/output quotations, and the supported intervention."))
    else:
        callout("Reading this result", "No reproduced finding is recorded. Consult scope coverage and valid observations before interpreting the absence of findings.")
    story.append(p("Complete technical evidence is a separate JSON/NDJSON export. This report presents the decision and supporting facts in readable form.", "AegisSmall"))

    section("Scope and evaluation method", "02 / RECORDED EXPERIMENT", page=True)
    grid(["Scope", "Recorded value"], [row for row in report["scope_rows"] if row[0] != "Target snapshot"], [1, 3])
    story += [p("How to read the measurements", "Heading2"),
        p("Attack success is violations divided by valid security observations. Utility is the fraction of legitimate tasks passed. Missing or failed executions cannot establish a successful defense."),
        p("The registered adapter supplies documents, response contracts and simulated tools around the model API. Application-layer findings do not imply that model weights or unrelated production tools were modified."),
        p("Reproduction uses fresh sessions. Selected controls are frozen before paired final replay, unseen, adaptive and normal-use testing.")]

    for index, risk in enumerate(report["risk_register"], 1):
        evidence = risk_story(risk)
        section(risk["title"], f"03 / FINDING {index:02d} / OBSERVED EVIDENCE", page=True)
        grid(["Severity", "Active tenant", "Reproduction", "Disposition"], [[label(risk["severity"]), evidence["tenant"], rate(risk["reproduction_rate"]), risk["disposition"]]], [1, 1.5, 1.3, 1.5])
        callout("What actually happened", evidence["observed_result"])
        story += [p("Expected behavior", "Heading3"), p(evidence["expected_behavior"]),
            p("Why this is the finding", "Heading3"), p(evidence["interpretation"])]
        grid(["Step", "Evidence", "Recorded item", "Meaning"], evidence["proof_rows"], [1, 1.5, 2, 2])
        for item in evidence["inputs"]:
            quote(item["label"], item)
        quote("Recorded target output", evidence["target_output"])
        story.append(p(evidence["target_output"]["note"], "AegisSmall"))
        story.append(p("Source use: " + (", ".join(evidence["sources"]) or "Not recorded") + "; method: " + evidence["method"] +
            "; " + str(evidence["resource_count"]) + " resources, " + str(evidence["tactic_count"]) + " tactics, " +
            str(evidence["transformation_count"]) + " recorded transformations.", "AegisSmall"))
        story.append(p("Evidence reference: " + str(evidence["attempt_id"]) + ". " + evidence["evidence_notice"], "AegisSmall"))

        section("Remediation and safe rollout", f"04 / FINDING {index:02d} / CONTROL COMPARISON", page=True)
        story += [p(risk["diagnosis"]), p("Development candidate comparison", "Heading2")]
        grid(["Candidate", "Controls", "Verdict", "Attack success", "Utility"], risk["candidate_rows"], [1, 2.4, 1.4, 1.1, 1])
        selected = risk["selected_candidate"]
        if selected:
            callout("Selected development intervention", "Candidate " + selected["label"] + ". Final disposition: " + risk["disposition"] +
                ". Deployment eligibility requires scoped final validation of the same selected artifact and target revision.")
        story.append(p("Implementation steps", "Heading2"))
        for number, item in enumerate(risk["deployment_steps"], 1):
            story.append(p(str(number) + ". " + item))
        callout("Rollback", risk["rollback_guidance"])
        story.append(p("Control boundaries", "Heading2"))
        for item in risk["residual_risks"]:
            story.append(p("• " + item))

    section("Security and normal-use verification", "05 / PAIRED FINAL EVIDENCE", page=True)
    if not report["verification"]:
        story.append(p("No final candidate verification is included in this report."))
    for run in report["verification"]:
        callout("Final verdict: " + label(run["verdict"]), "Baseline and selected candidate are tested on the same inputs. Verdicts depend on valid security and legitimate-use evidence.")
        grid(["Suite", "Baseline", "Candidate", "Candidate valid", "Status"], metric_rows({"verification": [run]}), [1.2, 1.1, 1.1, 1.1, 1.2])
        for suite in ("replay", "unseen", "adaptive"):
            before, after = run["suites"]["baseline"][suite], run["suites"]["candidate"][suite]
            chart = Drawing(width, 66)
            chart.add(String(0, 55, label(suite) + " attack success", fontName=font, fontSize=10, fillColor=teal))
            for j, (value, name, color) in enumerate([(before.get("asr"), "Baseline", "#df7476"), (after.get("asr"), "Candidate", "#119889")]):
                y = 30 - j * 25
                chart.add(String(0, y + 5, name, fontName=font, fontSize=9))
                chart.add(Rect(78, y, 285, 17, fillColor=colors.HexColor("#eaf0f5"), strokeColor=None))
                chart.add(Rect(78, y, 285 * (value or 0), 17, fillColor=colors.HexColor(color), strokeColor=None))
                chart.add(String(377, y + 5, rate(value), fontName=font, fontSize=9))
            story.append(KeepTogether([chart]))
        grid(["Suite", "Valid pairs", "Improved", "Worsened", "p-value", "95% interval"], comparison_rows(run), [1.4, 0.9, 1, 1, 1, 2])
        story.append(p("Paired comparisons and confidence intervals are descriptive; related generated inputs may be correlated. Lower attack success and higher utility are preferable.", "AegisSmall"))
        grid(["Family", "Language", "Surface", "Fresh valid / required", "Adaptive valid / required"], [
            [label(c["family"]), c["language"], label(c["surface"]), str(c["unseen"]["candidate"]["valid"]) + " / " + str(c["unseen"]["candidate"]["minimum"]),
             str(c["adaptive"]["candidate"]["valid"]) + " / " + str(c["adaptive"]["candidate"]["minimum"])] for c in run.get("coverage_cells", [])], [1.7, 0.8, 1.5, 1.5, 1.5])
        story.append(p("Verification reference: " + run["id"], "AegisSmall"))

    section("MITRE ATLAS and NIST evidence", "06 / FRAMEWORK CROSSWALK", page=True)
    story.append(p(report["standards"]["disclaimer"]))
    grid(["Finding", "ATLAS technique", "Established mechanism"], [[r["title"], r["atlas"].get("technique_id") or "Unmapped", r["atlas"]["name"]] for r in report["risk_register"]], [2, 1, 2])
    grid(["Framework", "Reference", "Outcome", "Evidence status"], [[r["framework"], r["id"], r["name"], label(r["status"])] for r in report["standards"]["rows"]], [1.2, 1.2, 2.5, 1.4])
    story.append(p("Mappings provide supporting evidence for the tested boundaries; they are not a certification or a complete organizational compliance audit.", "AegisSmall"))

    section("Resources and evidence references", "07 / AUDIT APPENDIX", page=True)
    grid(["Resource", "Limit", "Used", "Reserved"], report["resource_rows"], [1.6, 1, 1, 1])
    story.append(p("Interpretation boundaries", "Heading2"))
    for item in report["limitations"]:
        story.append(p("• " + item, "AegisSmall"))
    story.append(p("Evidence manifest", "Heading2"))
    grid(["Reference", "Recorded value"], [["Campaign", report["campaign_id"]], ["Target revision", report["target"]["revision"]],
        ["Report revision", report["report_revision"]], ["Report fingerprint", report["content_hash"]]], [1, 3])
    story.append(p("Full attack payloads, target outputs and source hashes belong to the separate machine-readable evidence export. This PDF quotes bounded excerpts and preserves the original verdicts.", "AegisSmall"))
    for url in report["references"]:
        story.append(p(url, "AegisSmall"))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(teal)
        canvas.rect(44, A4[1] - 29, 21, 3, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#52667a"))
        canvas.setFont(font, 8)
        canvas.drawString(74, A4[1] - 30, "AEGIS LOOP / APPLICATION SECURITY REVIEW")
        canvas.drawString(44, 23, report["target"]["model"] + " / " + report["generated_label"])
        canvas.drawRightString(A4[0] - 44, 23, "Page " + str(doc.page))
        canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()


def powerpoint_report(report):
    import textwrap
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    deck = Presentation(); deck.slide_width = Inches(13.333); deck.slide_height = Inches(7.5)
    dark = RGBColor.from_string("0C1D31"); white = RGBColor.from_string("EEF5FA"); accent = RGBColor.from_string("69DFD0")
    def slide(title, lines, eyebrow="AEGIS LOOP / SECURITY REVIEW"):
        # Paginate content using a conservative visible line budget.
        batches, batch, used = [], [], 0
        for line in lines:
            parts = textwrap.wrap(str(line), width=100, break_long_words=True) or [""]
            for offset in range(0, len(parts), 9):
                part = "\n".join(parts[offset:offset + 9])
                cost = len(parts[offset:offset + 9]) + 1
                if batch and used + cost > 13:
                    batches.append(batch); batch, used = [], 0
                batch.append(part); used += cost
        if batch:
            batches.append(batch)
        if len(batches) > 1:
            pages = [slide(title + (" (continued)" if i else ""), b, eyebrow) for i, b in enumerate(batches)]
            return pages[0]
        lines = batches[0] if batches else []
        page = deck.slides.add_slide(deck.slide_layouts[6]); page.background.fill.solid(); page.background.fill.fore_color.rgb = dark
        def box(x, y, w, h, size, color):
            frame = page.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)).text_frame
            frame.word_wrap = True
            return frame
        frame = box(.6, .35, 12, .4, 11, accent); frame.text = eyebrow; frame.paragraphs[0].font.size = Pt(11); frame.paragraphs[0].font.color.rgb = accent
        frame = box(.6, 1.0, 12, 1.0, 30, white); frame.text = title
        frame.paragraphs[0].font.size = Pt(30); frame.paragraphs[0].font.bold = True; frame.paragraphs[0].font.color.rgb = white
        frame = box(.7, 2.05, 11.9, 4.7, 19, white)
        for index, line in enumerate(lines):
            p = frame.paragraphs[0] if index == 0 else frame.add_paragraph(); p.text = str(line); p.font.size = Pt(18); p.font.color.rgb = white; p.space_after = Pt(14)
        foot = box(.6, 7.02, 12, .25, 9, white); foot.text = "AEGIS LOOP  |  " + report["generated_label"] + "  |  " + str(len(deck.slides)); foot.paragraphs[0].font.size = Pt(9); foot.paragraphs[0].font.color.rgb = RGBColor.from_string("A9BDCE")
        return page
    slide("AI Security & Remediation Review", [report["target"]["name"], report["campaign_id"], report["executive_summary"]["decision"],
        "TEST FIXTURE: simulated models; no real-model resilience claim." if report["fixture_environment"] else "Scoped evidence from the recorded target and protocol."])
    slide("Executive decision", [report["executive_summary"]["decision"],
        f'Confirmed findings: {report["executive_summary"]["findings"]}  |  Validated candidates: {report["executive_summary"]["validated"]}',
        f'Final valid security tests: {report["executive_summary"]["final_valid_tests"]}', report["executive_summary"]["interpretation"]])
    slide("Target and scope", [str(name) + ": " + str(value) for name, value in report["scope_rows"]])
    for risk in report["risk_register"]:
        slide(risk["title"], ["Severity: " + label(risk["severity"]), "Boundary: " + risk["boundary"], "Effect: " + risk["effect"],
            "Reproduction: " + rate(risk["reproduction_rate"]), "Disposition: " + risk["disposition"], "ATLAS: " + str(risk["atlas"].get("technique_id") or "Unmapped")], "FINDING / " + risk["id"])
        evidence = risk_story(risk)
        slide("What actually happened", ["Observed: " + evidence["observed_result"],
            "Expected: " + evidence["expected_behavior"], evidence["interpretation"]], "EVIDENCE / " + risk["title"])
        slide("Attack and recorded target output", [item["label"] + " (short excerpt): " + item["text"] for item in evidence["inputs"]] +
            (["Target output (short excerpt): " + evidence["target_output"]["text"]] if evidence["target_output"]["text"] else []) +
            ["Full inputs, output and source records: separate JSON/NDJSON evidence export."], "RECORDED QUOTATIONS")
        slide("Remediation and deployment", [risk["diagnosis"]] + risk["deployment_steps"] + ["Rollback: " + risk["rollback_guidance"]], "REMEDIATION / " + risk["id"])
        slide("Candidate comparison", [" | ".join(row) for row in risk["candidate_rows"]], "CANDIDATES / " + risk["id"])
    for run in report["verification"]:
        page = slide("Baseline vs selected candidate", ["Final verdict: " + label(run["verdict"]), "Each suite uses valid paired observations."], "VERIFICATION / " + run["id"])
        for index, suite in enumerate(("replay", "unseen", "adaptive")):
            y = 3.2 + index * .9
            field = page.shapes.add_textbox(Inches(.8), Inches(y), Inches(2), Inches(.6)).text_frame
            field.text = label(suite); field.paragraphs[0].font.size = Pt(15); field.paragraphs[0].font.color.rgb = white
            for offset, group, color in ((0, "baseline", "E56B6F"), (.3, "candidate", "00A994")):
                value = run["suites"][group][suite].get("asr")
                shape = page.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(3), Inches(y + offset), Inches(max(.015, (value or 0) * 6)), Inches(.22))
                shape.fill.solid(); shape.fill.fore_color.rgb = RGBColor.from_string(color); shape.line.fill.background()
                frame = page.shapes.add_textbox(Inches(9.4), Inches(y + offset), Inches(3), Inches(.3)).text_frame
                frame.text = label(group) + " " + rate(value); frame.paragraphs[0].font.size = Pt(13); frame.paragraphs[0].font.color.rgb = white
    atlas_rows = []
    for risk in report["risk_register"]:
        atlas = risk["atlas"]
        atlas_rows += [risk["id"] + " | " + str(atlas.get("technique_id") or "Unmapped") + " | " + atlas["name"],
                       "Mapping reason: " + atlas.get("reason", "No supported mechanism was established.")]
    slide("MITRE ATLAS evidence crosswalk", atlas_rows + [
        "Unmapped findings retain their evidence; an unsupported ATLAS technique is never inferred."] if atlas_rows else [
        "There are no confirmed findings to map to a supported MITRE ATLAS technique."], "FRAMEWORK EVIDENCE")
    rows = report["standards"]["rows"]
    for run in report["verification"]:
        slide("Paired evidence and uncertainty", [" | ".join(str(v) for v in row) for row in comparison_rows(run)] + [
            "Columns: suite, valid pairs, improved, worsened, exploratory p-value, candidate 95% Wilson interval.",
            "Generated cases can be correlated; this evidence does not certify population-wide resilience."], "STATISTICS / " + run["id"])
    for offset in range(0, len(rows), 5):
        slide("NIST evidence crosswalk", [r["id"] + " - " + r["name"] + " (" + label(r["status"]) + ")" for r in rows[offset:offset + 5]] + [report["standards"]["disclaimer"]])
    for offset in range(0, len(report["limitations"]), 5):
        slide("Uncertainty and next actions", report["limitations"][offset:offset + 5])
    slide("Evidence and reproducibility", ["Target revision: " + report["target"]["revision"], "Report revision: " + report["report_revision"],
        "Download the JSON/NDJSON evidence package for complete execution records.", "Report fingerprint: " + report["content_hash"]])
    buffer = io.BytesIO(); deck.save(buffer); return buffer.getvalue()
