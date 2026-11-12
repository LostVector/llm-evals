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
| Coding | LiveCodeBench code-generation-lite, pass@1 | Pin an official dataset revision and a leaderboard date window before generation; record the exact task IDs and count |
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
server behavior. Generation is sequential to avoid mixing concurrency effects
into the first baseline.
