# GitHub and GitHub Pages

## Publish

With GitHub CLI signed in, run from the repository root:

```sh
./scripts/publish_github.sh
```

The helper validates data, tests and builds the page, requires a clean working tree, creates a **public** `llm-evals` repository under the signed-in account, pushes `main`, enables GitHub Pages with Actions, and dispatches the first deployment. An optional first argument selects an organization you can administer. Existing unrelated or private repositories are not modified. The helper must have network access and GitHub permissions to create repositories, push workflow files, and configure Pages.

The page URL is returned by GitHub. Wait for the `Sync references and publish Pages` workflow to complete before treating it as live. Its `github-pages` environment also shows the deployed URL. If the initial push races Pages enablement, the explicit dispatch publishes afterward. If dispatch fails because the workflow is not yet registered, retry `gh workflow run pages.yml --ref main -F sync=false` after it appears in Actions.

## Data flow

```text
Official public Markdown tables ── daily/manual sync ── data/frontier/*.json
Reviewed source-backed scores ── manual updates ─────── data/references/*.json
Our measured runs ── validated observations ─────────── data/results/*.json
                                      ↓
                          scripts/build_site.py
                                      ↓
                static HTML + CSS + JS + downloadable JSON
                                      ↓
                             GitHub Pages
```

The browser makes no calls to third-party benchmark services. The build embeds the same public observations supplied in `data.json`; it also opens directly from `dist/index.html` for an offline preview. Source files and private run artifacts are not copied wholesale into the deployment.

### Automatic refresh

`python3 scripts/sync_frontier.py` refreshes the **BBEH and SuperGPQA** official Markdown tables. The daily workflow runs at 08:23 UTC (GitHub schedules can be delayed). It commits changed snapshots and publishes in the same workflow: pushes made with `GITHUB_TOKEN` do not trigger a second push workflow. Runs can also be dispatched manually with the `sync` checkbox.

Adapters require recognized column names, numeric ranges and a minimum row count. Both responses are parsed and validated before any snapshot is written. Network/format failure fails the workflow and leaves the existing deployed page intact. Unchanged scores do not create a new snapshot or imply a newly performed evaluation. Source response checksums are recorded in provenance. Source changes that preserve the parsed scores do not create a new snapshot.

These upstream tables are **historical coverage**, not a maintained list of today's leading models. All upstream model rows are retained: an open or older model is not relabeled a current frontier model. Check upstream data/code licenses and attribution requirements before expanding redistribution; the initial snapshots contain selected attributed score facts, not task data or source prose.

### Reviewed snapshots

`data/references/curated-2026-11-11.json` contains manually verified selected score rows for SuperGPQA, BBEH, Terminal-Bench 2.1, τ² text and MultiChallenge. Some source version/recipe details are unavailable and explicitly marked as such. The initial sync has not been verified against live upstream responses from this machine: outbound DNS/network access was unavailable. Offline parser fixtures and failure preservation are tested. The first GitHub sync must pass before automatic refresh is considered operational.

Terminal-Bench, τ-bench and MultiChallenge currently use reviewed snapshots. **LiveCodeBench numeric ingestion remains pending.** Do not add fragile universal HTML scraping or silently substitute another benchmark/window to fill a missing chart. Add and test a source-specific adapter when a stable, permitted source interface has been verified.

Keep all score/version tracks distinct. `observed_at` for published observations records when the source was observed, not when evaluation ran. The UI groups by the full benchmark descriptor, exact metric, unit and direction, then displays the latest observed model/quant/harness record. That grouping is an inventory aid, not proof of equivalent protocols. Histories remain in JSON/Git. Local fraction and published percent metrics stay separate tracks unless deliberately standardized in reviewed source records.

## Local checks

```sh
python3 -m unittest discover -s tests -v
python3 evals.py validate
python3 scripts/build_site.py
node --check site/app.js
```

Open `dist/index.html` in a browser. To serve it when socket access is available, use `python3 -m http.server 8765 --directory dist`.

The publish build validates every local and external observation and checks for common leaks (home paths, email addresses, private endpoints, obvious credential fields/tokens). It is a partial guard, not a complete secret scanner. Review data and commit metadata before publishing. Git ignores do not redact tracked files. Git author name is public; the configured contributor email is a placeholder.

## Current-model coverage

The default page now uses an explicitly reviewed cohort from `data/reference_policy.json`. `data/model_registry.json` maps exact source labels to model families/providers without merging dated checkpoints or reasoning settings. All six requested provider groups have verified AA Intelligence Index v5.0.1 observations. Additional coding, knowledge, workflow, and multi-turn observations use their own source/version tracks; not every model is evaluated on every track.

The new reviewed snapshot contains Sol 6.1/Astra, Fable 5.2/5.1, Opus 5.5, DeepSeek V4.1 Flash 1017, Qwen3.8 Max (0902)/Flash-Next, Kimi K3.1 Pro, GLM-5.3/Flash, and other source-backed labels. Exact settings and source caveats remain attached to each observation. Historical records are retained under “All references & history”. Scores missing from a source remain absent, and the coverage table makes that visible. The common AA index uses points, not percentages. AA-Omniscience net scores can be negative and are plotted with a signed axis.

**Automatic sync still covers only the historical BBEH/SuperGPQA tables.** It does not update this current cohort. The page displays the separate review date and flags a review overdue after 30 days. Update the dated current snapshot and featured IDs after source review; do not advance the review date simply because a build or historical sync ran.

For a more sustainable current-model feed, [Artificial Analysis documents an authenticated data API](https://artificialanalysis.ai/data-api/docs/reference). Its free endpoint requires a valid API key and exposes headline indices, while per-benchmark scores require a higher tier. No API key is configured or committed here, and public-page extraction has not been presented as a reliable automatic feed.

## Primary general metric

The chart now defaults to HLE-Diamond full-set no-tool accuracy, using its reviewed AA reference track first. [The local execution guide](general-capability.md) documents the pinned public dataset/evaluator and runner. AA Intelligence Index remains a separate external composite. Do not execute the gated dataset or model/judge inference in the Pages workflow; it publishes only reviewed aggregate observations. Raw dataset-derived artifacts stay under ignored `.local/`.
