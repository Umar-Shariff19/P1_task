# MASTER PAPER EVIDENCE PACKAGE — IEEE IIOT IDS PAPER

**Date:** 2026-10-05  
**Baseline Release Commit:** `c8ffa15f03e61fe601994bf53396b8614d9d3596`  
**Status:** **AUTHORITATIVE & COMPLETE (PHASES 0–6 VERIFIED)**

---

## 1. Executive Overview
This document compiles the complete, immutable evidence package for updating `final_ieee_paper/main.tex`. All reported numbers are directly traceable to executable scripts and JSON artifacts in `reports/`.

---

## 2. Authoritative Research Question
> *Can detection, adversarial robustness, neural-branch differential privacy, and explainability be evaluated coherently within a standardized IIoT flow representation and a unified RF–robust-MLP ensemble framework?*

---

## 3. Core Narrative & Findings
1. **Clean Performance:** Option C clean mean ROC-AUC (**0.9970**) preserves near-RF performance (**0.9976**). Option C does **NOT** improve clean accuracy over pure RF, but serves as a security-enabling wrapper.
2. **Baseline Adversarial Defense:** Under neural-stream PGD-10 evaluation, Option C suppresses evasion ASR to **4.0%** on NF-ToN-IoT-v2 (compared to 48.0% for standalone robust MLP and 53.8% for standard MLP).
3. **Adaptive Surrogate Attack:** Under an adaptive surrogate-gradient attack, evasion ASR rises to **11.8%** on Edge-IIoTset and **5.9%** on NF-ToN-IoT-v2, proving that neural robustness does not imply complete immunity to adaptive surrogate attacks.
4. **Fusion Weight Operating Point:** Ablation across $w \in [0.0, 1.0]$ confirms $w=0.7$ as a *high-clean-performance operating point with a favorable robustness tradeoff under the evaluated attack protocol*.
5. **Differential Privacy Scope:** Neural stream achieves audited $(\varepsilon=2.37, \delta=10^{-5})$-DP under Opacus PRV accounting. Privacy applies **exclusively to the neural stream**.
6. **Explainability Scope:** Delivered via Weighted Component Attribution Aggregation ($0.7 \text{RF}_{\text{norm}} + 0.3 \text{MLP}_{\text{norm}}$); explicitly **not** exact SHAP for the non-linear fused predictor.
7. **Runtime Scope:** Single-CPU host classifier inference throughput achieves **16,505 samples/sec** (0.0606 ms/sample) at batch $N=1024$.

---

## 4. Paper Revision Checklist & Action Plan

### Must Revise
- [ ] **Abstract & Intro:** Reframe around unified research question.
- [ ] **Clean AUC Claims:** Correct text to state Option C preserves near-RF performance (0.9970 vs 0.9976).
- [ ] **Flow Timeouts:** Insert explicit 15s inactivity and 120s max duration parameters in Section III-A.
- [ ] **RF Hyperparameters:** Optionally add `max_depth=15` to Section III-B.
- [ ] **Fusion Weight Sweep:** Add ablation results table/figure explaining $w=0.7$ operating point.
- [ ] **Baseline PGD Wording:** Explicitly label baseline attack as neural-stream PGD-10 evaluated through ensemble.
- [ ] **Adaptive Surrogate Attack:** Integrate Phase 5 adaptive attack results table/figure and threat model limitations.
- [ ] **DP Scope Bounds:** Clarify that DP applies strictly to the neural stream.
- [ ] **XAI Methodology:** Label as Weighted Component Attribution Aggregation; clarify non-SHAP nature.
- [ ] **XAI Attack-Family Analysis:** Integrate category-level attributions and local analyst case studies.
- [ ] **Bootstrap CIs:** Add 95% CIs to performance tables.
- [ ] **Runtime Scope:** Label throughput strictly as classifier-only host CPU benchmark.
- [ ] **Limitations Section:** Update Section VI with formal limitation statements.

---

## 5. Paper Revision Status
- **Evidence Package Complete:** **YES**
- **Numerical Contradictions Remaining:** **0**
- **Unsupported Claims Identified:** Several narrative wording claims (mapped in `CLAIM_EVIDENCE_MATRIX.md`)
- **Missing Mandatory Experiments:** **NONE**
