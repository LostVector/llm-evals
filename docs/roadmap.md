# Initial work plan

## Local model matrix

Select exact checkpoints after confirming available RAM/VRAM, target runtime, and acceptable run time. These are discovery families, not claims about current popularity or speed:

- [Qwen](https://huggingface.co/Qwen): include a general instruction model and a coding-focused checkpoint when available.
- [Mistral](https://huggingface.co/mistralai): include a size that fits the same local hardware budget.
- [DeepSeek](https://huggingface.co/deepseek-ai): consider locally feasible distilled or smaller checkpoints; distinguish distillation from quantization.
- Expand with other widely used local families based on dated download/use evidence and relevant tool-use support. Do not select exclusively on a single leaderboard.

For each selected base checkpoint, aim for a high-precision reference plus approximately 8-, 6-, and 4-bit variants where supported. GGUF labels such as Q8_0, Q6_K, and Q4_K_M are separate artifacts, not interchangeable generic bit widths. AWQ/GPTQ/MLX comparisons require their own artifact and backend metadata. [llama.cpp](https://github.com/ggml-org/llama.cpp) is one possible runtime; no backend is required yet.

Use memory tiers defined by the actual host, measuring total working memory including KV cache and context. Separate same-model quant loss from best quality under a fixed memory/latency budget. A model that cannot complete the workload remains a reported failure.

## Next milestones

1. Inventory hardware and choose runtime; select a small exact checkpoint matrix and license-compatible artifacts.
2. Pin a BFCL slice and runner; persist config, task manifest, original output, and artifact hashes. Run a high-precision baseline and one quant before expanding.
3. Add a reviewed adapter that converts runner output into the existing observation format. Add task-level analysis for paired comparisons.
4. Add a multi-turn τ²-bench protocol with a fixed simulator, then terminal/coding suites as resources allow.
5. Manually capture a few source-backed frontier baselines on matching benchmark versions. Automate ingestion only after stable data access and terms are confirmed.
6. Add charts for success versus memory, latency, and energy once real observations exist.

No hardware assumptions, downloaded weights, remote repository, or paid API usage are part of the initial setup.
