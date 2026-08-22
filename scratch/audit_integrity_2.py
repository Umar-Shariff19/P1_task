import joblib
from pathlib import Path

print("============================================================")
print("=== AUDIT 2: IN-DOMAIN vs CROSS-DOMAIN SEPARATION ===")
print("============================================================\n")

models_base = Path("models/final")

for ds in ["Edge-IIoTset", "ToN-IoT"]:
    m_dir = models_base / ds
    prep_c = joblib.load(m_dir / "prep_common.joblib")
    prep_i = joblib.load(m_dir / "prep_indomain.joblib")

    print(f"--- Dataset: {ds} ---")
    print(f"  Cross-Domain Preprocessor Features ({len(prep_c.numeric_cols)}):")
    print(f"    {prep_c.numeric_cols}")
    print(f"  In-Domain Preprocessor Features ({len(prep_i.numeric_cols)}):")
    print(f"    {prep_i.numeric_cols}")
    print()

