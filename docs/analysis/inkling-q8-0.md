# Inkling 2 Mini Q8_0 deployment checks

The model is the fixed-loop `Inkling-2-Mini-Q8_0.gguf` at
`db61c5b492a6a034d986328d28274af0a439aa6c`. Its SHA-256 was
`d57542f8aea5d7639beba5fc4ae7f584754916f63ac5d5a69328c27f652f45da`.
The serving profile uses four 262,144-token slots and up to three active
requests per host. [Model artifact](https://huggingface.co/ggml-org/Inkling-2-Mini-GGUF/blob/db61c5b492a6a034d986328d28274af0a439aa6c/Inkling-2-Mini-Q8_0.gguf)

The batched Gufo build with the same-slot checkpoint fix passed the native
function-call round trip on three replicas. A 24-token completion reported
23 reasoning tokens, and a separate request with a four-token reasoning
budget finished thinking at four tokens. Three simultaneous conversations
on each replica reused 2,290–2,314 prompt tokens independently. These requests
tested three concurrent sessions configured at 256K with shorter prompts.
[Preflight](../../scripts/inkling_gufo_preflight.py)

The Q8_0 batching fix reached physical decode width three. The same-slot
checkpoint fix reduced prefill from about 59K tokens to 11 in each of three
synthetic long-prompt replays. All three outputs matched clean prefill.
These runtime measurements describe the serving build separately from
the scores. [Batching evidence](https://github.com/LostVector/gufo/pull/24)
[Cache evidence](https://github.com/gufo-org/gufo/pull/1408)

During the matched HARD-51 run, we sampled completed chat requests with
at least 32,768 prompt tokens through 2026-11-25 22:47 UTC. All 68 requests
in that completed sample reported cache reuse. Median reuse was **99.08%**
of prompt tokens, with a median of **650 tokens** of fresh prefill.
The longest completed prompt reused 131,822 of 132,333 tokens. The
sample ends before later requests finish and describes runtime behavior.

The staged native Gufo build (`ada29e15ad50`) and llama.cpp b12600
agreed on the highest-scoring token for the raw prefixes `[100]`,
`[100, 200]`, and `[100, 200, 300]` using the same Q8_0 checkpoint.
The respective predictions were `68014`, `198`, and `68014`. The largest
absolute difference in the winning token's logit was 0.024.

A second check used Gufo ROCm prefill and llama.cpp b12600
(`29b52d398`) CPU decode on the same Q8_0 checkpoint. Both engines
received the same teacher-forced token IDs. Gufo and llama.cpp agreed
on the highest-logit token at **189 of 192 positions (98.44%)**.
At the three disagreements, the llama.cpp first-to-second logit gaps
were 0.0011, 0.0099, and 0.0048. Both engines ranked the other's
winning token in their top 64 at those positions.

| Synthetic fixture | Top-token agreement | Mean absolute logit difference on Gufo's top 64 | Mean KL divergence |
| --- | ---: | ---: | ---: |
| Prose | 46 / 48 | 0.1073 | 0.002695 |
| Python | 48 / 48 | 0.2488 | 0.001464 |
| Table | 95 / 96 | 0.2996 | 0.001780 |

The KL comparison uses Gufo's top 64 plus a bucket for the remaining
probability mass. llama.cpp CPU microbatches of 32 produced nonfinite logits
in this oracle run. The reported comparison uses one CPU token per decode,
with finite logits checked for every position. This establishes short-context
numerical agreement with three near-tie changes in token rank. The tool-call,
reasoning-budget, and cache tests cover the serving API separately.
[Fixtures and reproduction](inkling-q8-oracle-fixtures.md)
[llama.cpp source](https://github.com/ggml-org/llama.cpp/tree/29b52d398b294509746ec0a3f28948a3107c0213)

| Benchmark | Verified result | Evidence |
| --- | ---: | --- |
| GPQA Diamond | 170 / 198 | [Score record](../../data/results/gufo-inkling-2-mini-q8-0-gpqa-diamond-2026-11-23.json) |
| LiveCodeBench frozen window | 92 / 131 | [Score record](../../data/results/gufo-inkling-2-mini-q8-0-livecodebench-window-2026-11-25.json) |
| BFCL Multi-Turn Base | 112 / 200 | [Score record](../../data/results/gufo-inkling-2-mini-q8-0-bfcl-multi-turn-base-2026-11-25.json) · [Offline replay audit](bfcl-inkling-q8-0.json) |

The GPQA and LiveCodeBench rows record the earlier native Gufo build.
BFCL retained 168 cases on the batched build and ran the final 32 after
the cache update. The two builds and the checkpoint hash are recorded in
the audit. The 12-task HARD-51 score is pending.
