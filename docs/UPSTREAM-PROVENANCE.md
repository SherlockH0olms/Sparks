# Upstream provenance and integration reference

This document explains which external components AEGIS executes, which material it indexes/adapts, and which projects are research references. It complements the [product README](../README.md).

The documented snapshot is dated **1 November 2026**. Runtime installation probes determine what is available on another machine. Resource counts are globally deduplicated material counts, not independent algorithms, completed security tests, or target attack-success rates.

## Integration categories

| Category | Meaning |
|---|---|
| Executed component | A registered bridge calls an installed upstream API. |
| Indexed material | Selected upstream text is extracted as data, normalized, deduplicated, and made searchable. |
| Adapted candidate | AEGIS Red rewrites/composes mechanisms for the registered target's task, language, documents, and tools. |
| Design reference | Guidance/taxonomy informs AEGIS implementation or report mapping. |
| Research entry | Investigated capability with no executable connection established. |

Installed upstream package source is not forked or modified by the reviewed integration. The original bridges, target protocol, scheduler, persistent runtime, oracles, control search, evidence storage, verification, and UI are implemented in this repository. Text extraction/normalization and generated candidate adaptation are distinct from modifying upstream code.

## Executed upstream APIs and isolation

| Component | Version | Actual API | Environment / bridge |
|---|---|---|---|
| PyRIT | 1.1.0 | Registered converter `convert_async(prompt=..., input_type="text")` | `.venv-redtools`; [Python worker](../scripts/redteam_framework_worker.py) |
| Garak | 0.17.1 | `Buff.transform` with registered Base64/CharCode | Same isolated Python worker; partial package dependencies |
| Promptfoo | 0.125.1 | Public `redteam.Strategies.action` | `.runtime/redtools-node`; [Node worker](../scripts/redteam_promptfoo_worker.cjs) |
| DeepTeam | 1.0.10 | Four local single-turn `.enhance` attacks | `.venv-redtools-deep`, Python 3.12; [worker](../scripts/redteam_deepteam_worker.py) |
| python-jsonschema | 4.26.0 | `Draft202012Validator` | Application environment; [controls](../backend/aegis_v2/defenses.py) |
| Guardrails AI | 0.11.0 | `guardrails.schema.validator.validate_payload` | `.venv-defensetools`, Python 3.12; [defense worker](../scripts/defense_tool_worker.py) |
| Presidio Analyzer | 2.2.366 | Registered `PatternRecognizer` email/phone patterns | Same optional defense environment/worker |

Promptfoo's bridge disables telemetry/remote generation and seeds local randomness from component ID/input. The Python transformation bridge also seeds supported randomness. Recorded transformation results are retained for replay. Neither setup availability nor a source read means every upstream algorithm executes in the campaign.

AEGIS does not integrate complete PyRIT orchestrators/scorers, Garak scanners/detectors/providers, Promptfoo campaign generation, DeepTeam autonomous/model-dependent pipelines, Guardrails Hub validators, or Presidio NLP models. These APIs have narrower recorded scopes.

## All 49 verified local transformations

A row is a callable local text component, not a separate autonomous red-team system. PyRIT's six named encoding variants instantiate its Base64Converter with different encoding functions; CaesarConverter uses an offset of 3.

| Framework | Version | Registered transformation ID | Actual upstream implementation |
|---|---|---|---|
| pyrit | 1.1.0 | `pyrit:base64` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:base64url` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:base16` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:base32` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:ascii85` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:base85` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:ROT13Converter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:AtbashConverter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:BinaryConverter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:BinAsciiConverter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:MorseConverter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:NatoConverter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:LeetspeakConverter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:CharacterSpaceConverter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:JsonStringConverter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:UnicodeConfusableConverter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:ZeroWidthConverter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:BidiConverter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:UnicodeSubstitutionConverter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:SuperscriptConverter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:FlipConverter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:RandomCapitalLettersConverter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:InsertPunctuationConverter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:CaesarConverter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:DiacriticConverter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:ZalgoConverter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:BrailleConverter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:Base2048Converter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:EcojiConverter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:AsciiSmugglerConverter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:SneakyBitsSmugglerConverter` | `convert_async` |
| pyrit | 1.1.0 | `pyrit:VariationSelectorSmugglerConverter` | `convert_async` |
| garak | 0.17.1 | `garak:Base64` | `Buff.transform` |
| garak | 0.17.1 | `garak:CharCode` | `Buff.transform` |
| promptfoo | 0.125.1 | `promptfoo:base64` | `redteam.Strategies.action` |
| promptfoo | 0.125.1 | `promptfoo:hex` | `redteam.Strategies.action` |
| promptfoo | 0.125.1 | `promptfoo:rot13` | `redteam.Strategies.action` |
| promptfoo | 0.125.1 | `promptfoo:leetspeak` | `redteam.Strategies.action` |
| promptfoo | 0.125.1 | `promptfoo:homoglyph` | `redteam.Strategies.action` |
| promptfoo | 0.125.1 | `promptfoo:morse` | `redteam.Strategies.action` |
| promptfoo | 0.125.1 | `promptfoo:piglatin` | `redteam.Strategies.action` |
| promptfoo | 0.125.1 | `promptfoo:camelcase` | `redteam.Strategies.action` |
| promptfoo | 0.125.1 | `promptfoo:emoji` | `redteam.Strategies.action` |
| promptfoo | 0.125.1 | `promptfoo:arabic-presentation-forms` | `redteam.Strategies.action` |
| promptfoo | 0.125.1 | `promptfoo:jailbreak-templates` | `redteam.Strategies.action` |
| deepteam | 1.0.10 | `deepteam:Base64` | `deepteam.attacks.single_turn.Base64.enhance` |
| deepteam | 1.0.10 | `deepteam:ROT13` | `deepteam.attacks.single_turn.ROT13.enhance` |
| deepteam | 1.0.10 | `deepteam:Leetspeak` | `deepteam.attacks.single_turn.Leetspeak.enhance` |
| deepteam | 1.0.10 | `deepteam:CharacterStream` | `deepteam.attacks.single_turn.CharacterStream.enhance` |

## Package-derived attack resources

The initial catalog contains **920 PyRIT and 802 Garak resources**. They remain included in the 254,368-resource expanded corpus. The worker imports selected prompt/data files, not upstream Python attack algorithms.

### PyRIT extraction

Selected paths under installed `pyrit/datasets`:

- `jailbreak/`, `converters/`, and `executors/` YAML/prompt resources.
- `seed_datasets/local/psfuzz_steal_system.prompt`.
- `seed_datasets/local/garak/` prompt resources.

The worker imports string `value` and `seeds/*/value` fields, retaining available `name`, `source`, and `description`. It excludes unrelated scoring rubrics and unrelated content datasets. A transformation prompt being indexed does not mean its model-dependent upstream converter is installed/executed.

PyRIT resources can themselves attribute another project (including Garak or psfuzz). That nested `upstream_source` stays in the record. Such attribution does not imply a direct AEGIS integration with the referenced project's runtime.

### Garak extraction

Selected installed `garak/data` paths and unique records in the current initial catalog:

| Upstream path | Unique records |
|---|---:|
| `adaptive_attacks/seeds.txt` | 20 |
| `adaptive_attacks/suffixes.txt` | 5 |
| `autodan/autodan_init.txt` | 1 |
| `autodan/autodan_prompts.json` | 3 |
| `dan/AntiDAN.json` | 1 |
| `dan/ChatGPT_Developer_Mode_RANTI.json` | 1 |
| `dan/ChatGPT_Developer_Mode_v2.json` | 1 |
| `dan/ChatGPT_Image_Markdown.json` | 1 |
| `dan/Dan_10_0.json` | 1 |
| `dan/Dan_11_0.json` | 1 |
| `dan/Dan_6_0.json` | 1 |
| `dan/Dan_6_2.json` | 1 |
| `dan/Dan_7_0.json` | 1 |
| `dan/Dan_8_0.json` | 1 |
| `dan/Dan_9_0.json` | 1 |
| `dan/DAN_Jailbreak.json` | 1 |
| `dan/DUDE.json` | 1 |
| `dan/STAN.json` | 1 |
| `gcg/gcg.txt` | 13 |
| `inthewild_jailbreak_llms.json` | 650 |
| `tap/tap_jailbreaks.txt` | 9 |
| `typology_payloads.tsv` | 87 |

The importer selects actual prompt/text/attack/template/content fields, excludes URL/name/category fields as payloads, and extracts declared text lines. A file named after AutoDAN, TAP, GCG, BEAST, GOAT, or another research method supplies stored material; reading it does not execute that optimization algorithm.

## Expanded source snapshots

Machine-readable authority: [corpus snapshot](red-team-corpus-snapshot.json). Source files are downloaded locally; extraction uses JSON/JSONL/CSV parsing or Python AST literal inspection, not execution of downloaded repository code.

| Source | Version | Recorded material license | Extraction/adaptation | New unique records |
|---|---|---|---|---:|
| TensorTrust | v2 | Not specified | Attacker-input seeds; game-specific identifiers/passwords are not target facts. | 235,360 |
| WildTeaming | Snapshot | Not specified | Tactic definitions plus composition guidance; target-specific AEGIS composition. | 16,833 |
| BIPIA | Snapshot | MIT (attack templates) | Text/code attack-template strings only, excluding carrier datasets. | 250 |
| InjecAgent | Snapshot | MIT | Attacker Instruction fields adapted to registered tool/document surfaces. | 62 |
| HarmBench | Snapshot | MIT | GPTFuzzer CSV template text and Python literal fragments. | 137 |
| AgentDojo | Snapshot | MIT | Four long literal attack fragments, inspected without execution. | 4 |

### What changes during extraction and use

- **TensorTrust:** from 563,349 raw records, 384,296 usable records remain before cross-source deduplication; self-attacks, empty/correct-password entries, and single-code guesses are excluded. 235,360 new unique corpus records are added.
- **WildTeaming:** preserves tactic titles/definitions and strategy-type metadata. Duplicate definition entries are combined; original harmful objectives/excerpts are excluded. The 16,833 resources contain 16,832 tactics and composition guidance. AEGIS selects resources/tactics and asks its Red model to compose a candidate; it does not run upstream tactic mining or full pruning/evaluation.
- **BIPIA:** extracts 250 template records from four text/code train/test attack JSON files. AEGIS uses its own assigned-document surface and target utility/security checks.
- **InjecAgent:** extracts 62 attacker instructions. Original agent tools/destinations are adapted to declared AEGIS tools; the original agent environment is not reproduced.
- **HarmBench:** extracts 189 usable fragments with 137 new unique records after deduplication. Full benchmark classifiers and GPTFuzzer search/optimization do not execute.
- **AgentDojo:** extracts four guidance fragments through AST literal parsing. AEGIS supplies its own simulated gateway and retrieval environment.

The expanded indexing layer normalizes text, deduplicates by content, retains provenance aliases, and stores record IDs, source/version, path/location, kind, license metadata, and hashes. Red may rewrite an original template's objective, language, names, document IDs, or tool references to match the target. Original source text/provenance remains traceable.

### Exact files and recorded hashes

These hashes identify the downloaded snapshots; a mutable branch URL alone is not a pinned source version.

| Source | Upstream file | SHA-256 |
|---|---|---|
| [tensortrust](https://github.com/HumanCompatibleAI/tensor-trust-data) | [`raw-data/v2/raw_dump_attacks.jsonl.bz2`](https://raw.githubusercontent.com/HumanCompatibleAI/tensor-trust-data/main/raw-data/v2/raw_dump_attacks.jsonl.bz2) | `87853cc8065a22156d15c4bdec777a8d35758749beb79769147d63a9644a73ce` |
| [wildteaming](https://github.com/allenai/wildteaming) | [`data/tactics/auto_tactics.json`](https://raw.githubusercontent.com/allenai/wildteaming/main/data/tactics/auto_tactics.json) | `36a04ccb42b4a50ddb62d611dab0cbf6f9ea339c9c15223c9f14ef4e64c0db06` |
| [wildteaming](https://github.com/allenai/wildteaming) | [`data/prompts/compose_tactics.txt`](https://raw.githubusercontent.com/allenai/wildteaming/main/data/prompts/compose_tactics.txt) | `2833e8812082a95c00c1e4618e61def902522bb847ebb408c0f0a0b0356039ce` |
| [bipia](https://github.com/microsoft/BIPIA) | [`benchmark/text_attack_train.json`](https://raw.githubusercontent.com/microsoft/BIPIA/main/benchmark/text_attack_train.json) | `63f95d3e67eac4178cdabdbdaf192cd05f2b6ed0702b578f1d30d556e5155670` |
| [bipia](https://github.com/microsoft/BIPIA) | [`benchmark/text_attack_test.json`](https://raw.githubusercontent.com/microsoft/BIPIA/main/benchmark/text_attack_test.json) | `75750e7b4e8b34e8f9d88d89b357aeaaf02bd07f9e493ccd37eda74a0cd7c7f8` |
| [bipia](https://github.com/microsoft/BIPIA) | [`benchmark/code_attack_train.json`](https://raw.githubusercontent.com/microsoft/BIPIA/main/benchmark/code_attack_train.json) | `fe515080b6da2b5c0b67ca7ba2a3b3c2ce57c48f45733c475ebc813cba118484` |
| [bipia](https://github.com/microsoft/BIPIA) | [`benchmark/code_attack_test.json`](https://raw.githubusercontent.com/microsoft/BIPIA/main/benchmark/code_attack_test.json) | `892545c5aaec0645b1ded65dc7816b3d70e9ef4eadcba2301a7a3db93676b6e0` |
| [injecagent](https://github.com/uiuc-kang-lab/InjecAgent) | [`data/attacker_cases_ds.jsonl`](https://raw.githubusercontent.com/uiuc-kang-lab/InjecAgent/main/data/attacker_cases_ds.jsonl) | `87952398c989d8ca841724e38ecdbb789676d3841e19dfc44aac7b710df9cb1f` |
| [injecagent](https://github.com/uiuc-kang-lab/InjecAgent) | [`data/attacker_cases_dh.jsonl`](https://raw.githubusercontent.com/uiuc-kang-lab/InjecAgent/main/data/attacker_cases_dh.jsonl) | `999d52e15af3c80a3303a09430af0f3878d1f91e4c573ca7b477a91cdfa6b991` |
| [harmbench](https://github.com/centerforaisafety/HarmBench) | [`baselines/gptfuzz/GPTFuzzer.csv`](https://raw.githubusercontent.com/centerforaisafety/HarmBench/main/baselines/gptfuzz/GPTFuzzer.csv) | `e4abf25343b4adb991dd8ddc6189c038f26a6e74064d792cced69f56f71577fc` |
| [harmbench](https://github.com/centerforaisafety/HarmBench) | [`baselines/human_jailbreaks/jailbreaks.py`](https://raw.githubusercontent.com/centerforaisafety/HarmBench/main/baselines/human_jailbreaks/jailbreaks.py) | `62e53558de1da3e67d1aec15c0dff59c848c0b374fd262ffad8f723fda0cd099` |
| [agentdojo](https://github.com/ethz-spylab/agentdojo) | [`src/agentdojo/attacks/important_instructions_attacks.py`](https://raw.githubusercontent.com/ethz-spylab/agentdojo/main/src/agentdojo/attacks/important_instructions_attacks.py) | `519f24e0b9d72f43343d665679adacc33758b50cd1b586a81fa53fb098dcfe71` |
| [agentdojo](https://github.com/ethz-spylab/agentdojo) | [`src/agentdojo/attacks/baseline_attacks.py`](https://raw.githubusercontent.com/ethz-spylab/agentdojo/main/src/agentdojo/attacks/baseline_attacks.py) | `0e3f3cec2173524989d67bd3d934d032774ad3fc5995969c9565613efaa21c6d` |

Corpus revision: `78bec9caedc7b5dc0e2ee5e5d74632460b46bdec5fec221ebe0ba7a70f60b6bc`.

## Server-owned provenance and application development

The Red model can choose resources and write candidates but cannot supply trusted attribution as an assertion. [red.py](../backend/aegis_v2/red.py) constructs `red_strategy` from actual tool results. Recorded source IDs, methods, tactic IDs, composition hashes, and transformed-text use provide the audit trail.

A transformation's `insertion_token` materializes the exact returned string, supporting chained transformations and invisible Unicode without asking the model to reconstruct bytes. Validation follows insertion. Tool names/arguments are allowlisted; completed operations are read back during replay rather than claimed from prose.

AEGIS develops its own versioned target contract, family/property mapping, coverage scheduler, persistent phase controller, model accounting, native/JSON Red loop, target JSON adapter, simulated tool gateway, trusted authorization, scoped deterministic/semantic evaluation, supported control candidates, frozen final protocol, role-scoped evidence vault, report crosswalks, and English interface. These integration/application layers are not copied complete upstream campaign engines.

## Defense and standards references

- [OWASP prevention guidance](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html): policy/data separation, layered boundaries, trusted retrieval/tool authorization, and regression/utility evaluation.
- [python-jsonschema](https://python-jsonschema.readthedocs.io/): complete response/tool schemas.
- [Guardrails AI](https://github.com/guardrails-ai/guardrails): optional actual schema validator only.
- [Presidio](https://microsoft.github.io/presidio/): optional registered-pattern redaction only.
- [NeMo Guardrails](https://github.com/NVIDIA/NeMo-Guardrails) and [LLM Guard](https://github.com/protectai/llm-guard): researched references, not executable integrations.
- [MITRE ATLAS](https://atlas.mitre.org/): supported evidence mappings, pinned [catalog metadata](../backend/aegis_v2/catalogs/atlas.json).
- [NIST AI RMF](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf) and [Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf): scoped evidence crosswalks, not certification.

## Complete 90-source research inventory

This table is generated from [red-team-source-inventory.json](red-team-source-inventory.json); it preserves each source's recorded status. Capability descriptions describe the upstream project, not features all available in AEGIS. The four "installed components" entries are the Red frameworks; jsonschema, Guardrails, and Presidio are documented separately above.

Status summary: **4 installed-component projects, 6 indexed-material projects, 17 reference-only entries, 62 unconnected entries, and 1 gated/unconnected dataset**. Last recorded URL checks are part of the JSON inventory; those checks are not current runtime integration tests.

| Project | Category | Upstream capability | Recorded AEGIS status |
|---|---|---|---|
| [PyRIT](https://github.com/microsoft/PyRIT) | framework | Multi-turn orchestration, seed resources, converters, and scorers | Installed components |
| [Garak](https://github.com/NVIDIA/garak) | framework | Vulnerability scanning through probes, generators, buffs, and detectors | Installed components |
| [Promptfoo](https://github.com/promptfoo/promptfoo) | framework | LLM application evaluation with red-team plugins and strategies | Installed components |
| [DeepTeam](https://github.com/confident-ai/deepteam) | framework | Single- and multi-turn attacks for agent authorization, disclosure, and safety evaluation | Installed components |
| [Giskard](https://github.com/Giskard-AI/giskard) | framework | LLM and RAG testing, automatic issue discovery, and test-data generation | Not connected |
| [Moonshot](https://github.com/aiverify-foundation/moonshot) | framework | Connectors, recipes, benchmarks, and a modular red-team runner | Not connected |
| [FuzzyAI](https://github.com/cyberark/FuzzyAI) | framework | API fuzzing, genetic search, and jailbreak attacks | Not connected |
| [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai) | evaluation | Agent evaluation with sandboxes, tool-using solvers, and scorers | Not connected |
| [Inspect Evals](https://github.com/UKGovernmentBEIS/inspect_evals) | evaluation | Standard benchmark implementations built on Inspect | Not connected |
| [Adversarial Robustness Toolbox](https://github.com/Trusted-AI/adversarial-robustness-toolbox) | framework | Adversarial robustness, poisoning, and extraction tests for ML and multimodal systems | Not connected |
| [TextAttack](https://github.com/QData/TextAttack) | framework | Adversarial NLP examples, word-level transformations, and search | Not connected |
| [OpenAttack](https://github.com/thunlp/OpenAttack) | framework | Text adversarial attacks and target-model connectors | Not connected |
| [Counterfit](https://github.com/Azure/counterfit) | framework | Unified access to ML security tools; an older project that requires compatibility checks | Not connected |
| [EasyJailbreak](https://github.com/EasyJailbreak/EasyJailbreak) | framework | Modular jailbreak mutators, selectors, and evaluators | Not connected |
| [JailbreakEval](https://github.com/ThuCCSLab/JailbreakEval) | evaluation | Methods for evaluating jailbreak outcomes | Not connected |
| [LLAMATOR](https://github.com/LLAMATOR-Core/llamator) | framework | Multi-turn LLM attack campaigns and evaluation | Not connected |
| [Agentic Security](https://github.com/msoedov/agentic_security) | framework | LLM endpoint security scanning and prompt fuzzing | Not connected |
| [Promptmap](https://github.com/utkusen/promptmap) | framework | Prompt-injection scanning for LLM applications | Not connected |
| [LLMFuzzer](https://github.com/mnns/LLMFuzzer) | framework | LLM API fuzzing and extensible test workflows | Not connected |
| [PromptInject](https://github.com/agencyenterprise/PromptInject) | framework | An early modular framework for prompt-injection experiments | Not connected |
| [HouYi](https://github.com/LLMSecurity/HouYi) | framework | Black-box prompt injection adapted to application context | Not connected |
| [HackAgent](https://github.com/AISecurityLab/hackagent) | framework | SDK and CLI execution of research attacks against AI agents | Not connected |
| [OpenRT](https://github.com/AI45Lab/OpenRT) | framework | Multiple attack algorithms for multimodal models | Not connected |
| [JailbreakBench](https://github.com/JailbreakBench/jailbreakbench) | evaluation | Standard threat models, behaviors, adversarial artifacts, and evaluation | Not connected |
| [HarmBench](https://github.com/centerforaisafety/HarmBench) | evaluation | Standard harmful-behavior evaluation and attack baseline implementations | Indexed template fragments |
| [StrongREJECT](https://github.com/alexandrasouly/strongreject) | evaluation | Evaluation of whether a response meaningfully satisfies an attack objective | Not connected |
| [AgentDojo](https://github.com/ethz-spylab/agentdojo) | evaluation | Tool-using agent tasks, adversarial tool-result surfaces, and security/usefulness measurement | Indexed template fragments |
| [AgentHarm](https://huggingface.co/datasets/ai-safety-institute/AgentHarm) | dataset | Harmful multi-step agent tasks with benchmark-specific usage terms | Not connected |
| [InjecAgent](https://github.com/uiuc-kang-lab/InjecAgent) | dataset | Indirect injection against tool-integrated agents, including disclosure and harmful actions | Indexed attack templates |
| [BIPIA](https://github.com/microsoft/BIPIA) | dataset | Indirect prompt-injection tasks and attack templates in external data carriers | Indexed attack templates |
| [TensorTrust Data](https://github.com/HumanCompatibleAI/tensor-trust-data) | dataset | Research data from human-written prompt-injection game attacks | Indexed attacker inputs |
| [TensorTrust Game](https://github.com/HumanCompatibleAI/tensor-trust) | reference | Game threat model, attack/defense workflow, and data-generation context | Reference only |
| [WildTeaming](https://github.com/allenai/wildteaming) | algorithm | Mining real-world tactics, composing tactics, and attack pruning | Indexed tactics/composition |
| [WildJailbreak](https://huggingface.co/datasets/allenai/wildjailbreak) | dataset | Benign, adversarial, and direct examples with response pairs; dataset access terms apply | Gated / not connected |
| [JailbreakLLMs](https://github.com/TrustAIRLab/JailbreakLLMs) | dataset | Real-world jailbreak prompts and analysis | Not connected |
| [Jailbreak LLMs Study](https://github.com/verazuo/jailbreak_llms) | dataset | Primary collection and analysis code for in-the-wild jailbreak research | Not connected |
| [CyberSecEval / PurpleLlama](https://github.com/meta-llama/PurpleLlama) | evaluation | Prompt-injection, agent, and cybersecurity risk evaluation | Not connected |
| [AdvBench / GCG](https://github.com/llm-attacks/llm-attacks) | algorithm | Gradient-based adversarial suffix optimization requiring model weights and GPU access | Not connected |
| [PAIR](https://github.com/patrickrchao/JailbreakingLLMs) | algorithm | Iterative prompt improvement using an attacker model and target feedback | Not connected |
| [TAP](https://github.com/RICommunity/TAP) | algorithm | Tree-of-attacks search with branching and pruning for black-box tests | Not connected |
| [AutoDAN](https://github.com/SheltonLiu-N/AutoDAN) | algorithm | Genetic optimization of fluent jailbreak prompts | Not connected |
| [AutoDAN-Turbo](https://github.com/SaFoLab-WISC/AutoDAN-Turbo) | algorithm | Strategy memory and continual attack-strategy discovery | Not connected |
| [BEAST](https://github.com/vinusankars/BEAST) | algorithm | Token-level search for adversarial prompt optimization | Not connected |
| [GPTFuzzer](https://github.com/sherdencooper/GPTFuzz) | algorithm | Seed mutation, selection, and fuzzing guided by target responses | Not connected |
| [ArtPrompt](https://github.com/uw-nsl/ArtPrompt) | algorithm | ASCII-art representations for testing token/semantic interpretation boundaries | Not connected |
| [FlipAttack](https://github.com/yueliu1999/FlipAttack) | algorithm | Character or word reordering and reconstruction as instruction laundering | Not connected |
| [DeepInception](https://github.com/tmlr-group/DeepInception) | algorithm | Nested fictional environments and simulation layers | Not connected |
| [ReNeLLM](https://github.com/NJUNLP/ReNeLLM) | algorithm | Prompt rewriting and scenario nesting for attack generation | Not connected |
| [CipherChat](https://github.com/RobustNLP/CipherChat) | algorithm | Alternative-language or cipher representations for safety testing | Not connected |
| [CodeAttack](https://github.com/renqibing/CodeAttack) | algorithm | Embedding instructions in code contexts to test model safeguards | Not connected |
| [DrAttack](https://github.com/xirui-li/DrAttack) | algorithm | Prompt decomposition and reconstruction for black-box attacks | Not connected |
| [Crescendo](https://crescendo-the-multiturn-jailbreak.github.io/) | algorithm | Multi-turn escalation from a benign opening toward a conflicting objective | Not connected |
| [Many-shot Jailbreaking](https://www.anthropic.com/research/many-shot-jailbreaking) | algorithm | Behavior steering through many examples in a long context | Not connected |
| [Skeleton Key](https://www.microsoft.com/en-us/security/blog/2024/06/26/mitigating-skeleton-key-a-new-type-of-generative-ai-jailbreak-technique/) | algorithm | Instructions that attempt to change how a model applies its safety rules | Not connected |
| [Bad Likert Judge](https://unit42.paloaltonetworks.com/multi-turn-technique-jailbreaks-llms/) | algorithm | Multi-turn attacks using a model's judging role and scoring examples | Not connected |
| [Best-of-N Jailbreaking](https://jplhughes.github.io/bon-jailbreaking/) | algorithm | Sampling multiple text, audio, or image perturbations | Not connected |
| [HarmfulQA](https://github.com/declare-lab/red-instruct) | dataset | The HarmfulQA and Red-Instruct red-team data approach | Not connected |
| [Do-Not-Answer](https://github.com/Libr-AI/do-not-answer) | dataset | Evaluation requests covering risks that models should not answer | Not connected |
| [XSTest](https://github.com/paul-rottger/exaggerated-safety) | dataset | Tests for excessive refusal of harmless requests | Not connected |
| [SafetyBench](https://github.com/thu-coai/SafetyBench) | dataset | Safety questions across multiple categories | Not connected |
| [SALAD-Bench](https://github.com/OpenSafetyLab/SALAD-BENCH) | dataset | Safety taxonomy, attack-enhanced examples, and evaluation | Not connected |
| [ALERT](https://github.com/Babelscape/ALERT) | dataset | Risk categories for red teaming and safety evaluation | Not connected |
| [BeaverTails](https://github.com/PKU-Alignment/beavertails) | dataset | Safety annotations and categories for model responses | Not connected |
| [Safe-RLHF](https://github.com/PKU-Alignment/safe-rlhf) | dataset | Safety/helpfulness data and training/evaluation research | Not connected |
| [Anthropic HH-RLHF](https://huggingface.co/datasets/Anthropic/hh-rlhf) | dataset | Helpful/harmless preference pairs and red-team attempts | Not connected |
| [Anthropic Red Teaming](https://huggingface.co/datasets/Anthropic/hh-rlhf/tree/main/red-team-attempts) | dataset | Human red-team conversations with privacy and usage considerations | Not connected |
| [ToxicChat](https://huggingface.co/datasets/lmsys/toxic-chat) | dataset | Toxicity and adversarial examples from real user conversations | Not connected |
| [TrustLLM](https://github.com/HowieHwong/TrustLLM) | evaluation | Trustworthiness, safety, privacy, and robustness evaluation | Not connected |
| [DecodingTrust](https://github.com/AI-secure/DecodingTrust) | evaluation | Adversarial tests and measurement of model trustworthiness | Not connected |
| [HELM](https://github.com/stanford-crfm/helm) | evaluation | Standard model scenarios and measurements for comparison | Not connected |
| [LM Evaluation Harness](https://github.com/EleutherAI/lm-evaluation-harness) | evaluation | Reproducible model benchmark infrastructure | Not connected |
| [DeepEval](https://github.com/confident-ai/deepeval) | evaluation | LLM tests and scorers; a separate evaluation package from DeepTeam | Not connected |
| [Ragas](https://github.com/vibrantlabsai/ragas) | evaluation | RAG quality measurement and synthetic test-data generation | Not connected |
| [Rebuff](https://github.com/protectai/rebuff) | defense | Prompt-injection detection and canary checks; a defense rather than an attack generator | Reference only |
| [NeMo Guardrails](https://github.com/NVIDIA/NeMo-Guardrails) | defense | Policies and guardrails for conversation, tool, and output flows | Reference only |
| [Guardrails AI](https://github.com/guardrails-ai/guardrails) | defense | Schema- and validator-based input/output checks | Reference only |
| [LLM Guard](https://github.com/protectai/llm-guard) | defense | Input/output scanning for injection and disclosure risks | Reference only |
| [Llama Guard](https://huggingface.co/meta-llama/Llama-Guard-3-8B) | defense | A safety-classifier model; its weights are not downloaded by this integration | Reference only |
| [Prompt Guard](https://huggingface.co/meta-llama/Prompt-Guard-86M) | defense | A prompt-injection/jailbreak classifier; its weights are not downloaded here | Reference only |
| [ShieldGemma](https://huggingface.co/google/shieldgemma-2b) | defense | A safety-policy classifier model with separate access terms | Reference only |
| [ModelScan](https://github.com/protectai/modelscan) | reference | Unsafe serialization scanning for model files; a supply-chain security tool | Reference only |
| [MITRE ATLAS](https://atlas.mitre.org/) | reference | AI attack tactics, techniques, and case mappings | Reference only |
| [OWASP GenAI Security Project](https://genai.owasp.org/) | reference | LLM and agent security risks and test-scope guidance | Reference only |
| [OWASP LLM Top 10](https://genai.owasp.org/llm-top-10/) | reference | Application risks including injection, disclosure, and excessive agency | Reference only |
| [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework) | reference | Risk management, measurement, and evaluation guidance | Reference only |
| [NIST GenAI Profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence) | reference | The generative AI risk-management profile | Reference only |
| [AI Verify](https://github.com/aiverify-foundation/aiverify) | evaluation | AI testing and reporting infrastructure; a separate project from Moonshot | Not connected |
| [Lakera Gandalf](https://gandalf.lakera.ai/) | reference | Interactive prompt-injection exercises; AEGIS does not attack this external service | Reference only |
| [Microsoft AI Red Team](https://www.microsoft.com/en-us/research/publication/lessons-from-red-teaming-100-generative-ai-products/) | reference | Product red-teaming experience and methodology findings | Reference only |
| [Anthropic Agent Injection Research](https://www.anthropic.com/research/prompt-injection-defenses) | reference | Prompt-injection defenses and evaluation for tool-using systems | Reference only |

## Attribution and redistribution

Recorded code licenses: PyRIT/Promptfoo MIT; Garak/DeepTeam Apache-2.0. Dataset/template licenses remain separate from framework licenses. Preserve original notices and the nested resource attribution when using extracted material.

TensorTrust and WildTeaming snapshots have no clearly specified dataset license in the recorded source metadata. Their raw files and local corpus remain ignored runtime data rather than redistributed repository assets. WildJailbreak access terms have not been accepted and its dataset is unconnected. BIPIA imports only the recorded MIT attack templates, not carrier datasets.

No project-wide AEGIS LICENSE file was found in this checkout. This reference records provenance; it does not grant additional rights to upstream code/data or assign a project license.

