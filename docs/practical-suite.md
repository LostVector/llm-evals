# Practical local evaluation suite

The first deployment uses Halogen 0.20.3, revision `54a488ef3224`, with
`qwen38-flash-next-v2.hgn` (identity supplied by the operator). Checkpoint filename
and server revision are recorded separately; the filename is not an artifact hash.

The target is a few days per deployment. Full SuperGPQA is excluded. Pilot runtimes
must establish feasibility before committing to additional full runs. Changes to
a task set or budget produce a distinct protocol, never a silently comparable score.

| Lane | Planned measurement | Scope |
| --- | --- | --- |
| Science reasoning regression | GPQA Diamond, no tools | All 198 questions, one pass for the Flash-Next matrix. [Frozen protocol](../protocols/gpqa-diamond.json) |
| Coding | LiveCodeBench code-generation-lite, pass@1 | 131 tasks from February–April 2025; [frozen protocol](../protocols/livecodebench-v6-window.json) |
| Agentic / multi-turn | BFCL V4 Multi-Turn Base | All 200 base cases. Native function calling with the pinned BFCL scorer, scripted user turns, and the upstream step limit. |

GPQA uses the simple-evals prompt and answer regex, fixed choice shuffling,
xhigh reasoning, and a 32,768-token completion budget. The initial Flash-Next
deployments scored 176–182 out of 198. Retain those runs as science reasoning
regression checks. For future model or quant selection, reuse existing GPQA
references and prioritize [HLE-Diamond](general-capability.md) for general
capability. Run GPQA again when a deployment regression needs investigation.

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

## Terminal-Bench run history

Future runs are on hold until we agree on a cumulative per-task token limit, what counts toward it, and how the harness enforces it. Existing deadline-based scores remain historical deployment results.

Terminal-Bench 2.1 contains 89 tasks in the downloaded official snapshot. Its
standard agent time budgets total about 42.2 hours serially. Pilot latency and sandbox build time determine feasible
concurrency; a full one-attempt run should remain within a few days without
shortening the official task budgets. Generated commands run only in task
containers, and local endpoint credentials remain with the host-side agent.

## Optional τ²-bench Airline comparison

Use the full English text Airline domain and the same simulator, grading settings, inference step limit and reasoning policy for every quant. Leave the per-task wall-clock cutoff unset for scoring. Track latency and transport failures separately. Compare against the Airline leaderboard column for the same task release and simulator protocol. [Upstream runner guide](https://github.com/sierra-research/tau2-bench/blob/main/docs/running-the-benchmark.md) · [Leaderboard](https://taubench.com/leaderboard/)

## Flash-Next GSQ-RCO coverage

Run the same GPQA Diamond, LiveCodeBench window and BFCL Multi-Turn Base protocols for all four [ISTA-DASLab GSQ-RCO variants](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF). Use one Gufo build and matching settings where supported, confirm the loaded artifact after each model switch, and record any runtime differences. Run the Halogen v2 build as a separate reference.

| Deployment | GPQA Diamond | LiveCodeBench | BFCL Base |
| --- | --- | --- | --- |
| Gufo Q2_0 | [176/198](../data/results/gufo-gsq-rco-q2-0-gpqa-diamond-2026-11-18.json) | Pending | [126/200 (63.0%)](analysis/bfcl-gufo-q2-0.json) |
| Gufo IQ2_XS | Pending | Pending | [132/200 (66.0%)](analysis/bfcl-gufo-iq2-xs.json) |
| Gufo IQ3_XXS | Pending | Pending | [134/200 (67.0%)](analysis/bfcl-gufo-iq3-xxs.json) |
| Gufo IQ3_S | 182/198 | 109/131 | [120/200 (60.0%)](analysis/bfcl-gufo-iq3-s.json) |
| Halogen v2 | 180/198 | 103/131 | [127/200 (63.5%)](analysis/bfcl-halogen-v2.json) |

Reuse the [audited Gufo IQ3_S results](analysis/gufo-controlled-suite-summary-2026-11-18.json) and [Halogen v2 results](halogen-v2-publication.md) for the two completed lanes, with their recorded runtime and sampling differences. BFCL uses the pinned bfcl-eval 2026.3.23 dataset and scorer. The local profile requests medium effort and 8,192 output tokens per turn. Gufo sets a 6,963-token reasoning cutoff explicitly. Halogen uses its server policy, and effective cutoff equivalence needs verification. Report the Base score with the tool-call mode and generation settings. HARD-51 remains a separate repository-coding follow-up.

The original Gufo build served IQ3_S. Its loader rejected IQ3_XXS at provider selection and Q2_0 at the Q3_K embedding tensor. Candidate `73c2064f` loaded IQ3_XXS, then hit an unsupported embedding format during the cached native-MTP smoke test. Candidate `085aa5cc` passed the smoke test on IQ3_XXS, IQ2_XS, and Q2_0 and produced their BFCL scores using four 262,144-token slots. The builds matched all five IQ3_S full-model regression responses and decoding work counts, so the matrix carries forward the completed IQ3_S run.

### Published higher-precision references

AMD reports **92.12% GPQA Diamond** and **88.09% LiveCodeBench** for Flash-Next BF16 with the original n-gram table. Its 198-question GPQA set and 131-problem LiveCodeBench v6 date window align with ours. AMD averaged five `xhigh` runs and used a **253,952-token output cap** within a **262,144-token context window**. The local single-turn runs use a **32,768-token output cap**. Both scores are available in the chart's context view. [AMD results and protocol](https://rocm.blogs.amd.com/artificial-intelligence/quark-qwen-ple/README.html#appendix-b-exact-benchmark-results)

AMD's **66.21% BFCL v4** is a weighted no-web-search aggregate. The local BFCL track covers the 200-case Multi-Turn Base split. A published **87/100** LiveCodeBench result for the 8-bit oQ8e MLX build used a stratified 100-problem sample with thinking disabled. [AMD BFCL results](https://rocm.blogs.amd.com/artificial-intelligence/quark-qwen-ple/README.html#qwen-results-with-xhigh-thinking) · [oMLX 8-bit result](https://omlx.ai/benchmarks/intelligence/dc87mf9x)

## SWE-bench Pro V2 HARD-51 follow-up

After the BFCL runs, try Scale's official HARD-51 subset as the repository-level coding evaluation. Pin the V2 release, the 51 task IDs, image digests, and agent configuration. Use the V2 verifier to regrade each captured patch in a pristine environment. [Upstream protocol and task list](https://github.com/scaleapi/SWE-bench_Pro-os/blob/main/v2/README.md#hard-51)

The [three-task timing pilot](analysis/hard51-timing-pilot.md) validated the container grader. The wall-clock budget stopped one of three trials at 50 minutes and all three at 15 minutes. Use the pilot's matched-work profile for a quant comparison, with separate reporting for wall-clock deployment scores.

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

Current version-4.0 frontier references remain a separate external track. Its
66 task budgets total 528 hours and include three GPU tasks; this practical run
therefore uses [the frozen version-2.1 protocol](../protocols/terminal-bench-2.1.json).
Do not combine scores across those versions.

Version 2.0 was used only for calibration. Its xhigh/32768 profile timed out
before acting; medium/8192 acted and attempted a solution but timed out. The
main 2.1 profile was frozen after those latency checks, and runs all 89 tasks
with fresh one-attempt outcomes. Calibration results are not pooled into 2.1.
AA publishes 2.1 results for the same Flash Next family and several frontier
models; those references retain their e2b/three-repeat protocol labels.

## Audit before publishing

Run `python3 scripts/audit_local.py` with the `gpqa`, `coding` or `terminal`
lane and an ignored `--input` run directory. GPQA also requires `--dataset`.
Use `--require-complete` for a final export: partial runs are rejected.
The audit recomputes scores, checks task identity and generation profiles, and
emits aggregates plus artifact hashes, without questions, answers or traces.
Terminal-Bench content checksums must match the pinned 2.1 snapshot. Every task
in this snapshot requests a pytest CTRF report. The audit requires a nonempty,
consistent report and a reward matching the executed tests, and rejects known
verifier emulation crashes. A reward file alone does not prove grading ran.
A normal agent timeout with successfully executed verifier tests counts as a
failed task; setup failures and other unresolved exceptions require review.

The initial local Docker run was invalidated after seven of its first eight
verifiers crashed in `uvx` under x86 QEMU emulation before pytest started. Its
reported zero rewards are not model scores and must not be published. Preserve
those artifacts privately. Validate the replacement execution environment with
an upstream oracle solution and actual test reports before another measured run.
Two native ARM64 source-build oracle preflights subsequently passed: all nine
tests for `bn-fit-modify` and all six for `cancel-async-tasks`. The replacement
89-task cohort uses Harbor's `force_build: true` to build upstream Dockerfiles
natively; the oracle image architecture was checked with Docker.
All measured tasks restart fresh under that environment. Model generation
settings and task budgets stay fixed, and invalid emulated trials are excluded.

One native task, `fix-git`, needed an explicit environment repair: its setup
clones a public repository that now returns 404. The build failed before agent
setup or execution. Its original preconfigured Git working tree, including the
complete `.git` directory, was recovered from the stopped upstream image pinned
in `environment_repairs` in the protocol. No image code was run during extraction.
The native Dockerfile copies this state instead of executing the unavailable
clone, and retains the original setup's dummy Git committer configuration.
Instructions, verifier, solution and task budgets are unchanged. The repaired
environment passed both official oracle tests before one measured attempt.
The protocol retains both task checksums and identifies this deviation; the
source snapshot hash continues to describe the original upstream files.

Two further tasks, `qemu-startup` and `qemu-alpine-ssh`, failed during
Docker builds before agent setup because Debian security package URLs returned
404. Their isolated repairs bootstrap a CA bundle from the pinned coding
sandbox image and use Debian's official HTTPS security archive. Task
instructions, solutions, verifiers and budgets remain unchanged. The startup
oracle passed its test. The SSH oracle initially failed while waiting for guest
networking; a separate diagnostic copy changing only its Expect wait from 30 to
300 seconds passed the unchanged SSH verifier. The measured SSH task retains
the original solution and budget. Both single measured recovery attempts passed
their executed verifier tests; the SSH attempt reached its agent time limit.
The protocol pins the original setup failures, repaired task checksums,
Dockerfile hashes and measured replacement results. Recovery trial directories
can be gathered as symlinks under one private recovery root for the assembler.

Keep original failed and successful trial directories intact. Use
`python3 -m scripts.assemble_terminal --input <private-original-job>
--recovery <private-recovery-job> --output <fresh-private-cohort>` to create a
private selection of symlinks for auditing and export. The assembler permits
only the exact pinned pre-agent failure and exact pinned replacement result;
it rejects duplicate tasks and missing replacements. It never changes trial
contents. Reassemble into a fresh directory as the main job completes, then run
the normal terminal audit with `--require-complete` before publication. The
assembler itself does not establish that a score is valid.

Terminal exports also retain cumulative completed-trial duration, agent execution
duration, and verifier duration from timezone-aware Harbor timestamps. Trial
duration includes setup and grading; its agent and verifier components are not
additional wall time. These sums are not the elapsed time of a concurrent job.

Admission and transient HTTP failures are logged separately. The runners make
up to eight transport attempts with backoff and honor `Retry-After`. Invalid
requests fail immediately; none of these infrastructure failures become model
scores. Request durations include any retry/queue time, so they are shared-service
wall times rather than isolated inference throughput measurements.

After a complete audit, `scripts/export_local.py` writes a validated local
observation. It requires ignored `--metadata` containing only the approved public
model identity (name, revision, quantization, artifact and actual SHA-256), backend
version and hardware description, plus `artifact_verified: true`. An upstream
expected weight hash or a gateway deployment ID does not verify the loaded file.
Unknown metadata fields are not copied. Registered public model labels are
required; private endpoint aliases are rejected.

```sh
python3 scripts/export_local.py gpqa \
  --input .local/gpqa/halogen-v2-run \
  --dataset .local/gpqa/data/gpqa_diamond.csv \
  --metadata .local/halogen/public-metadata.json \
  --id halogen-v2-gpqa-diamond-complete --write
```

The `coding` and `terminal` lanes use their corresponding run directories and do
not need `--dataset`. Export refuses partial or unaudited outcomes and never
replaces an existing observation. Review the generated record before committing;
raw traces, questions, answer text, endpoint configuration and credentials remain
private. The published source link points to the sanitized result and its audit
fingerprints. The artifact hash and hardware remain operator-verified metadata.

## Historical coding context

Five official archived submissions cover exactly the same 131 problems: o3
(High), Claude Sonnet 4 Thinking, DeepSeek R1-0528, Qwen3-235B-A22B and Gemini
2.5 Pro (June 2025). Their snapshot is pinned to submission-repository commit
`6ca212e9c2039373f6e5069d37ffa9db66e23736` from August 1, 2025. Each observation
links the immutable original file and records its Git blob hash and SHA-256.
These are historical references, excluded from the latest reviewed cohort.
Use “All references & history” to view them alongside local coding results.

`python3 scripts/verify_lcb_history.py --archive-dir .local/livecodebench/references --dataset-dir .local/livecodebench/data --download`
recomputes their scores without executing or regenerating model outputs. Cache
files remain in ignored storage; `--download` fetches missing files directly from
the pinned official commit and verifies their hashes before saving them.
The verifier requires all task IDs, question text and starter code to match the
frozen local window, and checks every pass@1 value against its completion grades.
DeepSeek averages ten samples per task; the other four submissions use one.
The source does not establish effective generation budgets, hardware or full/lite
grading mode, so these remain contextual references rather than controlled
comparisons. The source snapshot date is not a claimed inference date.

Reasoning budget and closure handling are explicit run parameters; see [reasoning policy](reasoning-policy.md). Freeze server-side policy before starting a run and use a fresh run identity for changes.
