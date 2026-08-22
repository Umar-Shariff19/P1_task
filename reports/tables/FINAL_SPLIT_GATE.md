# FINAL STRUCTURAL SPLIT FORENSIC GATE REPORT

> [!IMPORTANT]
> **VERDICT: STRUCTURAL SPLIT FORENSIC GATE — PASS**
>
> Structural splitting (60% Train / 20% Val / 20% Test) successfully executed across **Edge-IIoTset** and **ToN-IoT Network** with zero cross-split overlap and guaranteed attack-category representation across all splits.

---

## Structural Split Manifest Evidence

| Dataset | Total Rows | Train (60%) | Val (20%) | Test (20%) | Train Benign/Attack | Val Benign/Attack | Test Benign/Attack | Split Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Edge-IIoTset** | 157,800 | 94,680 | 31,560 | 31,560 | 14,580 / 80,100 | 4,861 / 26,699 | 4,860 / 26,700 | **PASS** |
| **ToN-IoT Network** | 211,043 | 126,625 | 42,209 | 42,209 | 30,000 / 96,625 | 10,000 / 32,209 | 10,000 / 32,209 | **PASS** |

---

## Leakage & Contamination Audits
- **Zero Cross-Split Overlap**: Confirmed indices and partition rows maintain strict separation.
- **Untouched Test Split Guarantee**: Test splits preserved without model fitting or threshold tuning contamination.
- **Verdict**: **STRUCTURAL SPLIT FORENSIC GATE PASSED**.
