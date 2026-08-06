# Label Taxonomy

Version: `label-taxonomy-v1`

The mandatory cross-dataset target is binary:

- `BENIGN`
- `ATTACK`

Raw labels and attack family/subtype are preserved as metadata where available. They are not collapsed away during ingestion.

## Dataset Mappings

- CICIDS2017: `Label == BENIGN` maps to `BENIGN`; all other observed labels map to `ATTACK`.
- Edge-IIoTset: `Attack_label == 0` or `Attack_type == Normal` maps to `BENIGN`; all other observed attack types map to `ATTACK`.
- BoT-IoT: `attack == 0` or `category == Normal` maps to `BENIGN`; attack `category`/`subcategory` are preserved as raw taxonomy metadata.
- N-BaIoT: labels are derived from traffic filenames, for example `*.benign.csv`, `*.gafgyt.combo.csv`, and `*.mirai.udp.csv`.

## Multiclass Position

Coarse multiclass harmonization across all four datasets is not frozen as a primary cross-dataset task. The observed attack families do not align cleanly across CICIDS2017, Edge-IIoTset, BoT-IoT and N-BaIoT. Binary `BENIGN`/`ATTACK` is the scientifically defensible primary cross-dataset objective. Dataset-specific multiclass evaluation can remain a later within-dataset analysis.

