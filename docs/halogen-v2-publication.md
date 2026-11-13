# Halogen v2 evaluation publication

The measured suite is complete and audited. This change tracks the remaining
deployment metadata and publication of sanitized local observations.

Server metadata was supplied in [the PR comment](https://github.com/LostVector/llm-evals/pull/1#issuecomment-6861695568). The current file SHA-256 is `71246c6ab3fc1de2cf06326f18e275fe9c2a18366d646ed3357d194c884fc687`. The server uses an AMD Ryzen AI Max+ 395, one integrated Radeon 8060S, and 128 GiB shared memory. Public artifact source/revision is unknown. The hash and backend were verified after evaluation; continuity throughout the evaluation period remains unverified. All three result records preserve this limitation.

| Evaluation | Fixed scope | Result | Wilson 95% interval |
| --- | --- | --- | --- |
| GPQA Diamond | 198 questions, one attempt | 180/198 (90.91%) | 86.09–94.17% |
| LiveCodeBench | 131 problems, February 1 through April 30, 2025, one attempt | 103/131 (78.63%) | 70.84–84.78% |
| Terminal-Bench 2.1 | All 89 tasks, one measured attempt per valid environment | 52/89 (58.43%) | 48.05–68.11% |

These intervals describe task-sampling uncertainty, not all model variability.
The coding window is a subset of the 175-problem incremental v6 set. It is not
the full 1,055-problem cumulative `release_v6` collection. Published Qwen coding
scores do not yet have a verified matching task set and protocol.

## Server metadata needed

The server session should add a PR comment containing only:

```text
Loaded artifact filename: qwen38-flash-next-v2.hgn
SHA-256 of the actual loaded file: <64 hexadecimal characters>
Artifact source/revision: <public source and revision, if known>
CPU model: <model>
GPU/accelerator model(s) and count: <models and count, or none>
System RAM: <capacity>
GPU/unified memory: <capacity, if applicable>
Backend: Halogen 0.20.3, rev 54a488ef3224
Confirmation: this artifact/backend remained the same throughout the evaluation
```

Compute the file hash on the inference server with
`sha256sum /actual/path/qwen38-flash-next-v2.hgn` (or `shasum -a 256` on macOS).
Share the digest only; omit the absolute path. The gateway's model ID is not
proof of the loaded file's SHA-256. Report unknown source revisions explicitly.

This PR is public. Do not post endpoints, IP addresses, hostnames, usernames,
credentials, private configuration files, gated question content, or raw traces.
Hardware model names and capacities are sufficient; omit serial numbers and
machine identifiers.

## Publication steps

1. Verify server-supplied artifact and hardware metadata against the measured
   deployment; retain private connection details locally.
2. Export all three complete audited runs with `scripts/export_local.py` into
   `data/results/`, including source/protocol links, runtime, uncertainty,
   integrity fingerprints, and the disclosed Terminal-Bench environment repairs.
3. Validate observation schemas and privacy checks, run repository checks, build
   the comparison page, and review the resulting records.
4. Merge the completed results, verify GitHub Actions and the live Pages dataset,
   and confirm each score links to its result and protocol.

The frozen protocols and benchmark setup repairs are already on `main`.
Raw responses, reasoning, questions, verifier logs, and connection configuration
remain in ignored local storage. No extra coding generations or new benchmarks
are part of this publication change.
