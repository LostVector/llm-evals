# GSQ-RCO IQ3_S evaluation

This suite uses the existing 198-question GPQA Diamond, 131-problem February–April 2025 LiveCodeBench window, and 89-task Terminal-Bench 2.1 protocols. All three evaluations and their result/lineage audits are complete. Actual loaded GGUF shard hashes and KV-cache precision still await server verification; formal chart observations have not been exported. The [public-safe aggregate report](analysis/gsq-rco-suite-summary-2026-11-15.json) preserves scores, uncertainty, response lineage, infrastructure recovery counts and audit fingerprints.

## Audited results

| Evaluation | GSQ-RCO IQ3_S | Halogen v2 reference | Difference |
| --- | ---: | ---: | ---: |
| GPQA Diamond, 198 questions | 170/198 (85.86%) | 180/198 (90.91%) | -5.05 percentage points |
| LiveCodeBench, 131 fixed problems | 108/131 (82.44%) | 103/131 (78.63%) | +3.82 percentage points |
| Terminal-Bench 2.1, 89 tasks | 35/89 (39.33%) | 52/89 (58.43%) | -19.10 percentage points |

GPQA has zero truncated or unparsed final answers. Coding has one of each: reasoning finished, but final content then exhausted the total cap before a closing code fence. It remains a failed task under the frozen extractor. There were 52 Terminal-Bench agent timeouts; all verifier outcomes were checked against executed test reports.

These are deployment comparisons. The current GPQA/coding cohorts retain short responses from the original policy, as disclosed below. Terminal-Bench's fixed deadlines expose engine speed and shared-service contention as well as task-solving behavior; see the [trace audit](terminal-bench-comparability.md).

The 95% Wilson intervals are 80.32–90.03% for GPQA, 75.03–88.01% for coding, and 29.82–49.71% for Terminal-Bench. They describe task-sampling uncertainty rather than all run variability.

## Reasoning-policy continuation

The original GPQA/coding requests used a 32,768-token total output cap. Some responses exhausted that cap while reasoning and returned no usable final content. The corrected requests explicitly send llama.cpp `reasoning_budget_tokens: 27853` through the gateway. A 64-token diagnostic verified forwarding and final-answer generation; a previously capped GPQA question subsequently returned final content and a normal stop. The numeric threshold matches the observed Halogen GPQA/coding `answer_room` closure position. Exact injected closing-message equivalence remains unverified.

The frozen, outcome-independent continuation set is:

| Lane | Original short responses retained | Original responses regenerated | Previously unfinished questions |
| --- | ---: | ---: | ---: |
| GPQA Diamond | 105 | 25 | 68 |
| LiveCodeBench | 85 | 46 | 0 |

Every original response with a length finish reason, unknown output usage, or at least 27,853 total output tokens is selected for regeneration, irrespective of correctness. Total output is used conservatively because backend reasoning-token accounting can differ. All other response bytes and coding score checkpoints are retained unchanged. Original artifacts remain private and intact.

This is a **partial-regeneration result**, not a fresh full run under a uniform policy. Reused short responses have not been regenerated to prove counterfactual identity. Report both the selection counts and discarded-original request time. Scored-request timing excludes interrupted requests, diagnostics, and discarded generations unless separately itemized.

The serving build observed at resume is llama.cpp `b12370-b79696f1f`, with four slots and a 262,144-token context per slot. The observed model template SHA-256 is `12827f24b742ea4e80cdc12dbcf9622227056b9f797252a3149263d4f9aaadce`. The server's observed default `min_p` is approximately 0.05; neither the frozen requests nor advertised gateway route overrides it. Halogen v0.20.3 [documents a disabled min-p filter by default](https://github.com/peonist-ai/halogen-flash-server/blob/v0.20.3/docs/FLAGS.md), but its actual evaluation-period environment override was not captured. This is a likely sampling mismatch; the current run preserves its existing setting rather than mixing a new filter into selected responses. Model artifacts, KV precision, and runtime continuity need server-side verification before publication.

## Terminal-Bench recovery

Five original tasks ended in transport/rate-limit exceptions; two had already performed agent actions. One further task was interrupted before agent execution during the scheduler handoff. These six predetermined tasks receive fresh recovery trials with their original task resources, wall-clock limits, and agent generation settings. No successful or model-timeout outcome is retried for a higher score. A later user-requested pause interrupted one recovery; its trace is preserved and its replacement is disclosed separately.

Terminal-Bench is not assigned the new GPQA/coding thinking budget: its original 8,192-token per-turn cap and medium effort remain in effect. Its recorded original/recovery profile must remain separate from a future experiment using Halogen-like per-turn answer room.

## Completion and publication checks

- Audit the exact task sets, final-content scoring, grader outputs, and Terminal-Bench verifier execution.
- Audit every original response fingerprint, retained response bytes, regeneration selection, and the new request-budget manifest.
- Preserve every excluded transport failure and user-interrupted recovery; do not select among valid outcomes.
- Verify actual loaded GGUF shard hashes, source revision, hardware, KV precision, and continuity before exporting public observations.
- Export only aggregate results, public model metadata, policy disclosures, and integrity hashes. Questions, reasoning, endpoints, machine identifiers, and credentials remain private.

`scripts/export_local.py --recovery-plan <private-plan> --original-input <private-original>` performs the additional lineage audit before exporting GPQA or coding. See [reasoning policy](reasoning-policy.md) for the metadata fields.

The existing-trace analysis of deadlines, recorded agent turns, and timing limitations is documented in [Terminal-Bench comparability](terminal-bench-comparability.md).
