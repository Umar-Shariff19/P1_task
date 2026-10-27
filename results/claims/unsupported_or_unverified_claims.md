# Unsupported or unverified claims

| Claim | Current status | What would be needed |
|---|---|---|
| Existing Stage 3 splits are a global chronological holdout | `CONTRADICTED` by current generator semantics; historical files `UNVERIFIED`. | Historical run manifest, or a new controlled split design and safe re-evaluation. |
| Existing neural fusion model has epsilon 2.37 / delta 1e-5 guarantee | `CONTRADICTED` as a claim about current Option C; mechanism guarantee `UNVERIFIED`. | Correct, pinned DP mechanism/accountant and release analysis; new authorized training; independent validation. |
| Candidate BCL results establish clean generalization | `UNVERIFIED`/not confirmatory due documented prior test exposure. | New protocol with untouched test data, temporal boundaries, and no use of prohibited split. |
| Four historical ROC-AUC aggregates are newly reproduced | False; `HISTORICAL_REPORTED`. | Do not use that wording without a separate reproduction run and complete provenance. |
| Historical artifacts are bound to the current source/splits/environment | `UNVERIFIED`. | Source commit, split hashes/identities, artifact hashes, config, and environment tied together by trustworthy run record. |
| Runtime, robustness, XAI, attack, and privacy reports prove current performance | `UNVERIFIED` or `PARTIALLY_SUPPORTED`, depending on claim. | Review each report's source/input/output manifest and run controlled experiments. |

Manuscript sources were archived without correction because the authoritative version was not identified and scientific statements were not silently rewritten. Resolve the submission version and claim wording as an author decision, using this ledger as implementation evidence.
