# Comparing the Terminal-Bench deployments

Both deployments completed the same frozen 89-task Terminal-Bench 2.1 set with Harbor/Terminus-2, medium effort, an 8,192-token per-turn request cap, the same task resources and environment repairs, and unchanged task deadlines. These are deadline-limited deployment results. They do not isolate quantization or model ability from inference speed, queueing, backend behavior, and reasoning handling.

The GSQ-RCO loaded-file hashes and KV-cache precision are still awaiting server verification. The measurements below are audited task/verifier outcomes attributed to the reported serving deployment, not a fully verified local chart observation. Original failures and predetermined infrastructure replacements remain preserved.

| Measurement | Halogen v2 | GSQ-RCO IQ3_S |
| --- | ---: | ---: |
| Tasks solved | 52/89 (58.43%) | 35/89 (39.33%) |
| Agent timeouts | 27 | 52 |
| Median recorded agent turns, on the same 24 tasks where both timed out | 13 | 4 |
| Median recorded terminal command calls, on those same 24 tasks | 22 | 8.5 |
| Median reported completion tokens, on those same 24 tasks | 26,954.5 | 6,660.5 |

Halogen solved 24 tasks that GSQ-RCO did not; GSQ-RCO solved seven that Halogen did not. Of the 24 Halogen-only solves, 22 ended in a GSQ-RCO agent timeout. This supports unequal work completed before the deadline as an important factor. It does not establish that speed alone caused the score gap.

A timeout is not automatically a failed verifier outcome: three of Halogen's timed-out trials still passed their task verifiers. The measured rewards, not exception labels alone, determine the score.

## What the saved timing can establish

The [aggregate audit](analysis/terminal-bench-deployment-comparison-2026-11-15.json) contains no prompts, commands, terminal output, reasoning, endpoint details, or private paths. It summarizes the selected audited cohorts and records hashes of their source-result fingerprint inventories.

Harbor stores completed request durations in `agent_result.metadata.api_request_times_msec`. These include network, queueing, prefill and decoding, rather than measuring GPU decode alone. On the 24 common timeout tasks, reported completion tokens divided by recorded completed API seconds were approximately 39.24 tokens/s for Halogen and 8.41 tokens/s for GSQ-RCO. These are descriptive end-to-end rates for recorded returned calls, not controlled engine throughput benchmarks.

There are important telemetry gaps:

- Terminus-2 appends request duration after a successful chat return. Failed calls and the final in-flight request at timeout are not fully counted.
- LiteLLM raises on an output-length finish before returning the response to Chat. Those exceptions do not reliably contribute to Chat's reported token totals. Logged length exceptions are not complete usage accounting.
- Normal trajectory step timestamps are written after command execution. Differences between adjacent timestamps combine model and tool work.
- Residual agent time therefore includes omitted API waits as well as tools and harness overhead. An exact split of pure model time versus tool time cannot be reconstructed from these artifacts.

Recorded successful turns and command calls are useful measures of interaction opportunity. Reported token totals are incomplete compute accounting and should not be used as an exact normalized budget.

## Which comparison to use

Keep the current frozen deadlines when comparing deployment effectiveness. A slower deployment producing fewer useful turns before timeout is part of that result. Shared-service contention and the concurrency schedule must remain disclosed. The common per-turn output cap also does not prove identical thinking/answer allocation; the numeric GPQA/coding reasoning-budget fix does not establish per-turn Terminal-Bench closure equivalence.

For a future model-focused diagnostic, preselect a task subset and match the harness, task environments, sampling, total generated-token budget (including reasoning across all turns), tool-call budget, and reasoning closure policy. Run without competing evaluation traffic and allow enough wall-clock headroom that decoding speed is not the primary limit. Report that token-budgeted diagnostic separately from the frozen-deadline score.

## Prepared timeout rerun cohort

The [22-task candidate manifest](analysis/terminal-timeout-rerun-candidates-2026-11-15.json) contains every task Halogen solved whose selected GSQ-RCO trial failed with an agent timeout. It freezes task checksums, source-result fingerprints, original deadlines and resources. The runtime choice is pending: a faster compatible engine with the original deadlines, or the current engine under a separately labeled extended-time profile.

This failure-selected cohort measures recovery on those cases; it does not estimate full-suite accuracy. Rerun outcomes will be reported separately from the original 89-task result. Execution will use at most four inference slots while respecting unchanged task resources and Docker capacity.
