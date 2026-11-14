# Initial work plan

## Local model matrix

Select exact checkpoints after confirming available RAM/VRAM, target runtime, and acceptable run time. These are discovery families, not claims about current popularity or speed:

- [Qwen](https://huggingface.co/Qwen): include a general instruction model and a coding-focused checkpoint when available.
- [Mistral](https://huggingface.co/mistralai): include a size that fits the same local hardware budget.
- [DeepSeek](https://huggingface.co/deepseek-ai): consider locally feasible distilled or smaller checkpoints; distinguish distillation from quantization.
- Include locally available Kimi and GLM checkpoints from Moonshot and Z.ai; verify exact artifacts and memory requirements. Track major OpenAI/Anthropic and hosted-only models as frontier references.
- Expand with other widely used local families based on dated download/use evidence and relevant tool-use support. Do not select exclusively on a single leaderboard.

For each selected base checkpoint, aim for a high-precision reference plus approximately 8-, 6-, and 4-bit variants where supported. GGUF labels such as Q8_0, Q6_K, and Q4_K_M are separate artifacts, not interchangeable generic bit widths. AWQ/GPTQ/MLX comparisons require their own artifact and backend metadata. [llama.cpp](https://github.com/ggml-org/llama.cpp) is one possible runtime; no backend is required yet.

Use memory tiers defined by the actual host, measuring total working memory including KV cache and context. Separate same-model quant loss from best quality under a fixed memory/latency budget. A model that cannot complete the workload remains a reported failure.

## Next milestones

1. Inventory hardware and choose runtime; select a small exact checkpoint matrix and license-compatible artifacts.
2. Use the [suite selection and pilot policy](benchmarks.md): HLE-Diamond as primary general capability; SuperGPQA/BBEH as supporting tests; LiveCodeBench, Terminal-Bench, τ-bench text, and MultiChallenge. Use the pinned HLE runner and verify dataset/model/judge access before inference. Start with text-only general/coding pilots and IFBench/BFCL diagnostics, then the interactive pilots. Verify current score spread before fixing the reporting suite.
3. Pin runner revisions, dataset/task manifests, prompts, budgets and evaluators. Add reviewed output adapters and preserve task-level outcomes for paired model/quant comparisons.
4. Budget interactive simulator/judge calls explicitly; no paid endpoint use is enabled by this plan. Freeze simulator and judge recipes, and isolate version-incompatible historical references.
5. Capture source-backed frontier observations with matching benchmark versions and original provenance. Reassess broad coverage, ceilings, floors and task quality before expanding into long-context or repository patching tracks.
6. Add charts for success versus memory, latency, and energy once real observations exist.

## Future goal: harness effects on local agentic performance

After the current quant comparison finishes, measure how much changing the agent
harness improves the same open-weight deployment on Terminal-Bench 2.1.
Use Terminus-2 as the existing baseline and mini-SWE-agent as the first candidate;
better performance is a hypothesis, not an assumed outcome.

- Freeze the exact model artifact, quant, backend, KV cache precision, sampling,
  task environments, and total reasoning/output and wall-clock budgets. Pin both
  harness revisions and document any interface differences.
- Select a fixed 15–20-task pilot before examining candidate outcomes, spanning
  coding, configuration, debugging, and data tasks. Include baseline successes
  and failures; do not select only tasks Terminus-2 missed.
- Run the harnesses separately with the same concurrency and comparable server
  load, avoiding contention that favors either arm. Verify sandbox execution
  before running generated commands.
- Report paired task outcomes, wins and regressions, completion time, token use,
  formatting/tool errors, loops, and timeouts. A pilot remains explicitly partial;
  use its runtime and uncertainty to decide whether to run all 89 tasks.
- If the pilot supports a useful improvement within the practical runtime budget,
  perform the full comparison. Keep fixed-harness quant comparisons separate from
  fixed-model harness comparisons in the data and charts.

This is planned future work, not an additional run authorized or started by
recording the plan. No paid endpoint usage is enabled by this milestone.
