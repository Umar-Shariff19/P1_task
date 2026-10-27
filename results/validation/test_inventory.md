# Test inventory and safe execution notes

Test files exist under `tests/unit/` and `tests/integration/`. Filenames do not establish that their fixtures are synthetic. Inspect the selected test and its imported helpers for dataset/checkpoint reads and file writes before invocation.

Known safe focused target from prior Phase G/H validation: `tests/unit/data/test_flow_aggregator.py`, which uses synthetic packet/flow fixtures. The Phase H record reports 10 passing tests.

Do not run the golden pipeline, full integration suite, `tests/unit/test_dp_privacy.py`, publication/legacy audit tests, BCL tests/evaluators, or tests whose dependencies can open local dataset paths without first reviewing them. In particular, never access BoT-IoT file 4 or the previously exposed ToN-IoT test split. Synthetic unit outcomes must not be described as detection-performance or research validation.
