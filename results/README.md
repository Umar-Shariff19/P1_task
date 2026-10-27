# Results and implementation evidence

This directory is the project's central record of what the implementation contains, what was inspected or tested, and which research claims have supporting evidence. It explicitly replaces manuscript files as the central research-evidence record. It is **not** a collection of newly reproduced scientific results.

## Canonical records

- `implementation/implementation_status.md` — current software behavior and maturity.
- `implementation/component_inventory.md` — source and artifact map.
- `implementation/implementation_decisions.md` — methodological and integration decisions.
- `implementation/known_limitations.md` — unresolved correctness and research questions.
- `implementation/dataset_path_safety_policy.md` — path-safety policy and limits of the partial lexical gate; real-root enforcement and adapter integration are not implemented.
- `implementation/research_readiness_matrix.md` — evidence gaps, next safe actions, and owner/experiment blockers.
- `implementation/controlled_experiment_plan.md` — a proposed future protocol with prerequisites and stop conditions; it has not been run.
- `validation/validation_log.md` — actual commands, outcomes, scope, and restrictions.
- `provenance/` — split, model/artifact, metric provenance evidence, historical linkage matrix, prospective manifest schema, and clearly synthetic schema examples.
- `src/iot_ids/provenance/manifest_validation.py` — reusable structural validator for the canonical prospective schema; never an authorization or evidence-truth check.
- `claims/claim_evidence_ledger.md` — canonical claim-by-claim status; this controls over older report language.
- `claims/unsupported_or_unverified_claims.md` — open issues requiring author decisions or experiments.
- `experiments/experiment_registry.md` — registry for future controlled experiments.

Historical reports remain in their existing locations and should be cited as historical records, not silently rewritten. New validation must be appended to the validation log with its command, date, scope, outcome, files affected, and data-access limits. New experiments need an entry in the experiment registry and a separate run manifest recording source commit, configuration, input split identity, environment, outputs, and artifact hashes where safe and authorized.

Existing model artifacts are under `models/`; existing manifests and metric outputs remain under `reports/`. Their presence does not prove their provenance. Never overwrite them as part of evidence documentation. Historical numbers must be labeled `HISTORICAL_REPORTED` until the relevant run and inputs are established; synthetic tests never establish real-data detection performance.

All data-access restrictions apply here too: never access BoT-IoT file 4, and never run the prohibited ToN-IoT BCL evaluator or access the previously exposed ToN-IoT test split by any route. Do not regenerate official datasets, splits, checkpoints, manifests, or historical metrics for documentation purposes.

## Open scientific issues

The available source does not substantiate a formal differential-privacy guarantee; the split files are not tied to a specific generator run; historical metrics lack complete artifact/input provenance; the candidate BCL protocol has test-split contamination concerns; and the authoritative manuscript version was not established before manuscript-only files were archived. See the claim ledger and open-claims register before using any result.
