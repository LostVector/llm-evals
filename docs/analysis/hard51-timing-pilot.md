# HARD-51 timing pilot

The three tasks cover Ansible mount source discovery, OpenLibrary alternate-script author names, and qutebrowser successful process retention. The reference patches resolved all three tasks and empty patches resolved zero in the pinned Linux amd64 images. The official Ansible tests fail to collect on the empty patch because the module under test is missing from the base checkout. The reference patch passed all 48 Ansible tests.

The reference deployment was Qwen3.8-Flash-Next served by Halogen v2, engine 0.20.3. Harbor 0.25.0 ran two trials concurrently. The emulated installer exited with code 139, so mini-SWE-agent 2.4.6 and LiteLLM 1.109.1 ran on the host. The agent used Scale's native bash tool-call prompt and requested high reasoning effort. Repository commands ran offline inside the task containers. Each captured patch was graded with Scale's verifier in a fresh container. The 50- and 15-minute profiles reserved the last minute for patch capture. [Scale's protocol at the pinned revision](https://github.com/scaleapi/SWE-bench_Pro-os/blob/66f92766bba642462d4bbe5479e83f91f9211862/v2/README.md#hard-51) · [mini-SWE-agent release](https://pypi.org/project/mini-swe-agent/2.4.6/)

| Budget | Task | Agent exit | Agent time | Model calls | Reported completion tokens | Resolved |
| --- | --- | --- | ---: | ---: | ---: | --- |
| 50 min | Ansible | Deadline | 49:01 | 67 | 116,040 | No |
| 50 min | OpenLibrary | Submitted | 26:52 | 71 | 51,435 | Yes |
| 50 min | qutebrowser | Submitted | 28:42 | 54 | 42,117 | No |
| 15 min | Ansible | Deadline | 14:00 | 17 | 29,682 | No |
| 15 min | OpenLibrary | Deadline | 13:59 | 31 | 29,204 | Yes |
| 15 min | qutebrowser | Deadline | 14:00 | 27 | 43,437 | Yes |

The 50-minute profile resolved one of three tasks. The 15-minute profile resolved two of three from patches captured when the deadline stopped the agent. Each task had one trial per profile. The qutebrowser score changed alongside a different agent trajectory, so the pilot establishes deadline sensitivity without estimating the effect of shortening the budget on pass rate. Completion tokens include reasoning when reported. The final interrupted call in each timed-out trial returned no usage.

## Matched-work calibration

Halogen v2 and Gufo IQ3_S each ran the three pilot tasks once at two concurrent trials per deployment. The [matched-work protocol](../../protocols/hard51-matched-work.json) capped each task at 128 calls or 150,000 completion tokens, with a 16,384-token per-call cap and a six-hour wall-clock guard. Both endpoints reported reasoning inside completion usage. Each captured patch was regraded in a fresh container with the pinned verifier.

| Deployment | Task | Stop | Agent time | Model calls | Completion tokens | Resolved |
| --- | --- | --- | ---: | ---: | ---: | --- |
| Halogen v2 | Ansible | Submitted | 53:13 | 75 | 101,213 | No |
| Halogen v2 | OpenLibrary | Submitted | 27:14 | 77 | 52,023 | Yes |
| Halogen v2 | qutebrowser | Submitted | 32:06 | 60 | 45,569 | Yes |
| Gufo IQ3_S | Ansible | Token budget | 88:24 | 27 | 150,000 | Yes |
| Gufo IQ3_S | OpenLibrary | Submitted empty patch | 41:43 | 73 | 62,296 | No |
| Gufo IQ3_S | qutebrowser | Submitted | 69:30 | 103 | 61,594 | No |

Gufo's Ansible trial had six length-limited responses and reached the cumulative budget exactly. The captured patch passed. Every other trial submitted before reaching either work limit. The six-hour guard did not bind, and every trial produced an auditable verifier outcome. Halogen resolved two tasks and Gufo resolved one. These calibration results cover three tasks without repeated trials. They establish that the token limit can terminate a long run and still preserve a passing patch for grading.

<details>
<summary>Pinned task images and configuration</summary>

The upstream HARD-51 list has SHA-256 `6e35e84708a26443e1746ae928940555a3188654c90f3a2eb691f4f699482bd1`. The `mini_toolcall.yaml` configuration has SHA-256 `7275afa9920a6fb1b9ec66ab74cee44121db9b0276bb9fa90f5ec0597e523a45`.

| Task ID | Linux amd64 image SHA-256 |
| --- | --- |
| `instance_ansible__ansible-40ade1f84b8bb10a63576b0ac320c13f57c87d34-v6382ea168a93d80a64aab1fbd8c4f02dc5ada5bf` | `74ef826866ce57312db8311f14ec0c2ce2d03570028b5951653607f0ed72fb79` |
| `instance_internetarchive__openlibrary-0dc5b20fa186f9714f8a838178597e69f549d026-v2d9a6c849c60ed19fd0858ce9e40b7cc8e097e59` | `e577f3213ab319585b714b4a534141576bcd4d2991a93bcbd862ae464e81804a` |
| `instance_qutebrowser__qutebrowser-c09e1439f145c66ee3af574386e277dd2388d094-v2ef375ac784985212b1805e1d0431dc8f1b3c171` | `f2d98fc1a5c7fdb7a90fb16001e8b79a5a9ff86b0290bbcfbfd9c274b40c6ddb` |

</details>
