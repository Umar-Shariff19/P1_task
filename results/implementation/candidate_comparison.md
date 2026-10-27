# Candidate implementation comparison

Comparison source: `C:\Users\umari\Documents\umar_review-main\umar_review-main`. Source files were inspected without running candidate scripts. The candidate Git metadata is inaccessible, so its branch/HEAD/status and tracked state are unknown. The original repository remains authoritative.

| Candidate-only material | Assessment | Decision |
|---|---|---|
| `src/iot_ids/data/sampling.py` with reservoir sampling and stratified split helpers | Potentially useful for future bounded sampling, but adopting it would change split semantics and may undermine current historical comparability. | **Defer**; only consider in a separately versioned experiment after protocol approval. |
| `src/iot_ids/experiments/provenance.py` | Useful direction for manifests/validation. Its verified-split helper reads validation and test parquet files and hash helper hashes arbitrary paths, so it must not be called on protected inputs. | **Adopt after correction** in original architecture: path allowlist, no protected-file route, no retroactive claims, synthetic tests. Not integrated now. |
| `src/iot_ids/models/ensemble/bcl.py`, `src/iot_ids/runtime/bcl_engine.py` | Runtime BCL adds sequential behavioral consistency on frozen detector scores; tests include synthetic cases but also a test that reads ToN-IoT validation/test parquet. | **Keep experimental** in candidate; do not port or run the test evaluator. A fresh safe protocol and temporal audit are prerequisites. |
| Candidate BCL evaluator and reports | Candidate code calibrates from validation data and scores test data; prior ToN-IoT test exposure is documented by candidate project notes. | **Reject for confirmatory integration now**; retain source/reports as historical candidate evidence, never access the exposed test split. |
| `src/iot_ids/adversarial/black_box.py` and SPSA tests | Potentially useful query-based attack utilities; no original integration or safe validation was performed in this phase. | **Defer** pending threat-model review and isolated synthetic tests. |
| `src/iot_ids/data/adapters/bot_iot.py` and BoT-IoT tests | Additional adapter/scope, but its source enumerates all CSVs when given a directory. It was not run, and BoT-IoT file 4 remains prohibited. | **Keep in candidate; do not integrate or run** without an explicit file allowlist that can never select file 4. |
| Candidate XAI/bootstrap output code | XAI figure output formerly targeted a manuscript tree; bootstrap emitted JSON and LaTeX. | **Corrected in candidate**: XAI now targets `reports/xai/figures/`; bootstrap retains JSON and no longer writes TeX. No experiment was run. |
| Candidate manuscript/audit utilities | Submission compilation, publication audits, manuscript editors, paper figure and evidence generators. | **Archived** outside both trees after review; historical generated reports were retained. |
| Candidate project-context docs and evidence reports | Include research plans, caveats, candidate historical metrics and the prior test-exposure statement. | **Preserve** for future comparison. They are not authoritative or newly verified. |

No candidate model, method, BCL score, or experimental result was integrated into the original project. Candidate-only source/tests remain available in the candidate tree; manuscript-only files/tools were archived outside both trees.
