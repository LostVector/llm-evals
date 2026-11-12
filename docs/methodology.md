# Recording and comparing observations

## Required record fields

Both templates contain `schema_version`, `id`, `kind` (`local` or `external`), `observed_at` (ISO date), `model`, `benchmark`, `metric`, `protocol`, `provenance`, and `notes`. Unknown top-level fields are rejected to catch typos. Optional measurements belong under `measurements`.

- `model`: exact `name`, immutable `revision`, `quantization`, and `artifact`. For local runs include `artifact_sha256` (64 hex characters). Record the quantizer/version, calibration corpus, mixed precision, and KV-cache precision in notes or protocol. For external observations use `not_reported` for unavailable revision or quant details; never guess.
- `benchmark`: `name`, immutable `revision`, `split`, and `task_set` (task ID manifest hash or stable published dataset identifier).
- `metric`: `name`, numeric `value`, `unit` (`fraction`, `percent`, `seconds`, `tokens_per_second`, `index`, or `usd`), `direction` (`higher`/`lower`), and positive `n` (number of evaluated tasks; external only may use null if unreported). Preserve the source scale; pass@1 and pass^k are different metric names. Failures/timeouts remain in the denominator.
- `protocol`: exact `harness`, `harness_revision`, `config`, `backend`, `backend_revision`, and `hardware`. `config` identifies an immutable config artifact or contains a full configuration object. Include prompts and chat-template hashes, tool schema/parser, decoding settings and seeds, thinking mode, context limit, output/step/time/retry budgets, concurrency, judge/simulator, environment images, and task selection. External fields may say `not_reported`.
- `provenance`: `type` (`measured`, `benchmark_official`, `independent`, or `vendor_reported`), `location` (original log/artifact path or exact score URL), `retrieved_at` (ISO date), and `notes` (source row, table, screenshot/snapshot checksum, qualifications). External locations must be HTTP(S) URLs.
- `notes`: free text; include limitations and failed tasks. Literal TODO placeholders are rejected throughout a record.
- `measurements` (optional object): task pass counts, repetition counts, confidence intervals and method, latency percentiles, prompt/decode throughput, wall time, peak RAM/VRAM, power/energy, and cost. Use explicit units in keys. Distinguish unavailable from zero. No aggregate is calculated automatically.

One record contains one primary metric. Related records may share an artifact reference; give each a distinct ID. Preserve source responses and task-level outcomes in referenced artifacts. Do not copy a score into a different benchmark split or scale.

## Comparability

A model change and a quant change are separate experiments. To isolate quantization effects, hold base revision, harness, task IDs, prompt/template, budgets, decoding, hardware, backend, context length, and KV precision fixed. Compare each quant to the same model's high-precision baseline when feasible. Cross-backend runs are end-to-end system comparisons. Capture actual loaded artifact hashes and runtime overrides, not just requested settings.

Repeat stochastic runs on the same task set with recorded seeds. Prefer paired task-level differences and confidence intervals. Small differences on small samples are not reliable rankings. Report pass@1 separately from pass^k/retry success and never pool them. Record OOMs, invalid tool calls, truncation, and timeouts separately as well as in task success.

The generated report is an inventory, not a statistical leaderboard. It links each record so protocol and caveats remain reviewable. There is no automatic assertion of comparability and no cross-benchmark average. External scores remain in a separate table even if names match: check the original protocols before drawing conclusions. Model aliases from hosted APIs may change; preserve the reported name and date.

## External ingestion

1. Find the exact benchmark/version, source row, model name, score scale, and harness.
2. Save a permitted snapshot or raw response outside Git, recording its checksum/location in provenance notes. Follow source terms; no scraper is enabled here.
3. Fill an external template; explicitly mark unavailable metadata `not_reported` (or null for task count).
4. Validate and review against the source. Add a new dated observation for updates rather than silently replacing history.

Do not check credentials, proprietary task data, or unredacted sensitive traces into Git. Published benchmark limitations and contamination concerns belong with the result, not hidden behind a single score.
