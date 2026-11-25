# Evaluation suite selection

Decision updated 2026-11-25. The suite reports separate coding, multi-turn tool-use, repository-work, and science-regression scores. The general-capability pilot will establish runtime and headroom before the full cohort runs.

## Comparison suite

Freeze the task IDs, prompt, grader, and work budget before running a comparison. Keep published scores visible with their original source and protocol. A hosted baseline on the same profile can fill a gap where no matching published score exists.

| Capability | Fixed track | Published anchors and headroom |
| --- | --- | --- |
| General capability pilot | **HLE Diamond**, no tools, official prompt and one fixed judge. Use a fixed pilot cohort and the same image treatment across candidates. | Frontier references cover all 1,000 questions. Local pilot results apply to the pilot cohort. [Scores](https://artificialanalysis.ai/evaluations/hle-diamond) · [Method](https://artificialanalysis.ai/methodology/intelligence-benchmarking#hle-diamond) · [Local recipe](general-capability.md) |
| Coding | **LiveCodeBench release_v6**, the frozen 131 problems from February through April 2025, one completion per problem, upstream tests. | AMD's Flash-Next BF16 scores **88.09%** on the matching date window with five repeats and a larger output budget. Gufo IQ3_S scored **83.21%** with the local recipe. Published GLM and DeepSeek scores use different or undisclosed task sets. [AMD results](https://rocm.blogs.amd.com/artificial-intelligence/quark-qwen-ple/README.html#appendix-b-exact-benchmark-results) · [Local recipe](../protocols/livecodebench-v6-window.json) |
| Multi-turn tool use | **BFCL Multi-Turn Base**, all 200 cases, native function calling, scripted user turns, and the pinned upstream step limit. | Match category, scorer revision, tool-call mode, and reasoning limits before treating an external result as directly comparable. [Local recipe](practical-suite.md#flash-next-gsq-rco-coverage) · [Leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html) |
| Repository work | **HARD-51 maintenance**, the frozen 12 tasks with the matched-work token and turn budgets. | Record the actual result for patches produced at a work limit. The published 50-minute leaderboard provides deployment context. [Cohort](../protocols/hard51-maintenance-12.json) · [Matched limits](../protocols/hard51-matched-work.json) |
| Science regression | **GPQA Diamond**, one pass over the same 198 questions with the pinned settings. | Flash-Next results cluster near the ceiling in this cohort. Keep GPQA for comparisons with the previous runs. [Local recipe](../protocols/gpqa-diamond.json) |

Use the HLE pilot to measure runtime, confirm grading, and check that the local lineup scores above the floor. Retain τ³-Banking as a separate reference track with its published simulator and judge settings. [Banking methodology](https://artificialanalysis.ai/methodology/intelligence-benchmarking#tau3-banking)

## General-capability pilot

If the pilot supports a full run, use **HLE Diamond full-set no-tool pass@1 accuracy (%)**, with separate reasoning and knowledge accuracy. The 1,000-question release is available through a Hugging Face access gate. The [pinned protocol and local runner](general-capability.md) specify data and evaluator revisions, input mode, judge, failure handling, and commands. Artificial Analysis's composite remains external context.

Do not treat task subsets, missing images, different judges or different token/reasoning budgets as identical protocols. Use the 728-question text-only slice only as a separately labeled diagnostic. Retain SuperGPQA/BBEH for local model and quant discrimination if Diamond is too hard for a target tier; their historical source tables are not the current frontier baseline.

## Supporting and historical benchmarks

| Area | Benchmark and proposed track | Why include it | Local cost and scoring |
| --- | --- | --- | --- |
| Supporting broad knowledge and reasoning | [SuperGPQA](https://github.com/SuperGPQA/SuperGPQA), all disciplines | Graduate-level questions across 285 disciplines; much broader than a science-only or math-only test. Original results show substantial model separation below ceiling. | Many independent text generations; deterministic answer scoring. Start with a fixed discipline-stratified pilot, then expand. Report sample accuracy and discipline macro accuracy separately. |
| Supporting general reasoning | [BIG-Bench Extra Hard (BBEH)](https://github.com/google-deepmind/bbeh), Mini pilot then full | Diverse reasoning beyond code/math. Explicitly designed to replace saturated BBH tasks; includes an official 460-example Mini and 4,520-example full set. | No interactive environment or paid judge required. Use upstream evaluator; preserve per-task results and official aggregate, including distinction between harmonic and micro averages. Watch for floors in small models. |
| Agentic coding and computer work | [Terminal-Bench](https://www.tbench.ai/), future runs on hold pending an agreed cumulative per-task token limit | Multi-step terminal work tests planning, tool use, debugging, and recovery. Complements isolated programming questions. | High: containers, tools, long trajectories. Report task resolution, wall time, tokens, cost and failure categories with one fixed agent. Freeze suite, images and resource/step budgets. |
| Optional simulator check | [τ²-bench Airline](https://github.com/sierra-research/tau2-bench), full 50-task English text domain | Stateful interaction, policy adherence, and tool use with a simulated user. | Interactive runs plus simulator and judge inference. Fix the simulator, judge and step limit across candidates. |
| Multi-turn conversation | [MultiChallenge](https://labs.scale.com/leaderboard/multichallenge), revised dataset | Tests instruction retention, inference memory, coherent responses and iterative editing. Covers a gap that coding agents and tool-call tests do not. | Moderate generation cost plus rubric judging. Pin dataset revision, conversation rollout protocol, rubric, judge/version and answer extraction. Report each of the four axes separately. |

## Evidence and uncertainty

- **SuperGPQA:** the [authors' original results](https://github.com/SuperGPQA/SuperGPQA) span reasoning/chat/base models and difficulty strata; the reported DeepSeek-R1 overall sample accuracy is 61.82%. That is historical evidence of headroom, not a claim about the November 2026 frontier. Large task coverage permits substantially more statistical power than a tiny exam set, at increased generation cost.
- **BBEH:** the [official leaderboard](https://github.com/google-deepmind/bbeh/blob/main/leaderboard.md) shows original-paper BBEH Mini micro accuracy of 11.5% for Llama 3.1 8B Instruct, 15.4% for Distill R1 Qwen 32B, and 56.7% for o3-mini high. This supports its candidacy while warning that small models may approach the floor. These are historical rows; do not present them as current frontier leaders or compare their aggregates interchangeably.
- **LiveCodeBench:** [upstream](https://github.com/LiveCodeBench/LiveCodeBench) supports time-based evaluation, but older windows can become exposed or too easy. Release freshness, grading correctness and actual score spread must be audited at the chosen commit. Published leaderboard coverage may lag current models.
- **Terminal-Bench:** the [site](https://www.tbench.ai/) currently presents 4.1, while published references may use 2.x or 4.0. The browser-readable page did not expose numeric model rows during this review. Headroom for the chosen release remains a pilot question; never merge these versions.
- **τ-bench:** [v2.0.0 release notes](https://github.com/sierra-research/tau2-bench/releases/tag/v2.0.0) explicitly say 2.0 scores are not comparable with 1.x. Use a pinned current text track for new experiments; keep v1.0.1 as a separate historical comparison track if needed. Newer protocol is not evidence of remaining headroom by itself.
- **MultiChallenge:** the [March 2026 revision](https://labs.scale.com/blog/multichallenge-update) changed the judge and refined roughly 54 tasks. Use the revised data and judge recipe; older scores are separate observations. [Open data](https://huggingface.co/datasets/ScaleAI/MultiChallenge) are available. Judge reliability and current ceiling need pilot checks.

## Diagnostics and extension

| Status | Evaluation | Purpose and limits |
| --- | --- | --- |
| Diagnostic | [IFBench](https://github.com/allenai/IFBench), OOD constraint test and optional two-turn variant | Verifiable instruction following without an LLM judge. Useful for quant regressions and checking whether models obey constraints. It is narrower than general reasoning and its two-turn variant does not replace sustained dialogue. Match prompt-level loose/strict scoring explicitly. |
| Diagnostic | [BFCL](https://gorilla.cs.berkeley.edu/leaderboard), multi-turn and agentic categories | Catch native-tool/parser/template failures and distinguish tool execution from answer reasoning. Avoid allowing easy single-call categories to dominate the headline score. Check each category's ceiling independently. |
| Extension | [LongBench v2](https://github.com/THUDM/LongBench) | Long-context understanding, including dialogue history and repository understanding; useful when comparing context/KV quantization. Report fixed, tokenizer-aware context tiers and OOMs; long-context QA is not interactive agency. |

## Exclusions from headline comparisons

HumanEval, MBPP, GSM8K, original MMLU, BBH, and MT-Bench are legacy compatibility/smoke-test candidates only. Do not spend the main evaluation budget on them. This is a portfolio choice, not a claim that every local model saturates every one: BBEH's authors describe BBH saturation, and MultiChallenge's authors describe MT-Bench saturation in frontier models. Smaller models may still benefit from easier development checks.

Keep GPQA Diamond as a science reasoning regression check. The initial Flash-Next deployments clustered at 176–182 correct out of 198, so future runs should prioritize HLE-Diamond for broader general-capability comparisons. Keep published GPQA Diamond and MMLU-Pro scores as attributed references.

HLE-Diamond is now the primary general track. Original HLE and ARC-AGI remain separate possible stretch/reference tracks, subject to data access, tool/modality protocol and cost. Hardness alone does not establish local discriminatory value; avoid spending the core budget on a floor-dominated test. Private evaluations and composites such as the [Artificial Analysis Intelligence Index](https://artificialanalysis.ai/methodology/intelligence-benchmarking) provide frontier context, but cannot substitute for reproducible local runs. Preserve index versions and do not assume all components are public or locally runnable.

[SWE-bench Verified](https://www.swebench.com/) remains a historical reference. [OpenAI's audit of SWE-Bench Pro](https://openai.com/index/separating-signal-from-noise-coding-evaluations/) raises task-validity concerns about the audited version. τ²-bench Airline remains an optional simulator check. Future Terminal-Bench runs are on hold pending agreement on the cumulative token cap, accounting and enforcement. The HARD-51 timing pilot covers repository-level patching separately.

## Pilot acceptance and refresh policy

These are project heuristics, not statistical guarantees:

1. Pick at least three representative local checkpoints spanning capability/memory tiers, including a high-precision baseline and a lower-bit variant of the same checkpoint. Add a pinned frontier reference run only if separately budgeted; otherwise retain published scores as contextual observations.
2. Freeze a stratified development task manifest before viewing candidate outputs. Start HLE-Diamond with a 5-task plumbing smoke test, then a preselected stratified development pilot before the full 1,000-task headline run. Suggested supporting budgets: 500 SuperGPQA questions across broad fields; official BBEH Mini; roughly 150 dated LiveCodeBench tasks spanning difficulty; the full 50-task Airline domain after a plumbing pilot; and 80–100 MultiChallenge conversations spanning all four axes. These are custom development subsets unless they match an official split exactly. They are not sufficient to resolve tiny quantization deltas.
3. Flag a ceiling if all stronger target-local models exceed roughly 90% and there are few informative failures. Flag a floor if candidates cluster at chance or near-zero task success. Inspect category results: aggregate headroom can hide saturated or impossible subtests. Thresholds depend on task/scoring structure; never compare raw accuracy to zero when chance is nonzero.
4. Examine paired task-level differences, uncertainty and run-to-run variance. Bootstrap over tasks/conversations, with task clustering for repeated trajectories. For stochastic agents, start with at least three repetitions on the pilot tasks and increase repeats/sample size if noise masks relevant effects. One-point differences on a 100-task test are not convincing evidence of quant quality loss.
5. Retain a benchmark for model discrimination when it separates relevant candidates beyond measurement noise. Retain it for quant comparisons only when paired differences can be measured at useful precision. A model-ranking benchmark need not detect a small quantization effect. A nondetectable delta is inconclusive, not proof of equivalence.
6. Freeze a reporting suite after the pilot; do not remove tasks based on which candidate failed. Document invalid-task exclusions before scoring held-out reports. Publish task IDs, failures and caveats subject to upstream terms. Never pool development subsets with full official scores.
7. Review at each major model-generation change or quarterly. Add a fresh version/window when the old one loses signal, while preserving old observations and a stable overlap set for trend continuity.

## Frontier reference coverage requirement

Track major model families from OpenAI, Anthropic, DeepSeek, Alibaba/Qwen, Moonshot/Kimi and Z.ai/GLM. Maintain exact source-name mappings in the model registry, include distinct dated checkpoints/reasoning settings, and expose missing results per track. Do not equate a hosted model with an available local artifact. Current frontier reference coverage is a separate selection criterion from local-run practicality: historical BBEH/SuperGPQA rows alone do not satisfy it.

The current published-reference layer includes AA Intelligence Index v5.0.1 across all six provider groups, Terminal-Bench 4.0 under AA's protocol, HLE-Diamond with separate AA/Scale tracks, workflow and knowledge metrics, and current MultiChallenge rows. The AA composite includes private components and supplements rather than replaces our local suite. Source observation/review dates must not be used as model evaluation dates. Benchmark choices should be revisited if current comparable coverage disappears.
