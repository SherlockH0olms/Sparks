export type GuideStep = {
  id: string; title: string; page: string; pageName: string; purpose: string;
  actions: string[]; expected: string; terms: {name: string; explanation: string}[];
};

export const guideSteps: GuideStep[] = [
  {
    id: "setup", title: "Configure access and model roles", page: "/", pageName: "Overview",
    purpose: "AEGIS coordinates an experiment between a model that designs attacks, your target application, and an evaluator. Set up those connections before starting a run.",
    actions: [
      "Open the project's .env file. AEGIS_ADMIN_TOKEN is the platform login key. Enter that value on the sign-in screen for the first administrator account.",
      "Configure AEGIS_RED_PROVIDER, AEGIS_RED_ENDPOINT, AEGIS_RED_API_KEY, and AEGIS_RED_MODEL. Red generates attack candidates and uses the attack library through tool calls.",
      "Configure the corresponding AEGIS_JUDGE_* settings separately. Judge evaluates semantic behavior when a property needs interpretation; server-owned checks assess concrete events such as tool effects and secret exposure.",
      "Restart the application after changing .env. Review Red and Judge configuration on Overview. A configured badge means settings are present; campaign preflight checks actual connectivity.",
    ],
    expected: "You can sign in, and both Red and Judge show their configuration status. The local target connection is registered in the next step.",
    terms: [
      {name:"Red", explanation:"The model that designs and adapts attack inputs. It does not replace your target model."},
      {name:"Target", explanation:"The AI application being tested, including its model, document retrieval, tools, and task rules."},
      {name:"Judge", explanation:"The evaluator for semantic security properties. It complements deterministic checks and does not generate attacks."},
      {name:"AEGIS", explanation:"The control plane: it records scope and versions, executes tests, enforces budgets, and saves the evidence."},
    ],
  },
  {
    id:"target", title:"Register the application you want to test", page:"/target", pageName:"Targets",
    purpose:"A target record tells AEGIS how to reach the model, what it is allowed to do, and which documents and tools belong to each user group.",
    actions:[
      "Start a model API server, then select Add target on Targets. Choose localhost, LAN, Tailscale, Cloudflare, ngrok, Kaggle/Colab tunnel, or Custom. Registration connects to your server; it does not download model weights.",
      "Select OpenAI-compatible chat (usually a /v1 base) or native Ollama (server root). Enter the actual URL, model identifier, pinned weight version, application version, and task policy. Choose environment authentication, no API key, or a target-specific key. Cloudflare Access service tokens use the separate client ID and secret fields.",
      "In Documents and tasks, review the sample JSON. Documents have tenant ownership; assigned_to_red marks the document Red may replace during a document injection test. Normal-use cases describe questions the assistant should still answer correctly.",
      "In Access and controls, declare the capabilities your application actually supports, its starting defenses, writable attack surfaces, and feedback available to Red. Review the snapshot and select Save target.",
      "Select Test connection on the target card. A successful check confirms that the registered target responds from the platform backend. Resolve connection errors before creating a campaign.",
    ],
    expected:"A versioned target appears in the registry with a connection check result, document count, and normal-use test count.",
    terms:[
      {name:"Pinned model version",explanation:"A fixed release, revision, or weight hash. It identifies the model used in these results."},
      {name:"Tenant",explanation:"A separate data ownership group, such as two customers. Cross-tenant tests check whether one group can access another group's data."},
      {name:"Normal-use test",explanation:"A legitimate task with expected answer terms or an allowed tool action. These tests measure whether a defense preserves useful behavior."},
      {name:"Snapshot",explanation:"The recorded model, application rules, data, and access profile used by a campaign. Create a new target record to test a changed version."},
    ],
  },
  {
    id:"campaign",title:"Choose the test scope and budget",page:"/campaign",pageName:"Campaign",
    purpose:"A campaign is one experiment on a recorded target version. Its scope defines which behaviors to test and how much evidence to collect.",
    actions:[
      "Select New campaign, then choose a registered target. English is selected in the form by default; add other test languages when you want multilingual coverage.",
      "Choose security properties and attack families. A property is a rule to protect, such as tool authorization. A family is an approach used to challenge it, such as document injection.",
      "Set the discovery attempt limit or leave it blank for no attempt cap. Set the minimum normal-use pass rate as a fraction: 0.85 means at least 85% of the normal tasks must pass.",
      "Call, token, and time budgets are optional; blank means unlimited. Review any budgets you set. One candidate can require several Red calls for reading sources, composing tactics, and submitting its payload. A call budget is therefore different from an attack count.",
      "Choose Standard, Deep, Smoke, or Custom depth. Standard uses 30 fresh and 12 adaptive final cases per applicable property cell; Deep uses 100 and 40. Smoke checks a smaller finding scope. Configure counts, reproduction, utility thresholds, and optional group limits. Select Estimate test coverage, review the counts, then Create campaign and Start campaign.",
    ],
    expected:"The campaign console opens on your new draft with its target version, scope, and budget recorded.",
    terms:[
      {name:"Property",explanation:"An expected security behavior: task adherence, instruction separation, tenant isolation, confidentiality, authorized tools, output integrity, or session isolation."},
      {name:"Attack family",explanation:"A test approach: direct or document injection, authority spoofing, multi-turn manipulation, encoding evasion, tenant probing, tool misuse, or schema abuse."},
      {name:"Phase allocation",explanation:"A share of the total budget reserved for a stage. A stage can exhaust its allocation even when another stage still has capacity."},
      {name:"Attempt limit",explanation:"A cap on discovery attempts. Leaving it blank removes that cap; separately configured call, token, or time budgets still apply."},
    ],
  },
  {
    id:"run",title:"Start the campaign and follow its progress",page:"/campaign",pageName:"Campaign console",
    purpose:"The console shows the live experiment. The background worker moves the campaign through connection checks, baseline tasks, discovery, reproduction, repairs, verification, and reporting.",
    actions:[
      "Select your draft in the campaign picker and select Start campaign. The worker checks connections, measures normal behavior, and then asks Red to design tests for the remaining scope.",
      "Watch the phase badge, activity feed, and budget usage. Pause stops progress at a checkpoint; Resume continues the same campaign. Cancel ends the run.",
      "Filter attempts by phase. Select Inspect to see the input, target response, retrieved documents, simulated tool effects, assessment, and Red's source and transformation records.",
      "If the target disconnects, recorded retries are charged and the campaign pauses. Restore the same URL, test the connection, and select Resume. A new URL requires a new versioned target. If a run is queued without progress, check the controller on Audit and access. If it fails or exhausts a budget, read the recorded error and report before choosing settings for a new campaign.",
    ],
    expected:"Attempts and events appear as the worker executes. A completed campaign has finished its workflow; individual repair verdicts still determine whether an improvement was validated.",
    terms:[
      {name:"Execution status",explanation:"Whether the model call or test ran successfully. It is separate from the security verdict."},
      {name:"Checkpoint",explanation:"Saved progress used to resume a paused or interrupted workflow."},
      {name:"Tool effects",explanation:"The registered local email/export gateway records simulated actions. These records show attempted effects without sending real email through that gateway."},
      {name:"Worker",explanation:"The background process that executes queued campaigns. An inactive controller means new jobs cannot progress."},
    ],
  },
  {
    id:"coverage",title:"Check what was actually tested",page:"/coverage",pageName:"Coverage",
    purpose:"Coverage answers how much of the planned test scope has received enough valid tests. It helps you identify gaps in an experiment.",
    actions:[
      "Select the campaign. Filter by language, property, attack family, or input surface.",
      "Read the cell grid and the table together. A cell combines a language, property, family, surface, and required interaction depth. Multi-turn cells require three meaningful turns.",
      "Compare Valid / required for each applicable cell. Timeouts, infrastructure errors, and inconclusive assessments do not complete a cell. Not-applicable cells explain which capability or access condition is missing.",
      "Review attack diversity as well: sources read, methods selected, tactics composed, and transformations applied describe how Red generated tests. Inspect individual attempts to assess the actual payloads.",
    ],
    expected:"You can identify completed combinations, insufficient evidence, and excluded tests. High coverage does not by itself mean the target is secure.",
    terms:[
      {name:"Coverage",explanation:"Completed applicable cells divided by all applicable cells. A cell completes when its minimum valid test count is met."},
      {name:"Valid test",explanation:"A test with sufficient completed and evaluable observations for its property."},
      {name:"Inconclusive",explanation:"The evidence does not support a clear security conclusion. Check the assessment or execution error."},
      {name:"Attack diversity",explanation:"Recorded variety in generation methods and sources. It is distinct from success against the target."},
    ],
  },
  {
    id:"findings",title:"Inspect reproduced security issues",page:"/findings",pageName:"Findings",
    purpose:"A finding is an observed violation that met the campaign's reproduction requirements. Multiple attack inputs can demonstrate the same underlying issue.",
    actions:[
      "Open Findings and filter by security property. Compare severity, reproduction rate, and ATLAS mapping.",
      "Open a finding to read its violated boundary, observed effect, and diagnosis. Compare the original trace with the minimized reproduction input.",
      "Review each fresh-session reproduction. The property, boundary, and effect must match the original issue. A source reference or a convincing attack hypothesis is not a substitute for target evidence.",
      "After the campaign completes, an analyst or higher role can select Reproduce in a fresh session using the reserved reproduction budget. Follow the link to the related repair experiment.",
    ],
    expected:"You can explain what was violated, show the exact evidence, and understand how consistently it reproduced.",
    terms:[
      {name:"Finding",explanation:"A reproduced issue, rather than every generated candidate or every observed violation."},
      {name:"Reproduction rate",explanation:"The fraction of reproduction checks that demonstrated the same violation."},
      {name:"Minimized input",explanation:"A shorter attack input retained only when it still produces the same effect."},
      {name:"MITRE ATLAS",explanation:"A public taxonomy of AI attack techniques. The platform records a mapping and its supporting reason when available."},
    ],
  },
  {
    id:"repair",title:"Compare defense configurations",page:"/repair",pageName:"Repair Lab",
    purpose:"Repair Lab evaluates supported defense controls on isolated target configurations. The campaign runs these experiments automatically for selected defect groups.",
    actions:[
      "Compare baseline A, task-policy B, focused boundary C, and combined D. Applicable findings add E encoding/provenance controls, F Guardrails schema validation, or G Presidio personal-data filtering. Explore the executable catalog to see implementation and limitations.",
      "Read the configuration diff and artifact hash for each candidate. Depending on the property, controls can filter tenant retrieval, enforce tool authorization, separate document instructions, or validate output.",
      "Development replays related attacks and uses one shared fresh set across candidates. Final cases reject duplicates of discovery, development, and other final inputs. Review startup checks, development security tests, and normal-use results. Read any rejection reasons. A defense that prevents attacks but blocks legitimate work can fail its usefulness checks.",
      "Find the selected, frozen candidate and open Independent verification. Use the recorded configuration and rollback information when deciding how to apply a verified control to your application.",
    ],
    expected:"A passing defense candidate is selected for final tests, or the experiment records why no candidate qualified. Repair artifacts describe supported AEGIS configuration controls; external application changes require applying the corresponding controls there.",
    terms:[
      {name:"Candidate",explanation:"A proposed defense configuration evaluated against the same target snapshot."},
      {name:"Frozen",explanation:"The selected configuration and hash are fixed before final verification."},
      {name:"Development checks",explanation:"Tests used to qualify and choose a candidate. Fresh final tests assess the chosen candidate independently."},
      {name:"Rollback",explanation:"The recorded baseline configuration and target version needed to restore the tested starting state."},
    ],
  },
  {
    id:"verification",title:"Read the independent comparison",page:"/verification",pageName:"Verification",
    purpose:"Verification runs paired tests on the baseline and frozen candidate. It measures security changes together with normal task performance.",
    actions:[
      "Compare baseline and candidate results in Known attack replay, Fresh unseen attacks, Adaptive attacks, and Normal-use tasks.",
      "Inspect verification coverage by family, language, and surface, paired improvements, and descriptive Wilson intervals. Read the numerator, valid test count, timeouts, and inconclusive results alongside each rate. For security tests, lower attack success is better. For normal tasks, a higher pass rate is better.",
      "Review the final verdict: Validated in scope means the final requirements passed; Rejected means a requirement failed; Inconclusive means evidence was insufficient.",
      "Check candidate hash, target version, protocol, and test-set version. These identify exactly what was evaluated. Open Report to share the findings and limitations.",
    ],
    expected:"You can tell whether the candidate improved the measured security behavior and retained useful behavior within this experiment's scope.",
    terms:[
      {name:"Attack success rate (ASR)",explanation:"Observed violations divided by valid security tests in a suite. A generated candidate count is not an ASR."},
      {name:"Unseen attacks",explanation:"Fresh examples generated for final evaluation rather than used to choose the defense."},
      {name:"Adaptive attacks",explanation:"Attacks revised with feedback about the candidate. Their rates describe this adaptive experiment."},
      {name:"False block",explanation:"A legitimate request incorrectly refused or blocked by the defense."},
    ],
  },
  {
    id:"report",title:"Export evidence and manage access",page:"/report",pageName:"Report",
    purpose:"The report brings together the scope, findings, paired results, budget, errors, and limitations. Audit and access records who can use the platform and what actions occurred.",
    actions:[
      "Select a campaign on Report. While it runs, the report is a snapshot. After completion, review the final results and any uncompleted scope cells.",
      "Use Presentation preview, then download PDF, editable PowerPoint, standalone HTML, Markdown, or structured report JSON. Analysts and higher roles can export JSON/NDJSON evidence and a remediation ZIP with configurations, deployment plans, rollback, and hashes. MITRE ATLAS/NIST mappings show supporting evidence, not certification. Administrators can export raw evidence after closure; credentials are excluded.",
      "Use Audit and access to inspect the worker controller and saved events. Administrators can create role-scoped access keys; a newly issued key is shown once and should be copied securely.",
      "The stop-all control signals cancellation to open campaigns in the workspace and blocks new runs. Allowing new runs does not resume campaigns that were cancelled.",
    ],
    expected:"You have a reviewable report with its supporting records, and collaborators have access appropriate to their role.",
    terms:[
      {name:"Evidence package",explanation:"A JSON export of the campaign, scope, execution records, assessments, repair artifacts, verification, and budget."},
      {name:"Viewer",explanation:"Reads summaries and reports."},
      {name:"Analyst / Maintainer",explanation:"An analyst manages campaigns and evidence. A maintainer can also register targets and use repair permissions."},
      {name:"Administrator",explanation:"Manages access keys and execution controls, and can export confidential raw evidence after closure."},
    ],
  },
];

export const pageHelp: Record<string,{title:string;description:string;steps:string[];guideId:string;next:string;nextLabel:string}> = {
  "/":{title:"Start with a connected target",description:"Overview summarizes setup, campaigns, and the attack library.",steps:["Check Red and Judge configuration below.","Register your target and test its connection.","Create a campaign, then start it from the console."],guideId:"setup",next:"/target",nextLabel:"Register a target"},
  "/target":{title:"Define what you are testing",description:"A target combines the model connection, expected behavior, documents, and allowed inputs.",steps:["Select Add target and complete Connection, Documents and tasks, Access and controls, and Review.","Use normal-use cases to define tasks that should still work after a repair.","Save the target and select Test connection before creating a campaign."],guideId:"target",next:"/campaign",nextLabel:"Create a campaign"},
  "/campaign":{title:"Run and inspect your experiment",description:"The campaign picker sets the active experiment for the other pages.",steps:["Create a campaign with the target, scope, and budget you want.","Select Start campaign on a draft. Pause and Resume retain saved progress.","Open Inspect on an attempt to see inputs, target responses, and assessments."],guideId:"run",next:"/coverage",nextLabel:"Check coverage"},
  "/coverage":{title:"Find tested combinations and gaps",description:"Coverage measures completed applicable scope cells, rather than overall security.",steps:["Filter cells by language, property, family, or surface.","Compare the valid count with the required count. Read reasons for N/A and incomplete cells.","Open Findings to inspect issues that met the reproduction threshold."],guideId:"coverage",next:"/findings",nextLabel:"Review findings"},
  "/findings":{title:"Review the evidence for each issue",description:"Confirmed findings have reproduced the same property, boundary, and effect.",steps:["Filter findings and compare severity and reproduction rate.","Open a finding for the original trace, minimized input, and fresh-session checks.","Follow its repair link to compare defense configurations."],guideId:"findings",next:"/repair",nextLabel:"Compare repairs"},
  "/repair":{title:"Compare applicable defense configurations",description:"The campaign evaluates supported defense controls automatically on isolated variants.",steps:["Read the diff, startup check, attack results, and normal-use results for each candidate.","Check rejection reasons and which passing candidate was selected and frozen.","Review independent verification before applying the corresponding controls to your application."],guideId:"repair",next:"/verification",nextLabel:"Review verification"},
  "/verification":{title:"Assess security and useful behavior together",description:"The same final test suites compare the baseline and frozen candidate.",steps:["Compare replay, unseen, adaptive, and normal-use results.","Read valid counts, inconclusive cases, and false blocks alongside percentages.","Check the final verdict and export the report with its limitations."],guideId:"verification",next:"/report",nextLabel:"Open the report"},
  "/report":{title:"Share results with supporting evidence",description:"A running campaign produces a snapshot; a closed campaign has its final recorded results.",steps:["Read the findings, verification results, budget usage, and scope gaps.","Preview the designed report. Download PDF, PowerPoint, HTML, Markdown, JSON, NDJSON evidence, or a remediation bundle.","Raw evidence is available to administrators after closure and includes confidential test data."],guideId:"report",next:"/audit",nextLabel:"Manage access"},
  "/audit":{title:"Manage people and campaign execution",description:"This page shows worker status, your permissions, and administrator controls.",steps:["Check whether the background controller is active if queued campaigns do not progress.","Administrators can issue role-scoped keys and review audit events.","Stop all campaigns cancels open runs and prevents new ones until the execution lock is lifted."],guideId:"report",next:"/guide",nextLabel:"Read the complete guide"},
};

export const glossary = [
  ...guideSteps.flatMap(s=>s.terms),
  {name:"RAG",explanation:"Retrieval-augmented generation: the assistant retrieves documents to answer a question. Document injection tests whether retrieved text is wrongly treated as instructions."},
  {name:"Canary",explanation:"A server-generated secret marker used to detect disclosure of protected test data."},
  {name:"Oracle",explanation:"A server-owned check of the expected security outcome, using known test facts or recorded tool effects."},
  {name:"Seed / tactic / transformation",explanation:"A seed is a source example. A tactic is an idea for changing its framing or mechanism. A transformation changes text through a registered local framework component."},
  {name:"Insertion token",explanation:"A reference returned by a transformation tool. AEGIS replaces it with the exact output text when Red submits the candidate."},
  {name:"Artifact hash",explanation:"A content fingerprint for a defense configuration. It connects the reviewed configuration to the exact candidate evaluated."},
];
