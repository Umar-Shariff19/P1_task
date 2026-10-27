# Known limitations and required follow-up

- **Split provenance:** Current Stage 3 generator is class-wise adapter-stream partitioning, followed by in-split timestamp sorting. Timestamp provenance differs by adapter. Existing split files have no linked generation manifest. Temporal generalization is not established.
- **Privacy:** Current training loop does not match the accountant's stated assumptions, uses seeded ordinary PRNGs, forces nonempty draws, normalizes by realized batch count, and returns raw loss diagnostics. Opacus is not a declared/pinned project dependency. No formal epsilon guarantee is supported.
- **Option C:** Source uses adversarially trained, non-private robust MLP for the neural fusion stream. The separately trained DP model is an analysis branch, not the fused/saved Option C checkpoint.
- **BCL:** Candidate BCL is separate from original risk calibration. Existing ToN-IoT test exposure and temporal-order concerns invalidate confirmatory evaluation absent a clean new protocol.
- **Historical metrics/artifacts:** Golden manifest has aggregate/per-dataset numbers and seed/dataset/feature count, but not source commit, split hashes, model hashes, or bound environment. Model files do not have a complete run-linked provenance record.
- **Manuscript authority:** Different manuscript variants were found. They are archived without editing; no authoritative submission version was established.
- **Runtime, attacks, XAI:** Source modules exist and some historical outputs remain, but safe synthetic tests and static review do not establish real-data efficacy, runtime performance, attack robustness, or explanation validity.
- **Candidate access:** Candidate source can be read and cleanup assets moved with authorization, but its Git metadata is inaccessible; its branch, HEAD, and complete status are unknown.
- **Dataset restriction:** BoT-IoT file 4 remains prohibited. The prohibited BCL evaluator and previously exposed ToN-IoT test split remain off limits.

See `../claims/unsupported_or_unverified_claims.md` for decisions and experiments needed.
