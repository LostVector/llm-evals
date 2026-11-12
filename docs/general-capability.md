# Primary general-capability evaluation: HLE-Diamond

**Decision:** use **HLE-Diamond full-set no-tool pass@1 accuracy (%)** as our headline general-capability metric. Report its reasoning and knowledge partitions alongside the overall score. Artificial Analysis's composite index is external context, not our locally measured metric.

## Why this resolves the gap

The [CAIS/Scale dataset](https://huggingface.co/datasets/cais/hle-diamond) releases all 1,000 Diamond questions: 500 reasoning and 500 knowledge. The [public evaluator](https://github.com/centerforaisafety/hle) provides the generation and grading prompts. Dataset files require accepting a Hugging Face access gate; this is access-controlled public evaluation data, not a private AA test set.

There are current published scores for major model families across our required provider groups. [Artificial Analysis's HLE-Diamond methodology](https://artificialanalysis.ai/evaluations/hle-diamond) evaluates the same named full 1,000-question release without tools and describes its judge and modality treatment. [CAIS/Scale's release results](https://lastexam.ai/blog/hle-diamond) provide another independent protocol track. Our existing reviewed references preserve the source/setting differences rather than combining them. Current strong-model scores remain materially below perfect accuracy; local discrimination still requires pilot evidence.

This is a broad expert knowledge/reasoning measure, not a complete measure of intelligence or agency. Coding remains covered separately by LiveCodeBench/Terminal-Bench, and sustained interaction by τ-bench/MultiChallenge. SuperGPQA and BBEH remain supporting diagnostics to distinguish weaker local models if HLE-Diamond approaches their floor. Do not claim small quantization differences from an underpowered HLE sample.

## Frozen protocol

[Machine-readable recipe](../protocols/hle-diamond.json):

- Dataset: `cais/hle-diamond`, test split, revision `04eeb7efa7e3e4f83a00cbd5ce436a38fd5dda23`.
- Evaluator/prompt source: `centerforaisafety/hle`, revision `22ed3074b1e7b134bcbc09028d0ba320839b0655`.
- Exactly one generated answer per question; no browsing, shell, calculator, retrieval, or other tools.
- Our local default is temperature 0, 16,384 completion tokens, one request at a time. Preserve seed, reasoning mode, chat template, backend, model revision, quant and KV precision. These defaults are our recipe; they are not a claim to reproduce each frontier source's model-specific output budget.
- Read official generation/judge prompt constants from the pinned evaluator as data. The adapter does not execute upstream client initialization.
- Pick one fixed, explicitly versioned judge for a comparison series. AA reports GPT-5.6 Luna at medium reasoning effort, using the official judge prompt/format. Judge choice, reasoning setting, endpoint semantics, and generation settings must match to claim recipe equivalence. A different local judge is a separate grading protocol, not an AA reproduction.
- Generation errors stay in the denominator and receive zero task success; failed/missing judgments block scoring until resolved. Report truncation separately. Correctness is judged from the final answer against the reference answer, not from string equality alone.
- Report overall and partition accuracy, task count, failures, and Wilson 95% intervals. Retain task-level results privately for paired uncertainty analysis; a single model's interval does not establish a significant paired quant difference.

### Input modes

| Mode | Tasks | Use |
| --- | --- | --- |
| `multimodal` | All 1,000 | Models receive the 272 image-bearing questions with their images. |
| `text-input-full` | All 1,000 | Text-only models receive the text of every task, with no images; the denominator stays 1,000. This follows AA's stated treatment of models without image input, but is not modality parity with vision-capable frontier runs. |
| `text-only-subset` | 728 | Diagnostic restricted to tasks without images. Never overlay on full-set frontier accuracy or call it the full benchmark. A comparable frontier subset score requires its own task-level evaluation. |

`--limit` creates a development/smoke subset and is labeled as such. It never produces a full-set headline score. Original `cais/hle` (2,500 tasks), HLE-Rolling, and Diamond are separate datasets.

## Run locally

Use a Python 3.11 or 3.12 environment; the core tracking/site tooling does not need these optional dependencies. Run from the repository root:

```sh
python3.11 -m venv .local/hle-venv
.local/hle-venv/bin/python -m pip install -r requirements-hle.txt
.local/hle-venv/bin/python scripts/hle_diamond.py prepare
```

Accept the conditions at the [dataset page](https://huggingface.co/datasets/cais/hle-diamond) yourself, then supply authorized Hugging Face access through your normal environment/login. Do not put credentials in files tracked by this repository. The gate shares account information with the dataset publisher; the runner does not accept it for you.

Serve a selected model on an OpenAI-compatible endpoint. Use its actual endpoint model ID; `LOCAL_MODEL_ID` below is a shell variable you set, not an existing model configured by this repository. A smoke run:

```sh
.local/hle-venv/bin/python scripts/hle_diamond.py predict \
  --model "$LOCAL_MODEL_ID" \
  --base-url http://localhost:8080/v1 \
  --input-mode text-input-full \
  --limit 5 \
  --output .local/hle/smoke
```

For a headline run, omit `--limit` and use a new output directory. For vision-capable models, set `--input-mode multimodal`. Use `--token-parameter max_completion_tokens` if required by the endpoint. Explicit optional flags include `--max-tokens`, `--temperature`, `--seed`, and `--reasoning-effort`. Configure authentication with `HLE_MODEL_API_KEY` if the endpoint needs it; keys are not recorded in run manifests.

Grade through an explicitly chosen judge endpoint. `JUDGE_MODEL_ID` and `JUDGE_BASE_URL` are values you select; a hosted judge may charge for these calls. `HLE_JUDGE_API_KEY` supplies authentication if required. The endpoint must support the official structured judge response schema.

```sh
.local/hle-venv/bin/python scripts/hle_diamond.py judge \
  --run .local/hle/smoke \
  --model "$JUDGE_MODEL_ID" \
  --base-url "$JUDGE_BASE_URL" \
  --reasoning-effort medium

.local/hle-venv/bin/python scripts/hle_diamond.py report \
  --run .local/hle/smoke
```

The runner preserves a frozen task-ID manifest, partitions, protocol/config fingerprints, predictions, and judgments. It checkpoints each generated answer, requires a new directory for new generation runs, and rejects incomplete prediction sets at scoring time. Interrupted generation is an incomplete run, not a subset headline; keep it recorded separately. Rerunning `judge` retries only missing/failed judgments with the same judge recipe, without regenerating model answers.

Keep model/artifact hashes, runtime versions, hardware specifications, chat-template hash and KV precision with the run. Use the existing local observation template to publish reviewed aggregate results; the runner's summary does not bypass the repository's provenance/identity requirements. Benchmark questions, images, gold answers, and raw response/judge artifacts remain in ignored `.local/` and must not be deployed or redistributed. Never run this benchmark in Pages or a pull-request CI job.

## Verification and remaining setup

The public dataset's revision and access gate were checked through Hugging Face metadata. The evaluator commit was fetched and its prompt constants extracted successfully. Offline tests verify modality/subset selection, omission of gold from candidate requests, fixed one-attempt behavior, failure denominators, judge validation, and private artifact paths. **No real model evaluation or paid judge calls have run.** End-to-end execution still needs dataset access, optional dependencies, a served model, and the selected judge endpoint. The runner is our pinned adapter, not a claim of certification by the benchmark authors or exact reproduction of AA's implementation.
