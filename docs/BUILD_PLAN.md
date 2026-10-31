# AEGIS LOOP v2 implementation and acceptance plan

The offensive generator is a Foundry model. The evaluated model is an independently configured local OpenAI-compatible endpoint. Their credentials, observations, prompts, budgets and responsibilities remain separate. The application mediating the local model provides versioned retrieval and mock tools so that application controls can be tested without external side effects.

The original implementation remains available in Git history. This branch rebuilds the runtime and its tests. The user's `.env` is ignored; `.env.example` documents every required setting. Missing provider settings are visible configuration errors and never trigger fabricated results.

| Commit stage | Implementation | Acceptance evidence |
|---|---|---|
| 1. Foundation | Explicit contracts, environment settings, durable database, RBAC, audit, immutable snapshots | Restart persistence, workspace separation, authenticated roles, atomic resource reservation |
| 2. Model boundaries | Foundry and Azure OpenAI adapters; local model application; deterministic oracles; pinned official ATLAS data | HTTP request contracts, timeout/error separation, legitimate tool positive tests, tenant negative tests |
| 3. Discovery | Versioned campaigns, coverage scheduler, bounded AI generation, multi-turn traces, exact document snapshots, reproduction, minimization | No static fallback in real runs; no out-of-scope candidate; same violation on fresh repeats; budget contains every provider call |
| 4. Repair and verification | Catalog preconditions, immutable config patches, startup smoke tests, development gates, frozen candidate, isolated final suite, adaptive reattack, utility regression | Reject ineffective/unusable variants; zero tests cannot pass; same baseline/candidate protocol; final data inaccessible to development roles |
| 5. Control API | Authenticated target setup, preflight, campaign controls, durable jobs/leases, replayable SSE, report/evidence export | Pause/resume after restart, cancel checkpoints, worker loss, idempotency, sanitized and authorized exports |
| 6. Web product | Login, target wizard, campaign console, multidimensional coverage, findings, repair comparison, verification, report, audit and access management | Real API contracts, empty/error/offline states, URL state, safe content rendering, end-to-end browser scenarios |
| 7. Delivery | Windows/Linux launchers, Docker/PostgreSQL option, scenarios, exact setup docs, CI, repeatable benchmark | Full test suite, typecheck/build, browser tests, equal-budget benchmark, secret-free Git diff |

## Execution and evidence rules

* A provider request reserves calls, conservative input/output tokens and remaining time before sending. Every turn, generation, judge, replay, build smoke test and utility test is accounted for. Failed/ambiguous requests keep their reservation or reconcile conservatively; they are never free calls.
* Discovery, development, final verification and utility have separate allocations. Final allocations cannot be borrowed by discovery. Reservations belong to an operation and an allocation, not merely a global counter.
* Execution status and security verdict are separate. Timeout, invalid candidate, missing trace, empty response and unavailable judge never become a successful defense.
* Coverage requires distinct validated tests at the required turn depth with completed assessment. It uses the applicable cells fixed at campaign creation. It does not claim global attack coverage.
* The entire target snapshot, documents, canary references, scenario, per-turn responses, tool/retrieval traces, revisions and assessments are preserved. Red receives only the configured public observations; Blue receives confirmed evidence and permitted configuration paths.
* Reproduction and minimization preserve the original property, boundary and effect. Failed reproduction stays a candidate. Related payloads are grouped by defect evidence, not prompt text count.
* A repair is an allowlisted configuration patch with an actual before/after diff, smoke-test record, content hash and rollback. A config variant does not imply arbitrary source rewriting or real deployment.
* Development chooses one candidate before final evaluation. Final tests are created and persisted in the evaluator-only store. Reusing final feedback for another candidate explicitly ends independence; it is not silently reported as blind validation.
* The final report compares the exact fixed suite on baseline and candidate, records valid denominators and infrastructure outcomes, and states the scope and remaining uncertainty.
* The controller persists phases/checkpoints, uses bounded workers and renewable leases, and recovers interrupted operations without claiming exactly-once network delivery. Mock tool effects use operation identifiers.

## Scenarios to deliver

1. Direct task diversion through user input, evaluated against a declared task contract and optional independent semantic rubric.
2. Indirect instruction injection through an assigned document, with document snapshots and actual model/tool traces.
3. Cross-tenant retrieval and synthetic secret disclosure, with trusted identity context and evaluator-only canaries.
4. Unauthorized tool requests, distinguished from executed effects; authorized mock operations remain functional.
5. Structured output corruption, including rejection behavior and positive structured-output utility tests.
6. Multi-turn escalation and session isolation, with per-turn assessment and new-session reproduction.
7. Turkish, Azerbaijani and English variants with language-specific utility and coverage records.
8. Encoding/role/authority variants generated by Foundry, under bounded search and a declared access profile.

The system is ready for external provider validation when configuration is supplied. Automated integration tests inject explicitly identified fixture providers; those results are never represented as real Foundry/local-model evidence.
