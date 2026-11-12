# Practical local evaluation suite

The first deployment uses Halogen 0.20.3, revision `54a488ef3224`, with
`qwen38-flash-next-v2.hgn` (identity supplied by the operator). Checkpoint filename
and server revision are recorded separately; the filename is not an artifact hash.

The target is a few days per deployment. Full SuperGPQA is excluded. Pilot runtimes
must establish feasibility before committing to additional full runs. Changes to
a task set or budget produce a distinct protocol, never a silently comparable score.

| Lane | Planned measurement | Scope |
| --- | --- | --- |
| Reasoning | GPQA Diamond, no tools | All 198 questions, one pass; [frozen protocol](../protocols/gpqa-diamond.json) |
| Coding | LiveCodeBench code-generation-lite, pass@1 | 131 tasks from February–April 2025; [frozen protocol](../protocols/livecodebench-v6-window.json) |
| Agentic / multi-turn | Terminal-Bench with Terminus-2 | Pin dataset and harness versions; pilot first, then retain standard task budgets if feasible |

GPQA uses the simple-evals prompt and answer regex, deterministic choice shuffling,
explicit sampling, xhigh reasoning, and a 32,768-token completion budget. This is
one pass rather than the upstream default four repeats. Report a confidence
interval and avoid interpreting small quant differences as established rankings.
GPQA measures graduate science reasoning and knowledge, not all general intelligence.
It supplements the harder HLE-Diamond reference view.

LiveCodeBench generation and scoring are separate. Code must execute in isolated,
resource-limited containers without host credentials or broad host mounts. Terminal
agents receive only their benchmark sandbox. Neither lane should run while the
container runtime is being updated. A pilot or partial run must be labeled partial;
it must not be published as a completed full benchmark.

External frontier scores contextualize each lane but are not controlled comparisons
unless task set, version, agent, tools, reasoning settings and budgets match. Link
the original score source and retain discrepancies in the comparison page.

Private API configuration, route names, task text and raw model traces stay under
ignored local storage. Only sanitized protocols, aggregate statistics and safe task
identifiers may be published. No endpoint or credentials belong in a public protocol.

## Reproduce GPQA Diamond

After accepting the dataset terms and logging in to Hugging Face, download
`gpqa_diamond.csv` from the revision in the protocol into `.local/gpqa/data/`.
Create an ignored JSON configuration with `base_url` (including `/v1`), `model`
(the fixed route), and `deployment` (server version, revision and checkpoint).
Optional fields are `api_key` and `bypass_proxy` (for a direct LAN connection).
Keep this file private.

```sh
python3 scripts/gpqa_diamond.py \
  --config .local/gpqa/config.json \
  --dataset .local/gpqa/data/gpqa_diamond.csv \
  --output .local/gpqa/reproduction
```

Use `--limit 20` for a timing pilot. Re-run with the same output directory and no
limit to resume the full 198 questions. The runner refuses to resume if the
protocol, model/deployment metadata, dataset bytes or task manifest differ.
Infrastructure errors stop the process without creating a task score; rerunning
resumes at that task. The summary records a Wilson 95% interval, truncations,
parse failures, forced reasoning closures and cumulative request time. The
interval does not cover all variability from sampling, contamination or changing
server behavior. The first GPQA pass uses one worker, sharing the endpoint with coding and
agentic pilots. The operator reports four slots, a 512k shared context pool and a
256k per-request window. Record concurrent activity with runtime measurements;
these are shared-service timings rather than isolated throughput results.

The coding window uses the v6 increment and an inclusive February 1 / exclusive
May 1, 2025 date filter, yielding 131 tasks. It retains all difficulties (31 easy,
39 medium, 61 hard), with one completion per task. Official Generic/OpenAIChat
prompts, last fenced code extraction and the unmodified upstream test grader are
pinned by the harness commit. A five-task prefix is only a runtime/harness pilot.

Terminal-Bench 2.0 contains 89 tasks in the downloaded official snapshot. Their
standard agent time budgets total about 41.3 hours serially (the longest is
12,000 seconds). Pilot latency and sandbox build time determine feasible
concurrency; a full one-attempt run should remain within a few days without
shortening the official task budgets. Generated commands run only in task
containers, and local endpoint credentials remain with the host-side agent.

## Reproduce the coding window

Download the dataset at the revision in `protocols/livecodebench-v6-window.json`
to `.local/livecodebench/data/`, and check out its stated harness revision into
`.local/livecodebench/upstream/`. The runner checks the upstream commit, exact
selected task IDs and a hash of selected question/test content before inference.
It never sends tests or reference answers to the model.

Prepare the scorer build context from that checkout and this repository:

```sh
mkdir -p .local/livecodebench/scorer
cp -R .local/livecodebench/upstream/lcb_runner .local/livecodebench/scorer/
cp scripts/lcb_scorer/Dockerfile scripts/lcb_scorer/score.py .local/livecodebench/scorer/
docker build -t llm-evals-lcb:local .local/livecodebench/scorer
python3 scripts/livecodebench.py \
  --config .local/gpqa/config.json \
  --dataset-dir .local/livecodebench/data \
  --upstream .local/livecodebench/upstream \
  --output .local/livecodebench/reproduction --limit 5
```

Omit `--limit 5` to resume through all 131 tasks. Use the same private config
fields as GPQA. The scorer image has only pinned NumPy/tqdm plus the upstream
harness; it runs unprivileged, offline, read-only, with CPU, memory and PID limits.
Private test decompression/unpickling occurs only inside that container. An outer
900-second infrastructure deadline is distinct from the official six-second
per-test timeout. Infrastructure errors stop the run rather than becoming wrong
answers. The runner records its scorer image ID and refuses a manifest change
when resuming. Raw responses, extracted programs and grader details stay private.
