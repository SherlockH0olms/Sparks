"""Verify primary source links and generate the research inventory (no installs)."""
from concurrent.futures import ThreadPoolExecutor
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]

# Name | primary URL | category | concrete capability. Algorithms remain
# research references unless their actual execution is verified by an adapter.
ROWS = """
PyRIT|https://github.com/microsoft/PyRIT|framework|Multi-turn orchestration, seed resources, converters, and scorers
Garak|https://github.com/NVIDIA/garak|framework|Vulnerability scanning through probes, generators, buffs, and detectors
Promptfoo|https://github.com/promptfoo/promptfoo|framework|LLM application evaluation with red-team plugins and strategies
DeepTeam|https://github.com/confident-ai/deepteam|framework|Single- and multi-turn attacks for agent authorization, disclosure, and safety evaluation
Giskard|https://github.com/Giskard-AI/giskard|framework|LLM and RAG testing, automatic issue discovery, and test-data generation
Moonshot|https://github.com/aiverify-foundation/moonshot|framework|Connectors, recipes, benchmarks, and a modular red-team runner
FuzzyAI|https://github.com/cyberark/FuzzyAI|framework|API fuzzing, genetic search, and jailbreak attacks
Inspect AI|https://github.com/UKGovernmentBEIS/inspect_ai|evaluation|Agent evaluation with sandboxes, tool-using solvers, and scorers
Inspect Evals|https://github.com/UKGovernmentBEIS/inspect_evals|evaluation|Standard benchmark implementations built on Inspect
Adversarial Robustness Toolbox|https://github.com/Trusted-AI/adversarial-robustness-toolbox|framework|Adversarial robustness, poisoning, and extraction tests for ML and multimodal systems
TextAttack|https://github.com/QData/TextAttack|framework|Adversarial NLP examples, word-level transformations, and search
OpenAttack|https://github.com/thunlp/OpenAttack|framework|Text adversarial attacks and target-model connectors
Counterfit|https://github.com/Azure/counterfit|framework|Unified access to ML security tools; an older project that requires compatibility checks
EasyJailbreak|https://github.com/EasyJailbreak/EasyJailbreak|framework|Modular jailbreak mutators, selectors, and evaluators
JailbreakEval|https://github.com/ThuCCSLab/JailbreakEval|evaluation|Methods for evaluating jailbreak outcomes
LLAMATOR|https://github.com/LLAMATOR-Core/llamator|framework|Multi-turn LLM attack campaigns and evaluation
Agentic Security|https://github.com/msoedov/agentic_security|framework|LLM endpoint security scanning and prompt fuzzing
Promptmap|https://github.com/utkusen/promptmap|framework|Prompt-injection scanning for LLM applications
LLMFuzzer|https://github.com/mnns/LLMFuzzer|framework|LLM API fuzzing and extensible test workflows
PromptInject|https://github.com/agencyenterprise/PromptInject|framework|An early modular framework for prompt-injection experiments
HouYi|https://github.com/LLMSecurity/HouYi|framework|Black-box prompt injection adapted to application context
HackAgent|https://github.com/AISecurityLab/hackagent|framework|SDK and CLI execution of research attacks against AI agents
OpenRT|https://github.com/AI45Lab/OpenRT|framework|Multiple attack algorithms for multimodal models
JailbreakBench|https://github.com/JailbreakBench/jailbreakbench|evaluation|Standard threat models, behaviors, adversarial artifacts, and evaluation
HarmBench|https://github.com/centerforaisafety/HarmBench|evaluation|Standard harmful-behavior evaluation and attack baseline implementations
StrongREJECT|https://github.com/alexandrasouly/strongreject|evaluation|Evaluation of whether a response meaningfully satisfies an attack objective
AgentDojo|https://github.com/ethz-spylab/agentdojo|evaluation|Tool-using agent tasks, adversarial tool-result surfaces, and security/usefulness measurement
AgentHarm|https://huggingface.co/datasets/ai-safety-institute/AgentHarm|dataset|Harmful multi-step agent tasks with benchmark-specific usage terms
InjecAgent|https://github.com/uiuc-kang-lab/InjecAgent|dataset|Indirect injection against tool-integrated agents, including disclosure and harmful actions
BIPIA|https://github.com/microsoft/BIPIA|dataset|Indirect prompt-injection tasks and attack templates in external data carriers
TensorTrust Data|https://github.com/HumanCompatibleAI/tensor-trust-data|dataset|Research data from human-written prompt-injection game attacks
TensorTrust Game|https://github.com/HumanCompatibleAI/tensor-trust|reference|Game threat model, attack/defense workflow, and data-generation context
WildTeaming|https://github.com/allenai/wildteaming|algorithm|Mining real-world tactics, composing tactics, and attack pruning
WildJailbreak|https://huggingface.co/datasets/allenai/wildjailbreak|dataset|Benign, adversarial, and direct examples with response pairs; dataset access terms apply
JailbreakLLMs|https://github.com/TrustAIRLab/JailbreakLLMs|dataset|Real-world jailbreak prompts and analysis
Jailbreak LLMs Study|https://github.com/verazuo/jailbreak_llms|dataset|Primary collection and analysis code for in-the-wild jailbreak research
CyberSecEval / PurpleLlama|https://github.com/meta-llama/PurpleLlama|evaluation|Prompt-injection, agent, and cybersecurity risk evaluation
AdvBench / GCG|https://github.com/llm-attacks/llm-attacks|algorithm|Gradient-based adversarial suffix optimization requiring model weights and GPU access
PAIR|https://github.com/patrickrchao/JailbreakingLLMs|algorithm|Iterative prompt improvement using an attacker model and target feedback
TAP|https://github.com/RICommunity/TAP|algorithm|Tree-of-attacks search with branching and pruning for black-box tests
AutoDAN|https://github.com/SheltonLiu-N/AutoDAN|algorithm|Genetic optimization of fluent jailbreak prompts
AutoDAN-Turbo|https://github.com/SaFoLab-WISC/AutoDAN-Turbo|algorithm|Strategy memory and continual attack-strategy discovery
BEAST|https://github.com/vinusankars/BEAST|algorithm|Token-level search for adversarial prompt optimization
GPTFuzzer|https://github.com/sherdencooper/GPTFuzz|algorithm|Seed mutation, selection, and fuzzing guided by target responses
ArtPrompt|https://github.com/uw-nsl/ArtPrompt|algorithm|ASCII-art representations for testing token/semantic interpretation boundaries
FlipAttack|https://github.com/yueliu1999/FlipAttack|algorithm|Character or word reordering and reconstruction as instruction laundering
DeepInception|https://github.com/tmlr-group/DeepInception|algorithm|Nested fictional environments and simulation layers
ReNeLLM|https://github.com/NJUNLP/ReNeLLM|algorithm|Prompt rewriting and scenario nesting for attack generation
CipherChat|https://github.com/RobustNLP/CipherChat|algorithm|Alternative-language or cipher representations for safety testing
CodeAttack|https://github.com/renqibing/CodeAttack|algorithm|Embedding instructions in code contexts to test model safeguards
DrAttack|https://github.com/xirui-li/DrAttack|algorithm|Prompt decomposition and reconstruction for black-box attacks
Crescendo|https://crescendo-the-multiturn-jailbreak.github.io/|algorithm|Multi-turn escalation from a benign opening toward a conflicting objective
Many-shot Jailbreaking|https://www.anthropic.com/research/many-shot-jailbreaking|algorithm|Behavior steering through many examples in a long context
Skeleton Key|https://www.microsoft.com/en-us/security/blog/2024/06/26/mitigating-skeleton-key-a-new-type-of-generative-ai-jailbreak-technique/|algorithm|Instructions that attempt to change how a model applies its safety rules
Bad Likert Judge|https://unit42.paloaltonetworks.com/multi-turn-technique-jailbreaks-llms/|algorithm|Multi-turn attacks using a model's judging role and scoring examples
Best-of-N Jailbreaking|https://jplhughes.github.io/bon-jailbreaking/|algorithm|Sampling multiple text, audio, or image perturbations
HarmfulQA|https://github.com/declare-lab/red-instruct|dataset|The HarmfulQA and Red-Instruct red-team data approach
Do-Not-Answer|https://github.com/Libr-AI/do-not-answer|dataset|Evaluation requests covering risks that models should not answer
XSTest|https://github.com/paul-rottger/exaggerated-safety|dataset|Tests for excessive refusal of harmless requests
SafetyBench|https://github.com/thu-coai/SafetyBench|dataset|Safety questions across multiple categories
SALAD-Bench|https://github.com/OpenSafetyLab/SALAD-BENCH|dataset|Safety taxonomy, attack-enhanced examples, and evaluation
ALERT|https://github.com/Babelscape/ALERT|dataset|Risk categories for red teaming and safety evaluation
BeaverTails|https://github.com/PKU-Alignment/beavertails|dataset|Safety annotations and categories for model responses
Safe-RLHF|https://github.com/PKU-Alignment/safe-rlhf|dataset|Safety/helpfulness data and training/evaluation research
Anthropic HH-RLHF|https://huggingface.co/datasets/Anthropic/hh-rlhf|dataset|Helpful/harmless preference pairs and red-team attempts
Anthropic Red Teaming|https://huggingface.co/datasets/Anthropic/hh-rlhf/tree/main/red-team-attempts|dataset|Human red-team conversations with privacy and usage considerations
ToxicChat|https://huggingface.co/datasets/lmsys/toxic-chat|dataset|Toxicity and adversarial examples from real user conversations
TrustLLM|https://github.com/HowieHwong/TrustLLM|evaluation|Trustworthiness, safety, privacy, and robustness evaluation
DecodingTrust|https://github.com/AI-secure/DecodingTrust|evaluation|Adversarial tests and measurement of model trustworthiness
HELM|https://github.com/stanford-crfm/helm|evaluation|Standard model scenarios and measurements for comparison
LM Evaluation Harness|https://github.com/EleutherAI/lm-evaluation-harness|evaluation|Reproducible model benchmark infrastructure
DeepEval|https://github.com/confident-ai/deepeval|evaluation|LLM tests and scorers; a separate evaluation package from DeepTeam
Ragas|https://github.com/vibrantlabsai/ragas|evaluation|RAG quality measurement and synthetic test-data generation
Rebuff|https://github.com/protectai/rebuff|defense|Prompt-injection detection and canary checks; a defense rather than an attack generator
NeMo Guardrails|https://github.com/NVIDIA/NeMo-Guardrails|defense|Policies and guardrails for conversation, tool, and output flows
Guardrails AI|https://github.com/guardrails-ai/guardrails|defense|Schema- and validator-based input/output checks
LLM Guard|https://github.com/protectai/llm-guard|defense|Input/output scanning for injection and disclosure risks
Llama Guard|https://huggingface.co/meta-llama/Llama-Guard-3-8B|defense|A safety-classifier model; its weights are not downloaded by this integration
Prompt Guard|https://huggingface.co/meta-llama/Prompt-Guard-86M|defense|A prompt-injection/jailbreak classifier; its weights are not downloaded here
ShieldGemma|https://huggingface.co/google/shieldgemma-2b|defense|A safety-policy classifier model with separate access terms
ModelScan|https://github.com/protectai/modelscan|reference|Unsafe serialization scanning for model files; a supply-chain security tool
MITRE ATLAS|https://atlas.mitre.org/|reference|AI attack tactics, techniques, and case mappings
OWASP GenAI Security Project|https://genai.owasp.org/|reference|LLM and agent security risks and test-scope guidance
OWASP LLM Top 10|https://genai.owasp.org/llm-top-10/|reference|Application risks including injection, disclosure, and excessive agency
NIST AI RMF|https://www.nist.gov/itl/ai-risk-management-framework|reference|Risk management, measurement, and evaluation guidance
NIST GenAI Profile|https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence|reference|The generative AI risk-management profile
AI Verify|https://github.com/aiverify-foundation/aiverify|evaluation|AI testing and reporting infrastructure; a separate project from Moonshot
Lakera Gandalf|https://gandalf.lakera.ai/|reference|Interactive prompt-injection exercises; AEGIS does not attack this external service
Microsoft AI Red Team|https://www.microsoft.com/en-us/research/publication/lessons-from-red-teaming-100-generative-ai-products/|reference|Product red-teaming experience and methodology findings
Anthropic Agent Injection Research|https://www.anthropic.com/research/prompt-injection-defenses|reference|Prompt-injection defenses and evaluation for tool-using systems
""".strip()

INTEGRATED = {"PyRIT": "installed_components", "Garak": "installed_components", "Promptfoo": "installed_components",
    "DeepTeam": "installed_components", "TensorTrust Data": "indexed_attacker_inputs", "BIPIA": "indexed_attack_templates",
    "InjecAgent": "indexed_attack_templates", "HarmBench": "indexed_template_fragments", "AgentDojo": "indexed_template_fragments",
    "WildTeaming": "indexed_tactics_and_composition", "WildJailbreak": "gated_unconnected"}


def verify(row):
    name, url, category, capability = row.split("|", 3)
    status = INTEGRATED.get(name, "reference_only" if category in {"reference", "defense"} else "not_connected")
    requires = {"algorithm": "Target/model adapter; some methods also need attacker/scorer models, model weights, or GPU access",
        "framework": "Framework dependencies, a target adapter, and an appropriate test environment",
        "dataset": "Dataset license/access terms and adaptation to the registered target",
        "evaluation": "Task/scorer adapters, target outputs, and benchmark license requirements",
        "defense": "Defense or classifier; not counted as an attack generator",
        "reference": "Methodology or scope guidance; not an executable attack component"}[category]
    entry = {"id": name.lower().replace(" ", "_"), "name": name, "url": url, "category": category,
             "capability": capability, "integration_status": status, "requirements": requires}
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "AEGIS-Research/1.0"}, method="HEAD")
        with urllib.request.urlopen(request, timeout=25) as response:
            entry.update(http_status=response.status, resolved_url=response.url, link_verified=True)
    except urllib.error.HTTPError as exc:
        entry.update(http_status=exc.code, link_verified=False)
    except Exception as exc:
        entry.update(http_status=None, link_verified=False, verification_error=type(exc).__name__)
    return entry


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-cached",action="store_true",help="Render the existing verified inventory without network requests")
    args=parser.parse_args()
    if args.render_cached:
        entries=json.loads((ROOT/"docs/red-team-source-inventory.json").read_text(encoding="utf-8"))
        timestamp=entries[0]["checked_at"]
    else:
        with ThreadPoolExecutor(max_workers=8) as pool:
            entries = list(pool.map(verify, ROWS.splitlines()))
        timestamp = datetime.now(timezone.utc).isoformat()
        for entry in entries:
            entry["checked_at"] = timestamp
    path = ROOT / "docs/red-team-source-inventory.json"
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# AI red-team source inventory", "", f"Links checked: {timestamp}. {len(entries)} primary sources.", "",
        "Frameworks, datasets, algorithms, evaluation tools, defenses, and references are listed separately. A verified link does not imply that a package is installed or integrated. `installed_components` and `indexed_*` identify the connected parts; other entries are research references. The integration report records which APIs were actually executed.", "",
        "WildJailbreak is not connected because its access terms have not been accepted. An explicit data license was not found for TensorTrust or WildTeaming: local snapshots stay under `.runtime` and are not committed. AgentHarm and model sources have separate usage requirements.", ""]
    for category in ("framework", "algorithm", "dataset", "evaluation", "defense", "reference"):
        lines.extend(["## " + category, ""])
        for entry in entries:
            if entry["category"] != category:
                continue
            lines.extend([f"### {entry['name']}", "", f"Source: [{entry['url']}]({entry['url']})", "",
                f"Capability: {entry['capability']}. Requirements: {entry['requirements']}.", "",
                f"AEGIS integration: `{entry['integration_status']}`. Link: HTTP {entry.get('http_status')}; " +
                ("verified." if entry['link_verified'] else "not verified automatically."), ""])
    (ROOT / "docs/RED-TEAM-KAYNAK-ENVANTERI.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"entries": len(entries), "verified": sum(e['link_verified'] for e in entries),
        "unverified": [{"name": e['name'], "url": e['url'], "status": e['http_status']} for e in entries if not e['link_verified']]}, ensure_ascii=True))


if __name__ == "__main__":
    main()
