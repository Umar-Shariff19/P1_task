# Experiment registry

| ID | Status | Purpose | Required protocol/evidence | Restrictions |
|---|---|---|---|---|
| DP mechanism correction and validation | PROPOSED — requires author approval | Establish whether a defensible privacy guarantee can be made for a newly trained model. | Specify adjacency, sampler, clipping, secure RNG, noise, normalization, accountant/version, delta, released diagnostics, and independent tests; new checkpoint/run manifest. | Do not change/overwrite official artifacts or claim current guarantee. |
| Split provenance recovery / temporal study | PROPOSED — provenance recovery first | Establish exact historical split generation if evidence exists; otherwise design a separate temporal protocol. | Source/run commit, per-split identities, adapter timestamp semantics, boundaries, manifest, and controlled evaluation. | No protected data; do not regenerate official split artifacts. |
| Clean BCL evaluation | DEFERRED | Assess BCL without contaminated test evidence. | Freeze calibration protocol on validation, define temporal boundaries, pre-register scoring and untouched safe test source, document no reuse of exposed ToN test split. | Prohibited ToN BCL evaluator/test split remain inaccessible. |
| Artifact provenance closure | PROPOSED | Tie existing/new artifacts to exact source and environment where feasible. | Investigate already-existing metadata only; future runs add hashes/config/env/source commit. | Never hash protected data or fabricate historical linkage. |

No experiment above was run as part of Phase I.
