# llm-evals

Track how well local LLMs and their quantization variants perform, especially as agents. Keep published frontier-model results nearby as attributed reference points.

The unit of evaluation is **model artifact + inference configuration + agent harness + task set + budget**. A quant label alone is insufficient to reproduce a result. Published scores are reference observations, not automatically comparable measurements.

## Start here

Python 3.11+; no third-party dependencies.

```sh
python3 evals.py validate
python3 evals.py template local > data/results/my-run.json
# Fill every TODO using the run configuration and original evaluation output.
python3 evals.py validate
python3 evals.py report > reports.md
python3 -m unittest discover -s tests -v
```

For a published score, use `python3 evals.py template external`. Unfilled templates intentionally fail validation. Results are one JSON file per observation, with globally unique IDs. The report sorts by benchmark and model, never invents a combined ranking, and separates local runs from external references. No scores have been seeded or benchmarks run.

Our primary general-capability metric is **HLE-Diamond full-set accuracy at pass@1 without tools**, with reasoning/knowledge breakdowns. [Run it locally](docs/general-capability.md). **SuperGPQA + BBEH** provide supporting diagnostics, alongside **LiveCodeBench + Terminal-Bench** (coding and terminal agents), and **τ-bench + MultiChallenge** (interactive tools and conversation). [Selection rationale and pilot gates](docs/benchmarks.md) explain how we will check ceilings, floors, uncertainty, and local run cost before freezing the suite.

## Repository

| Path | Purpose |
| --- | --- |
| `data/results/` | Validated observations, including provenance and protocol |
| `data/sources.json` | Curated online reference catalog |
| `templates/` | Local and external observation templates |
| `docs/benchmarks.md` | Agentic benchmark priorities and caveats |
| `docs/methodology.md` | Reproducibility and comparison rules; field reference |
| `docs/roadmap.md` | Initial model/quant matrix and next implementation steps |
| `evals.py` | Offline validation and Markdown reporting |

This starts as a tracking repository. Benchmark runners and broader source adapters are future work. A static comparison page and two public-table adapters are included. Source links identify original evidence; the Pages workflow can refresh two public reference tables. Store large logs and task traces outside Git and reference immutable artifacts; never commit model weights or credentials.

## Public repository hygiene

All tracked content and commit metadata are public. Use relative paths and generic machine labels; record hardware specifications without usernames, hostnames, serial numbers, or device IDs. Result provenance must point to shareable artifacts. Redact credentials, private endpoints, account/project identifiers, personal data, and private task content from configurations, notes, logs, and traces before adding them. The report preserves supplied metadata, so review observations before committing. Validation checks structure, not the absence of secrets.

Keep private run configuration and raw output in the ignored `.local/`, `raw-results/`, or `logs/` directories. Ignore rules do not protect files already tracked. Review `git diff --cached` and commit author metadata before publishing; use a public identity or a hosting-provider noreply address for contributions.

## Comparison page and GitHub Pages

Run `python3 scripts/build_site.py`, then open `dist/index.html`. The page includes benchmark/metric/model filters, score bars, protocol details, source links, and a full JSON download. It includes 117 stored observations and a reviewed current cohort covering major OpenAI, Anthropic, DeepSeek, Alibaba/Qwen, Moonshot/Kimi, and Z.ai/GLM families. Provider filters and a model-coverage table show missing scores explicitly. Historical tables are available in a separate view; LiveCodeBench numeric import is pending. There are no local measurements yet.

[Publishing and sync instructions](docs/publishing.md) cover the public GitHub repo, Pages deployment, daily BBEH/SuperGPQA refresh, snapshot history, and data-review requirements. After GitHub login, `./scripts/publish_github.sh` creates the public repo and enables Pages.

The default reference view is controlled by `data/reference_policy.json`, with exact source labels mapped in `data/model_registry.json`. Current references supplement the locally runnable benchmark plan: external composites and private benchmarks do not become local evaluation requirements. A review-date warning prevents a new site build or historical-table fetch from implying a fresh frontier-model evaluation.

The comparison page defaults to HLE-Diamond. The complete released task set and evaluator are pinned in `protocols/hle-diamond.json`; `scripts/hle_diamond.py` supports an explicit local model endpoint and a separately selected judge. Dataset files require Hugging Face access, and raw evaluation artifacts remain private under `.local/`. AA's composite index is supplementary external context, not a score this repository claims to reproduce.
