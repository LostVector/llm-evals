# Benchmark plan

Sources reviewed 2026-11-11. Pin the exact upstream revision and task IDs before running; benchmark names and leaderboard defaults change.

| Priority | Benchmark | What it measures | Comparison caveat |
| --- | --- | --- | --- |
| 1 | [BFCL](https://gorilla.cs.berkeley.edu/leaderboard) | Tool selection, arguments, multi-turn tool use | Record version, category, native FC vs prompting, parser, and score aggregation. Overall and category accuracy differ. |
| 2 | [τ²-bench](https://github.com/sierra-research/tau2-bench) | Stateful tool-agent-user interaction | Pin domain, simulator model/configuration, policy, seed, retries, and pass metric. Simulator differences affect results. |
| 3 | [Terminal-Bench](https://www.tbench.ai/) | Agent work in terminal environments | Pin suite version, agent, container images, timeouts, and resource limits. A harness leaderboard is not a bare-model ranking. |
| 4 | [SWE-bench](https://www.swebench.com/) | Repository-level issue resolution | Pin split and agent. Start with a fixed development subset; do not label it a full leaderboard score. Track contamination and task validity concerns. |
| Supporting | [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) | General capability and quantization regression checks | Supporting evidence only; few-shot QA is not an agentic evaluation. |

Start with a small, fixed tool-use slice to catch chat-template, parser, and quant regressions cheaply. Then run repeated multi-turn tasks before investing in container-heavy coding evaluations. Keep development tasks separate from held-out reporting tasks. Document selection bias for every subset.

[Artificial Analysis](https://artificialanalysis.ai/methodology) supplies broader model, endpoint, and pricing context. Its composite indexes are separate metrics, not substitutes for these agentic benchmarks. Prefer original benchmark leaderboards, then independent measurements, then clearly labeled vendor claims. Record the actual score location and retrieval date, not just a homepage.
