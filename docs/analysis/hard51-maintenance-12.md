# HARD-51 maintenance cohort

Each of the five deployments ran the same [12 tasks](../../protocols/hard51-maintenance-12.json) under the [matched-work protocol](../../protocols/hard51-matched-work.json). We graded each captured patch in a fresh pinned image. Every trial finished within the six-hour wall guard.

| Deployment | Resolved | Generated tokens | Model calls | Token-limit stops | Call-limit stops |
| --- | ---: | ---: | ---: | ---: | ---: |
| Halogen v2 | [10/12](../../data/results/halogen-v2-hard51-maintenance-12-2026-11-20.json) | 692,609 | 869 | 0 | 0 |
| Gufo IQ3_S | [10/12](../../data/results/gufo-gsq-rco-iq3-s-hard51-maintenance-12-2026-11-21.json) | 799,855 | 858 | 1 | 0 |
| Gufo IQ3_XXS | [7/12](../../data/results/gufo-gsq-rco-iq3-xxs-hard51-maintenance-12-2026-11-21.json) | 832,660 | 834 | 1 | 1 |
| Gufo IQ2_XS | [7/12](../../data/results/gufo-gsq-rco-iq2-xs-hard51-maintenance-12-2026-11-21.json) | 868,525 | 764 | 0 | 0 |
| Gufo Q2_0 | [10/12](../../data/results/gufo-gsq-rco-q2-0-hard51-maintenance-12-2026-11-21.json) | 743,525 | 820 | 1 | 1 |

| Task | Halogen v2 | Gufo IQ3_S | Gufo IQ3_XXS | Gufo IQ2_XS | Gufo Q2_0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| NodeBB image cleanup | Pass | Pass | Fail | Fail | Pass |
| Ansible mount discovery | Fail | Pass | Fail | Fail | Fail |
| Ansible type coercion | Pass | Pass | Pass | Fail | Pass |
| Ansible size parsing | Fail | Pass | Pass | Fail | Pass |
| Element voice seekbar | Pass | Pass | Fail | Pass | Pass |
| Flipt segment targeting | Pass | Pass | Pass | Pass | Pass |
| Teleport event storage | Pass | Pass | Pass | Pass | Pass |
| OpenLibrary alternate-script author names | Pass | Fail | Pass | Pass | Pass |
| OpenLibrary search-index updates | Pass | Pass | Pass | Pass | Pass |
| Navidrome nullable timestamps | Pass | Pass | Fail | Pass | Pass |
| qutebrowser key sequences | Pass | Pass | Pass | Pass | Pass |
| qutebrowser process retention | Pass | Fail | Fail | Fail | Fail |

Halogen and IQ3_S each reuse three audited trials from the [calibration](hard51-timing-pilot.md). Those six trials ran in amd64 emulation. The OpenLibrary search-index task used the same fallback for every deployment because its image contains an unmapped UID under rootless Podman. Other new trials ran in native x86 containers. Reference and empty-patch controls passed on each executor used.

The first native batch hit a patch-capture timeout. We recovered completed patches from the original containers where available, then regenerated the missing trials with the same budget. An IQ2_XS empty patch was regraded after verifying its original capture contained only terminal control bytes.

## Decision on expanding the comparison

Eight tasks distinguished at least two deployments. Four passed across all five. Q2_0 matched the leading total with fewer generated tokens than the other Gufo quants. It differed from Halogen and from IQ3_S on two tasks each, winning one and losing one in each comparison. The three deployments are tied in this cohort. Exact ranking needs more evidence than one attempt per task on 12 selected cases.

Keep the 150,000-token and 128-call limits. Three tasks exhausted the token budget and two reached the call limit. None needed the wall guard. A larger local comparison should freeze additional ordinary maintenance tasks before inference and verify each image with both patch controls. Keep the resulting score on its own cohort track alongside official full-set scores. Before increasing concurrency from two to three, measure completed trials per hour, inference queue time, and verifier host memory on the next calibration block.
