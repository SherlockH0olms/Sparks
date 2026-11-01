# AI red-team source inventory

Links checked: 2026-10-31T22:02:39.977665+00:00. 90 primary sources.

Frameworks, datasets, algorithms, evaluation tools, defenses, and references are listed separately. A verified link does not imply that a package is installed or integrated. `installed_components` and `indexed_*` identify the connected parts; other entries are research references. The integration report records which APIs were actually executed.

WildJailbreak is not connected because its access terms have not been accepted. An explicit data license was not found for TensorTrust or WildTeaming: local snapshots stay under `.runtime` and are not committed. AgentHarm and model sources have separate usage requirements.

## framework

### PyRIT

Source: [https://github.com/microsoft/PyRIT](https://github.com/microsoft/PyRIT)

Capability: Multi-turn orchestration, seed resources, converters, and scorers. Requirements: Framework dependencies, a target adapter, and an appropriate test environment.

AEGIS integration: `installed_components`. Link: HTTP 200; verified.

### Garak

Source: [https://github.com/NVIDIA/garak](https://github.com/NVIDIA/garak)

Capability: Vulnerability scanning through probes, generators, buffs, and detectors. Requirements: Framework dependencies, a target adapter, and an appropriate test environment.

AEGIS integration: `installed_components`. Link: HTTP 200; verified.

### Promptfoo

Source: [https://github.com/promptfoo/promptfoo](https://github.com/promptfoo/promptfoo)

Capability: LLM application evaluation with red-team plugins and strategies. Requirements: Framework dependencies, a target adapter, and an appropriate test environment.

AEGIS integration: `installed_components`. Link: HTTP 200; verified.

### DeepTeam

Source: [https://github.com/confident-ai/deepteam](https://github.com/confident-ai/deepteam)

Capability: Single- and multi-turn attacks for agent authorization, disclosure, and safety evaluation. Requirements: Framework dependencies, a target adapter, and an appropriate test environment.

AEGIS integration: `installed_components`. Link: HTTP 200; verified.

### Giskard

Source: [https://github.com/Giskard-AI/giskard](https://github.com/Giskard-AI/giskard)

Capability: LLM and RAG testing, automatic issue discovery, and test-data generation. Requirements: Framework dependencies, a target adapter, and an appropriate test environment.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### Moonshot

Source: [https://github.com/aiverify-foundation/moonshot](https://github.com/aiverify-foundation/moonshot)

Capability: Connectors, recipes, benchmarks, and a modular red-team runner. Requirements: Framework dependencies, a target adapter, and an appropriate test environment.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### FuzzyAI

Source: [https://github.com/cyberark/FuzzyAI](https://github.com/cyberark/FuzzyAI)

Capability: API fuzzing, genetic search, and jailbreak attacks. Requirements: Framework dependencies, a target adapter, and an appropriate test environment.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### Adversarial Robustness Toolbox

Source: [https://github.com/Trusted-AI/adversarial-robustness-toolbox](https://github.com/Trusted-AI/adversarial-robustness-toolbox)

Capability: Adversarial robustness, poisoning, and extraction tests for ML and multimodal systems. Requirements: Framework dependencies, a target adapter, and an appropriate test environment.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### TextAttack

Source: [https://github.com/QData/TextAttack](https://github.com/QData/TextAttack)

Capability: Adversarial NLP examples, word-level transformations, and search. Requirements: Framework dependencies, a target adapter, and an appropriate test environment.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### OpenAttack

Source: [https://github.com/thunlp/OpenAttack](https://github.com/thunlp/OpenAttack)

Capability: Text adversarial attacks and target-model connectors. Requirements: Framework dependencies, a target adapter, and an appropriate test environment.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### Counterfit

Source: [https://github.com/Azure/counterfit](https://github.com/Azure/counterfit)

Capability: Unified access to ML security tools; an older project that requires compatibility checks. Requirements: Framework dependencies, a target adapter, and an appropriate test environment.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### EasyJailbreak

Source: [https://github.com/EasyJailbreak/EasyJailbreak](https://github.com/EasyJailbreak/EasyJailbreak)

Capability: Modular jailbreak mutators, selectors, and evaluators. Requirements: Framework dependencies, a target adapter, and an appropriate test environment.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### LLAMATOR

Source: [https://github.com/LLAMATOR-Core/llamator](https://github.com/LLAMATOR-Core/llamator)

Capability: Multi-turn LLM attack campaigns and evaluation. Requirements: Framework dependencies, a target adapter, and an appropriate test environment.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### Agentic Security

Source: [https://github.com/msoedov/agentic_security](https://github.com/msoedov/agentic_security)

Capability: LLM endpoint security scanning and prompt fuzzing. Requirements: Framework dependencies, a target adapter, and an appropriate test environment.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### Promptmap

Source: [https://github.com/utkusen/promptmap](https://github.com/utkusen/promptmap)

Capability: Prompt-injection scanning for LLM applications. Requirements: Framework dependencies, a target adapter, and an appropriate test environment.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### LLMFuzzer

Source: [https://github.com/mnns/LLMFuzzer](https://github.com/mnns/LLMFuzzer)

Capability: LLM API fuzzing and extensible test workflows. Requirements: Framework dependencies, a target adapter, and an appropriate test environment.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### PromptInject

Source: [https://github.com/agencyenterprise/PromptInject](https://github.com/agencyenterprise/PromptInject)

Capability: An early modular framework for prompt-injection experiments. Requirements: Framework dependencies, a target adapter, and an appropriate test environment.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### HouYi

Source: [https://github.com/LLMSecurity/HouYi](https://github.com/LLMSecurity/HouYi)

Capability: Black-box prompt injection adapted to application context. Requirements: Framework dependencies, a target adapter, and an appropriate test environment.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### HackAgent

Source: [https://github.com/AISecurityLab/hackagent](https://github.com/AISecurityLab/hackagent)

Capability: SDK and CLI execution of research attacks against AI agents. Requirements: Framework dependencies, a target adapter, and an appropriate test environment.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### OpenRT

Source: [https://github.com/AI45Lab/OpenRT](https://github.com/AI45Lab/OpenRT)

Capability: Multiple attack algorithms for multimodal models. Requirements: Framework dependencies, a target adapter, and an appropriate test environment.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

## algorithm

### WildTeaming

Source: [https://github.com/allenai/wildteaming](https://github.com/allenai/wildteaming)

Capability: Mining real-world tactics, composing tactics, and attack pruning. Requirements: A target/model adapter, and depending on the method, attacker/scorer models or model weights and GPU access.

AEGIS integration: `indexed_tactics_and_composition`. Link: HTTP 200; verified.

### AdvBench / GCG

Source: [https://github.com/llm-attacks/llm-attacks](https://github.com/llm-attacks/llm-attacks)

Capability: Gradient-based adversarial suffix optimization requiring model weights and GPU access. Requirements: A target/model adapter, and depending on the method, attacker/scorer models or model weights and GPU access.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### PAIR

Source: [https://github.com/patrickrchao/JailbreakingLLMs](https://github.com/patrickrchao/JailbreakingLLMs)

Capability: Iterative prompt improvement using an attacker model and target feedback. Requirements: A target/model adapter, and depending on the method, attacker/scorer models or model weights and GPU access.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### TAP

Source: [https://github.com/RICommunity/TAP](https://github.com/RICommunity/TAP)

Capability: Tree-of-attacks search with branching and pruning for black-box tests. Requirements: A target/model adapter, and depending on the method, attacker/scorer models or model weights and GPU access.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### AutoDAN

Source: [https://github.com/SheltonLiu-N/AutoDAN](https://github.com/SheltonLiu-N/AutoDAN)

Capability: Genetic optimization of fluent jailbreak prompts. Requirements: A target/model adapter, and depending on the method, attacker/scorer models or model weights and GPU access.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### AutoDAN-Turbo

Source: [https://github.com/SaFoLab-WISC/AutoDAN-Turbo](https://github.com/SaFoLab-WISC/AutoDAN-Turbo)

Capability: Strategy memory and continual attack-strategy discovery. Requirements: A target/model adapter, and depending on the method, attacker/scorer models or model weights and GPU access.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### BEAST

Source: [https://github.com/vinusankars/BEAST](https://github.com/vinusankars/BEAST)

Capability: Token-level search for adversarial prompt optimization. Requirements: A target/model adapter, and depending on the method, attacker/scorer models or model weights and GPU access.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### GPTFuzzer

Source: [https://github.com/sherdencooper/GPTFuzz](https://github.com/sherdencooper/GPTFuzz)

Capability: Seed mutation, selection, and fuzzing guided by target responses. Requirements: A target/model adapter, and depending on the method, attacker/scorer models or model weights and GPU access.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### ArtPrompt

Source: [https://github.com/uw-nsl/ArtPrompt](https://github.com/uw-nsl/ArtPrompt)

Capability: ASCII-art representations for testing token/semantic interpretation boundaries. Requirements: A target/model adapter, and depending on the method, attacker/scorer models or model weights and GPU access.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### FlipAttack

Source: [https://github.com/yueliu1999/FlipAttack](https://github.com/yueliu1999/FlipAttack)

Capability: Character or word reordering and reconstruction as instruction laundering. Requirements: A target/model adapter, and depending on the method, attacker/scorer models or model weights and GPU access.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### DeepInception

Source: [https://github.com/tmlr-group/DeepInception](https://github.com/tmlr-group/DeepInception)

Capability: Nested fictional environments and simulation layers. Requirements: A target/model adapter, and depending on the method, attacker/scorer models or model weights and GPU access.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### ReNeLLM

Source: [https://github.com/NJUNLP/ReNeLLM](https://github.com/NJUNLP/ReNeLLM)

Capability: Prompt rewriting and scenario nesting for attack generation. Requirements: A target/model adapter, and depending on the method, attacker/scorer models or model weights and GPU access.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### CipherChat

Source: [https://github.com/RobustNLP/CipherChat](https://github.com/RobustNLP/CipherChat)

Capability: Alternative-language or cipher representations for safety testing. Requirements: A target/model adapter, and depending on the method, attacker/scorer models or model weights and GPU access.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### CodeAttack

Source: [https://github.com/renqibing/CodeAttack](https://github.com/renqibing/CodeAttack)

Capability: Embedding instructions in code contexts to test model safeguards. Requirements: A target/model adapter, and depending on the method, attacker/scorer models or model weights and GPU access.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### DrAttack

Source: [https://github.com/xirui-li/DrAttack](https://github.com/xirui-li/DrAttack)

Capability: Prompt decomposition and reconstruction for black-box attacks. Requirements: A target/model adapter, and depending on the method, attacker/scorer models or model weights and GPU access.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### Crescendo

Source: [https://crescendo-the-multiturn-jailbreak.github.io/](https://crescendo-the-multiturn-jailbreak.github.io/)

Capability: Multi-turn escalation from a benign opening toward a conflicting objective. Requirements: A target/model adapter, and depending on the method, attacker/scorer models or model weights and GPU access.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### Many-shot Jailbreaking

Source: [https://www.anthropic.com/research/many-shot-jailbreaking](https://www.anthropic.com/research/many-shot-jailbreaking)

Capability: Behavior steering through many examples in a long context. Requirements: A target/model adapter, and depending on the method, attacker/scorer models or model weights and GPU access.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### Skeleton Key

Source: [https://www.microsoft.com/en-us/security/blog/2024/06/26/mitigating-skeleton-key-a-new-type-of-generative-ai-jailbreak-technique/](https://www.microsoft.com/en-us/security/blog/2024/06/26/mitigating-skeleton-key-a-new-type-of-generative-ai-jailbreak-technique/)

Capability: Instructions that attempt to change how a model applies its safety rules. Requirements: A target/model adapter, and depending on the method, attacker/scorer models or model weights and GPU access.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### Bad Likert Judge

Source: [https://unit42.paloaltonetworks.com/multi-turn-technique-jailbreaks-llms/](https://unit42.paloaltonetworks.com/multi-turn-technique-jailbreaks-llms/)

Capability: Multi-turn attacks using a model's judging role and scoring examples. Requirements: A target/model adapter, and depending on the method, attacker/scorer models or model weights and GPU access.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### Best-of-N Jailbreaking

Source: [https://jplhughes.github.io/bon-jailbreaking/](https://jplhughes.github.io/bon-jailbreaking/)

Capability: Sampling multiple text, audio, or image perturbations. Requirements: A target/model adapter, and depending on the method, attacker/scorer models or model weights and GPU access.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

## dataset

### AgentHarm

Source: [https://huggingface.co/datasets/ai-safety-institute/AgentHarm](https://huggingface.co/datasets/ai-safety-institute/AgentHarm)

Capability: Harmful multi-step agent tasks with benchmark-specific usage terms. Requirements: Dataset license/access terms and adaptation to the registered target.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### InjecAgent

Source: [https://github.com/uiuc-kang-lab/InjecAgent](https://github.com/uiuc-kang-lab/InjecAgent)

Capability: Indirect injection against tool-integrated agents, including disclosure and harmful actions. Requirements: Dataset license/access terms and adaptation to the registered target.

AEGIS integration: `indexed_attack_templates`. Link: HTTP 200; verified.

### BIPIA

Source: [https://github.com/microsoft/BIPIA](https://github.com/microsoft/BIPIA)

Capability: Indirect prompt-injection tasks and attack templates in external data carriers. Requirements: Dataset license/access terms and adaptation to the registered target.

AEGIS integration: `indexed_attack_templates`. Link: HTTP 200; verified.

### TensorTrust Data

Source: [https://github.com/HumanCompatibleAI/tensor-trust-data](https://github.com/HumanCompatibleAI/tensor-trust-data)

Capability: Research data from human-written prompt-injection game attacks. Requirements: Dataset license/access terms and adaptation to the registered target.

AEGIS integration: `indexed_attacker_inputs`. Link: HTTP 200; verified.

### WildJailbreak

Source: [https://huggingface.co/datasets/allenai/wildjailbreak](https://huggingface.co/datasets/allenai/wildjailbreak)

Capability: Benign, adversarial, and direct examples with response pairs; dataset access terms apply. Requirements: Dataset license/access terms and adaptation to the registered target.

AEGIS integration: `gated_unconnected`. Link: HTTP 200; verified.

### JailbreakLLMs

Source: [https://github.com/TrustAIRLab/JailbreakLLMs](https://github.com/TrustAIRLab/JailbreakLLMs)

Capability: Real-world jailbreak prompts and analysis. Requirements: Dataset license/access terms and adaptation to the registered target.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### Jailbreak LLMs Study

Source: [https://github.com/verazuo/jailbreak_llms](https://github.com/verazuo/jailbreak_llms)

Capability: Primary collection and analysis code for in-the-wild jailbreak research. Requirements: Dataset license/access terms and adaptation to the registered target.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### HarmfulQA

Source: [https://github.com/declare-lab/red-instruct](https://github.com/declare-lab/red-instruct)

Capability: The HarmfulQA and Red-Instruct red-team data approach. Requirements: Dataset license/access terms and adaptation to the registered target.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### Do-Not-Answer

Source: [https://github.com/Libr-AI/do-not-answer](https://github.com/Libr-AI/do-not-answer)

Capability: Evaluation requests covering risks that models should not answer. Requirements: Dataset license/access terms and adaptation to the registered target.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### XSTest

Source: [https://github.com/paul-rottger/exaggerated-safety](https://github.com/paul-rottger/exaggerated-safety)

Capability: Tests for excessive refusal of harmless requests. Requirements: Dataset license/access terms and adaptation to the registered target.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### SafetyBench

Source: [https://github.com/thu-coai/SafetyBench](https://github.com/thu-coai/SafetyBench)

Capability: Safety questions across multiple categories. Requirements: Dataset license/access terms and adaptation to the registered target.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### SALAD-Bench

Source: [https://github.com/OpenSafetyLab/SALAD-BENCH](https://github.com/OpenSafetyLab/SALAD-BENCH)

Capability: Safety taxonomy, attack-enhanced examples, and evaluation. Requirements: Dataset license/access terms and adaptation to the registered target.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### ALERT

Source: [https://github.com/Babelscape/ALERT](https://github.com/Babelscape/ALERT)

Capability: Risk categories for red teaming and safety evaluation. Requirements: Dataset license/access terms and adaptation to the registered target.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### BeaverTails

Source: [https://github.com/PKU-Alignment/beavertails](https://github.com/PKU-Alignment/beavertails)

Capability: Safety annotations and categories for model responses. Requirements: Dataset license/access terms and adaptation to the registered target.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### Safe-RLHF

Source: [https://github.com/PKU-Alignment/safe-rlhf](https://github.com/PKU-Alignment/safe-rlhf)

Capability: Safety/helpfulness data and training/evaluation research. Requirements: Dataset license/access terms and adaptation to the registered target.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### Anthropic HH-RLHF

Source: [https://huggingface.co/datasets/Anthropic/hh-rlhf](https://huggingface.co/datasets/Anthropic/hh-rlhf)

Capability: Helpful/harmless preference pairs and red-team attempts. Requirements: Dataset license/access terms and adaptation to the registered target.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### Anthropic Red Teaming

Source: [https://huggingface.co/datasets/Anthropic/hh-rlhf/tree/main/red-team-attempts](https://huggingface.co/datasets/Anthropic/hh-rlhf/tree/main/red-team-attempts)

Capability: Human red-team conversations with privacy and usage considerations. Requirements: Dataset license/access terms and adaptation to the registered target.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### ToxicChat

Source: [https://huggingface.co/datasets/lmsys/toxic-chat](https://huggingface.co/datasets/lmsys/toxic-chat)

Capability: Toxicity and adversarial examples from real user conversations. Requirements: Dataset license/access terms and adaptation to the registered target.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

## evaluation

### Inspect AI

Source: [https://github.com/UKGovernmentBEIS/inspect_ai](https://github.com/UKGovernmentBEIS/inspect_ai)

Capability: Agent evaluation with sandboxes, tool-using solvers, and scorers. Requirements: Task/scorer adapters, target outputs, and benchmark license requirements.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### Inspect Evals

Source: [https://github.com/UKGovernmentBEIS/inspect_evals](https://github.com/UKGovernmentBEIS/inspect_evals)

Capability: Standard benchmark implementations built on Inspect. Requirements: Task/scorer adapters, target outputs, and benchmark license requirements.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### JailbreakEval

Source: [https://github.com/ThuCCSLab/JailbreakEval](https://github.com/ThuCCSLab/JailbreakEval)

Capability: Methods for evaluating jailbreak outcomes. Requirements: Task/scorer adapters, target outputs, and benchmark license requirements.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### JailbreakBench

Source: [https://github.com/JailbreakBench/jailbreakbench](https://github.com/JailbreakBench/jailbreakbench)

Capability: Standard threat models, behaviors, adversarial artifacts, and evaluation. Requirements: Task/scorer adapters, target outputs, and benchmark license requirements.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### HarmBench

Source: [https://github.com/centerforaisafety/HarmBench](https://github.com/centerforaisafety/HarmBench)

Capability: Standard harmful-behavior evaluation and attack baseline implementations. Requirements: Task/scorer adapters, target outputs, and benchmark license requirements.

AEGIS integration: `indexed_template_fragments`. Link: HTTP 200; verified.

### StrongREJECT

Source: [https://github.com/alexandrasouly/strongreject](https://github.com/alexandrasouly/strongreject)

Capability: Evaluation of whether a response meaningfully satisfies an attack objective. Requirements: Task/scorer adapters, target outputs, and benchmark license requirements.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### AgentDojo

Source: [https://github.com/ethz-spylab/agentdojo](https://github.com/ethz-spylab/agentdojo)

Capability: Tool-using agent tasks, adversarial tool-result surfaces, and security/usefulness measurement. Requirements: Task/scorer adapters, target outputs, and benchmark license requirements.

AEGIS integration: `indexed_template_fragments`. Link: HTTP 200; verified.

### CyberSecEval / PurpleLlama

Source: [https://github.com/meta-llama/PurpleLlama](https://github.com/meta-llama/PurpleLlama)

Capability: Prompt-injection, agent, and cybersecurity risk evaluation. Requirements: Task/scorer adapters, target outputs, and benchmark license requirements.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### TrustLLM

Source: [https://github.com/HowieHwong/TrustLLM](https://github.com/HowieHwong/TrustLLM)

Capability: Trustworthiness, safety, privacy, and robustness evaluation. Requirements: Task/scorer adapters, target outputs, and benchmark license requirements.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### DecodingTrust

Source: [https://github.com/AI-secure/DecodingTrust](https://github.com/AI-secure/DecodingTrust)

Capability: Adversarial tests and measurement of model trustworthiness. Requirements: Task/scorer adapters, target outputs, and benchmark license requirements.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### HELM

Source: [https://github.com/stanford-crfm/helm](https://github.com/stanford-crfm/helm)

Capability: Standard model scenarios and measurements for comparison. Requirements: Task/scorer adapters, target outputs, and benchmark license requirements.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### LM Evaluation Harness

Source: [https://github.com/EleutherAI/lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness)

Capability: Reproducible model benchmark infrastructure. Requirements: Task/scorer adapters, target outputs, and benchmark license requirements.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### DeepEval

Source: [https://github.com/confident-ai/deepeval](https://github.com/confident-ai/deepeval)

Capability: LLM tests and scorers; a separate evaluation package from DeepTeam. Requirements: Task/scorer adapters, target outputs, and benchmark license requirements.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### Ragas

Source: [https://github.com/vibrantlabsai/ragas](https://github.com/vibrantlabsai/ragas)

Capability: RAG quality measurement and synthetic test-data generation. Requirements: Task/scorer adapters, target outputs, and benchmark license requirements.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

### AI Verify

Source: [https://github.com/aiverify-foundation/aiverify](https://github.com/aiverify-foundation/aiverify)

Capability: AI testing and reporting infrastructure; a separate project from Moonshot. Requirements: Task/scorer adapters, target outputs, and benchmark license requirements.

AEGIS integration: `not_connected`. Link: HTTP 200; verified.

## defense

### Rebuff

Source: [https://github.com/protectai/rebuff](https://github.com/protectai/rebuff)

Capability: Prompt-injection detection and canary checks; a defense rather than an attack generator. Requirements: A defense or classifier; it is not counted as an attack generator.

AEGIS integration: `reference_only`. Link: HTTP 200; verified.

### NeMo Guardrails

Source: [https://github.com/NVIDIA/NeMo-Guardrails](https://github.com/NVIDIA/NeMo-Guardrails)

Capability: Policies and guardrails for conversation, tool, and output flows. Requirements: A defense or classifier; it is not counted as an attack generator.

AEGIS integration: `reference_only`. Link: HTTP 200; verified.

### Guardrails AI

Source: [https://github.com/guardrails-ai/guardrails](https://github.com/guardrails-ai/guardrails)

Capability: Schema- and validator-based input/output checks. Requirements: A defense or classifier; it is not counted as an attack generator.

AEGIS integration: `reference_only`. Link: HTTP 200; verified.

### LLM Guard

Source: [https://github.com/protectai/llm-guard](https://github.com/protectai/llm-guard)

Capability: Input/output scanning for injection and disclosure risks. Requirements: A defense or classifier; it is not counted as an attack generator.

AEGIS integration: `reference_only`. Link: HTTP 200; verified.

### Llama Guard

Source: [https://huggingface.co/meta-llama/Llama-Guard-3-8B](https://huggingface.co/meta-llama/Llama-Guard-3-8B)

Capability: A safety-classifier model; its weights are not downloaded by this integration. Requirements: A defense or classifier; it is not counted as an attack generator.

AEGIS integration: `reference_only`. Link: HTTP 200; verified.

### Prompt Guard

Source: [https://huggingface.co/meta-llama/Prompt-Guard-86M](https://huggingface.co/meta-llama/Prompt-Guard-86M)

Capability: A prompt-injection/jailbreak classifier; its weights are not downloaded here. Requirements: A defense or classifier; it is not counted as an attack generator.

AEGIS integration: `reference_only`. Link: HTTP 200; verified.

### ShieldGemma

Source: [https://huggingface.co/google/shieldgemma-2b](https://huggingface.co/google/shieldgemma-2b)

Capability: A safety-policy classifier model with separate access terms. Requirements: A defense or classifier; it is not counted as an attack generator.

AEGIS integration: `reference_only`. Link: HTTP 200; verified.

## reference

### TensorTrust Game

Source: [https://github.com/HumanCompatibleAI/tensor-trust](https://github.com/HumanCompatibleAI/tensor-trust)

Capability: Game threat model, attack/defense workflow, and data-generation context. Requirements: Methodology or scope guidance; it is not an executable attack component.

AEGIS integration: `reference_only`. Link: HTTP 200; verified.

### ModelScan

Source: [https://github.com/protectai/modelscan](https://github.com/protectai/modelscan)

Capability: Unsafe serialization scanning for model files; a supply-chain security tool. Requirements: Methodology or scope guidance; it is not an executable attack component.

AEGIS integration: `reference_only`. Link: HTTP 200; verified.

### MITRE ATLAS

Source: [https://atlas.mitre.org/](https://atlas.mitre.org/)

Capability: AI attack tactics, techniques, and case mappings. Requirements: Methodology or scope guidance; it is not an executable attack component.

AEGIS integration: `reference_only`. Link: HTTP 200; verified.

### OWASP GenAI Security Project

Source: [https://genai.owasp.org/](https://genai.owasp.org/)

Capability: LLM and agent security risks and test-scope guidance. Requirements: Methodology or scope guidance; it is not an executable attack component.

AEGIS integration: `reference_only`. Link: HTTP 200; verified.

### OWASP LLM Top 10

Source: [https://genai.owasp.org/llm-top-10/](https://genai.owasp.org/llm-top-10/)

Capability: Application risks including injection, disclosure, and excessive agency. Requirements: Methodology or scope guidance; it is not an executable attack component.

AEGIS integration: `reference_only`. Link: HTTP 200; verified.

### NIST AI RMF

Source: [https://www.nist.gov/itl/ai-risk-management-framework](https://www.nist.gov/itl/ai-risk-management-framework)

Capability: Risk management, measurement, and evaluation guidance. Requirements: Methodology or scope guidance; it is not an executable attack component.

AEGIS integration: `reference_only`. Link: HTTP 200; verified.

### NIST GenAI Profile

Source: [https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence)

Capability: The generative AI risk-management profile. Requirements: Methodology or scope guidance; it is not an executable attack component.

AEGIS integration: `reference_only`. Link: HTTP 200; verified.

### Lakera Gandalf

Source: [https://gandalf.lakera.ai/](https://gandalf.lakera.ai/)

Capability: Interactive prompt-injection exercises; AEGIS does not attack this external service. Requirements: Methodology or scope guidance; it is not an executable attack component.

AEGIS integration: `reference_only`. Link: HTTP 200; verified.

### Microsoft AI Red Team

Source: [https://www.microsoft.com/en-us/research/publication/lessons-from-red-teaming-100-generative-ai-products/](https://www.microsoft.com/en-us/research/publication/lessons-from-red-teaming-100-generative-ai-products/)

Capability: Product red-teaming experience and methodology findings. Requirements: Methodology or scope guidance; it is not an executable attack component.

AEGIS integration: `reference_only`. Link: HTTP 200; verified.

### Anthropic Agent Injection Research

Source: [https://www.anthropic.com/research/prompt-injection-defenses](https://www.anthropic.com/research/prompt-injection-defenses)

Capability: Prompt-injection defenses and evaluation for tool-using systems. Requirements: Methodology or scope guidance; it is not an executable attack component.

AEGIS integration: `reference_only`. Link: HTTP 200; verified.
