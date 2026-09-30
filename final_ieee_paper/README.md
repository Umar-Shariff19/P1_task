# FINAL IEEE RESEARCH PAPER - OVERLEAF PROJECT

This folder contains the complete, editable IEEE LaTeX project for the manuscript:

**Title**: *An Adversarially Robust, Differentially Private, and Explainable Ensemble Framework for Industrial IoT Intrusion Detection*

## Project Structure
- `main.tex`: Primary LaTeX manuscript source formatted in standard IEEE two-column `IEEEtran` layout.
- `references.bib`: BibTeX bibliography database containing all 25 cited research references.
- `figures/`: High-resolution IEEE single-column figures:
  - `detection_performance.png`: Detection ROC-AUC comparison across models and datasets.
  - `adversarial_asr.png`: Adversarial PGD-10 Attack Success Rate ($\epsilon=0.1$).
  - `runtime_throughput.png`: Host inference throughput scaling across batch sizes $N \in \{1, \dots, 1024\}$.
- `tables/`: Table assets and templates.
- `FINAL_IEEE_PAPER_Overleaf.zip`: Self-contained Overleaf-ready upload package.

## Overleaf Compilation Instructions
1. Download `FINAL_IEEE_PAPER_Overleaf.zip`.
2. Log in to [Overleaf](https://www.overleaf.com/).
3. Click **New Project** -> **Upload Project**.
4. Select `FINAL_IEEE_PAPER_Overleaf.zip`.
5. Set main document to `main.tex` and compiler to **pdfLaTeX**.
6. Click **Recompile**.
