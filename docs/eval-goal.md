# Compare local models and quantizations under matched evals

Build a public scorecard that shows how much capability changes across
popular local models and quantizations. Use published frontier results to
anchor each benchmark where the task set, grading, and run settings support
the comparison.

1. Finish Inkling 2 Mini Q8_0. Verify native Gufo against llama.cpp on the
   same checkpoint, document tool calls, reasoning-token accounting,
   batching, and prompt-cache reuse, and publish GPQA Diamond, the frozen
   LiveCodeBench window, BFCL Multi-Turn Base, and the matched 12-task
   HARD-51 maintenance cohort. Preserve completed Flash-Next results.
2. Use LiveCodeBench for coding, BFCL Multi-Turn Base for multi-turn tool
   use, and matched HARD-51 for repository work. Pilot HLE Diamond for
   broad capability and keep GPQA Diamond for regression checks. Promote
   benchmarks that distinguish the local lineup and finish in a practical
   amount of time.
3. Compare Flash-Next GSQ-RCO quants, Inkling 2 Mini Q8_0, Qwen 27B, and
   Qwen 35B-A3B. Record the exact checkpoint, engine, harness, reasoning and
   output limits, context, and concurrency for each run. Use token and
   turn budgets for agentic comparisons and wall-clock guards to stop
   stalls. Report throughput and cache behavior separately.
4. Publish revisioned results to GitHub and GitHub Pages. Link every score
   to its evidence, label pilots and incomplete runs, explain protocol
   differences, and keep private infrastructure details and raw traces local.

The goal is complete when the public table shows the matched local results
and identifies which frontier references are directly comparable.
