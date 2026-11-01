# Remediation and model deployment connections

The target is an existing model API server. AEGIS evaluates a versioned application adapter around that model: task policy, registered document retrieval, output contracts, and simulated email/export gateways. A remediation configuration changes these application boundaries. It does not modify model weights or automatically patch an unrelated application's internal tools.

## Connect a deployed model

On **Targets**, select **Add target**, choose a deployment type and API format, and replace the example address with your actual server address.

| Deployment | Example OpenAI-compatible API base | Requirement |
|---|---|---|
| This computer | `http://127.0.0.1:11434/v1` | The model server runs on the platform backend host. |
| LAN | `http://192.168.1.50:8000/v1` | The backend can reach the private IP and model port. |
| Tailscale | `http://100.64.0.20:8000/v1` or a `.ts.net` hostname | The backend joins the same tailnet and has route access. |
| Cloudflare Tunnel | `https://model.example.com/v1` | The tunnel forwards requests to the model API. |
| ngrok | `https://your-model.ngrok-free.app/v1` | Use the current HTTPS forwarding address. |
| Kaggle / Colab | The notebook's Cloudflare or ngrok HTTPS base | Start an API model server and keep the notebook and tunnel alive. |
| Custom | `https://model.example.com/inference/v1` | The endpoint implements a supported API protocol. |

**OpenAI-compatible chat** sends non-streaming requests to `BASE/chat/completions`. **Native Ollama** sends non-streaming requests to `SERVER_ROOT/api/chat`; enter the server root without `/v1`. Hosting labels do not translate arbitrary RPC protocols. Add an API adapter for a server that implements neither format. Model-native tool calling requires support in the deployed model and server.

Model authentication can use `AEGIS_LOCAL_API_KEY`, no key, or a target-specific key. Cloudflare Access has separate client ID and client secret fields. Explicitly selecting no authentication disables environment inheritance. Credentials are encrypted in the private target snapshot; public metadata contains authentication booleans. Review JSON masks entered values, and report/evidence exports exclude connection credentials, including administrator raw exports. ngrok and notebook requests include `ngrok-skip-browser-warning: 1`.

Supply the exact model identifier and a pinned weight revision. Review documents, tenant ownership, capabilities, normal-use test cases, starting controls, allowed attack surfaces, and feedback. Save, then select **Test connection**. Connection checks run from the backend, so browser access to a URL alone does not establish backend connectivity.

Private LAN ranges, Tailscale addresses and `.ts.net` names are supported. Maintainers can register public HTTPS targets when `AEGIS_ALLOW_REMOTE_TARGETS=true`. Additional private hostnames use `AEGIS_LOCAL_ALLOWED_HOSTS`. URLs must omit embedded credentials, queries, fragments, and the final chat route.

After transient target errors, each retry is recorded and charged. Exhausted retries pause the campaign with its checkpoint. Restore the same endpoint, test connectivity, then select **Resume**. Completed turns and simulated tool effects remain recorded; they are not repeated. A changed URL requires a new versioned target and campaign. An outage cannot establish a passing security result.

An ngrok `404` with `ERR_NGROK_3200` is an offline tunnel and follows this recovery path. An ordinary missing model or API route remains a configuration error. Do not interpret an unavailable target as a successful defense.

## Executable controls and researched components

The live **Repair Lab** catalog lists each control's implementation, prerequisites, source, availability, and limitations.

| Layer | Implemented controls |
|---|---|
| Input | Injection pattern detection, Unicode normalization, supported encoded-instruction detection |
| Policy / context | Explicit task policy, untrusted document boundary, structured JSON document envelopes |
| Retrieval | Tenant authorization before ranking |
| Tool gateway | Trusted authorization and complete argument schemas |
| Output | Complete response schema, protected marker gate, citation ownership, Guardrails schema validation, Presidio pattern redaction |

There are 14 controls. Repair candidates include baseline A, task policy B, focused boundary C, and combined D. Relevant findings can add E encoding/provenance, F Guardrails validation, and G Presidio redaction. Controls with unavailable dependencies or incompatible capabilities cannot qualify. Each candidate has an immutable configuration artifact, diagnosis, deployment steps, rollback configuration, framework references, and residual risks.

| Component | Integration status | Executed scope | Authoritative source |
|---|---|---|---|
| python-jsonschema 4.26.0 | Integrated in application | Draft 2020-12 response and tool argument validation | [Documentation](https://python-jsonschema.readthedocs.io/) |
| Guardrails AI 0.11.0 | Isolated local integration | Actual `validate_payload` schema validator; no claim of installed Hub validators | [Project](https://github.com/guardrails-ai/guardrails) |
| Presidio Analyzer 2.2.366 | Isolated local integration | Actual `PatternRecognizer` for registered email and phone patterns; no NLP model | [Microsoft documentation](https://microsoft.github.io/presidio/) |
| NeMo Guardrails | Researched reference | No executable integration in this release | [NVIDIA project](https://github.com/NVIDIA/NeMo-Guardrails) |
| LLM Guard | Researched reference | No executable integration in this release | [Project](https://github.com/protectai/llm-guard) |
| OWASP prevention guidance | Design reference | Defense boundaries, layered controls, and normal-use regression testing | [Cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html) |

Optional tools run locally in `.venv-defensetools`, separately from the application environment. Persistent serialized workers reuse imports. Failed or timed-out validator calls remain execution errors. Tool availability comes from verified installation probes in `.runtime/defense-tools.json`.

```powershell
# Install isolated tools; supply Python 3.12 if it is not already available.
.\.venv-win\Scripts\python.exe scripts\setup_defense_tools.py --python "C:\path\to\Python312\python.exe"
# Verify an existing installation without installing packages.
.\.venv-win\Scripts\python.exe scripts\setup_defense_tools.py --index-only
```

## Test depth and interpretation

Available source material and executed evidence are separate. A library of 254,368 resources can feed a small or large experiment; its size does not establish how many independent cases ran, whether the target failed, or whether a remedy passed.

| Protocol | Discovery valid tests per cell | Reproduction trials | Development fresh per cell | Final fresh per cell | Adaptive per cell | Utility repetitions | Final scope |
|---|---:|---:|---:|---:|---:|---:|---|
| Smoke | 1 | 3 | 0 | 3 | 2 | 1 | Original finding cell |
| Standard | 5 | 5 | 8 | 30 | 12 | 2 | All applicable same-property cells |
| Deep | 10 | 10 | 20 | 100 | 40 | 3 | All applicable same-property cells |
| Custom | Operator settings | Operator settings | Operator settings | Operator settings | Operator settings | Operator settings | Operator choice |

Cells combine a security property, applicable attack family, language, and surface. Supported families and capabilities determine applicability; the protocol does not imply every Cartesian combination is meaningful. Property verification rotates through its cells to balance fresh/adaptive generation. **Estimate test coverage** shows applicable cells and planned cases before starting. Counts are per selected finding group. Final pairs run each input on baseline and candidate, adding two attempts; multiple turns and Red tool calls add provider calls.

By default all selected repair groups and related replay cases are considered; blank limits mean all/unlimited. Optional budgets still reserve capacity by phase. Development fresh inputs are generated once and shared across candidates. Final generation rejects duplicates of discovery, development, and other final inputs, with recorded retry exhaustion as invalid evidence. Replay, unseen, adaptive, and utility suites must have sufficient completed observations. No timeout, invalid input, unavailable judge, or connection failure becomes a passing case.

The normal-use floor defaults to 85%, maximum false-block rate to 5%, and maximum allowed utility drop to 10 percentage points. Reports include valid denominators, incompleteness, 95% Wilson intervals, and exploratory paired McNemar/binomial comparisons. Related generated inputs may be correlated; these statistics describe the experiment and do not certify population-wide model resilience.

The paired v4 protocol requires complete baseline observations as well as complete candidate observations before validation. An incomplete normal-use suite has an unknown score and an unknown utility change, rather than a misleading zero. Presentation exports also display incomplete legacy scores as unmeasured while preserving the original evidence records.

## Reports, deployment, and standards

**Report** provides a styled presentation preview, standalone HTML, Markdown, structured JSON, native PDF, and editable PowerPoint. The report contains executive decision, fixed scope and revisions, evidence-based risk register, candidate comparisons, paired security/utility results, per-cell coverage, deployment steps, rollback, resources, MITRE ATLAS mappings, NIST evidence crosswalk, and gaps.

Presentation formats use a shared readable-evidence projection: expected behavior, actual observed effect, a short proof table, and labeled input/output quotations. Quotation excerpts are explicitly marked and bounded; full attack payloads, model responses, source metadata and hashes remain in the separate JSON/NDJSON evidence export. A retrieval-boundary failure is explained separately from tool execution, so a refused export is not incorrectly described as an executed export. Persisted older report models also use this presentation projection when rendered again.

Analysts and higher roles can download full JSON evidence, streamed NDJSON, and remediation ZIP bundles. NDJSON includes a manifest and count/SHA-256 trailer; the hash covers the UTF-8 bytes of preceding lines including LF. Evidence traversal has no 1,000-record ceiling. Raw final inputs require an administrator and a closed campaign. Running exports describe their live snapshot limits.

The ZIP includes verified configuration artifacts, selection/verdict metadata, plans, rollback, and file SHA-256 hashes. Apply only a selected candidate validated in scope, implement equivalent controls in the destination application, rerun security and normal-use suites there, and monitor blocked requests and utility. Reports preserve rejected and inconclusive alternatives.

Each ZIP plan explicitly records `deployment_eligible`, `verification_verdict`, and the selected verification ID. A selected development candidate is not deployable while final verification is pending, rejected, or inconclusive. Eligibility also requires the independently validated candidate hash and target revision to match the exported artifact.

NIST mappings provide **supporting evidence** for [AI RMF 1.0](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf) and the [Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf), including `MS-2.7-001` and `MS-2.10-001` where applicable. They do not claim certification. Organizational governance, legal compliance, fairness, environmental impact, and operational incident response remain unassessed. MITRE technique mappings retain their reason and catalog revision.

Live target performance and attack success must be measured after the operator supplies and connects the deployed model URL. Fixture tests validate the implementation and workflow.
