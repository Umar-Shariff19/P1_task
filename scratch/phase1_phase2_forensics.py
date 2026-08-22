import hashlib
import json
import os
import sys
from pathlib import Path
import joblib
import torch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from iot_ids.utils.paths import REPO_ROOT

def get_file_info(path: Path) -> dict:
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    mtime = os.path.getmtime(path)
    size = os.path.getsize(path)
    return {
        "md5": hasher.hexdigest(),
        "mtime_iso": torch.datetime.datetime.fromtimestamp(mtime).isoformat() if hasattr(torch, 'datetime') else str(mtime),
        "size_bytes": size
    }

def main():
    print("============================================================")
    print("=== PHASE 1 & 2: FROZEN GROUND TRUTH & CHECKPOINT FORENSICS ===")
    print("============================================================\n")

    # 1. Extract Frozen Ground Truth
    eval_json_path = REPO_ROOT / "reports" / "tables" / "final_evaluation_results.json"
    if not eval_json_path.exists():
        raise FileNotFoundError(f"Missing authoritative ground truth file: {eval_json_path}")

    eval_data = json.loads(eval_json_path.read_text(encoding="utf-8"))

    print("--- 1. Authoritative Frozen Ground Truth Extraction ---")
    print(json.dumps(eval_data, indent=2))

    # 2. Checkpoint Forensics
    models_root = REPO_ROOT / "models" / "final"
    datasets = ["Edge-IIoTset", "ToN-IoT"]

    checkpoint_info = {}

    print("\n--- 2. Checkpoint Metadata & Schema Forensics ---")
    for ds in datasets:
        ds_dir = models_root / ds
        print(f"\n[Dataset: {ds}] Directory: {ds_dir}")
        rf_path = ds_dir / "rf_model.joblib"
        mlp_path = ds_dir / "mlp_model.pt"
        ae_path = ds_dir / "ae_model.pt"
        prep_in_path = ds_dir / "prep_indomain.joblib"
        prep_c_path = ds_dir / "prep_common.joblib"
        risk_path = ds_dir / "risk_layer.json"

        rf = joblib.load(rf_path)
        prep_in = joblib.load(prep_in_path)
        prep_c = joblib.load(prep_c_path)
        mlp_sd = torch.load(mlp_path)
        ae_sd = torch.load(ae_path)
        risk_data = json.loads(risk_path.read_text(encoding="utf-8"))

        rf_n_features = rf.n_features_in_
        prep_in_cols = prep_in.numeric_cols
        prep_c_cols = prep_c.numeric_cols

        # MLP input dimension from weight shape
        mlp_in_dim = mlp_sd["net.0.weight"].shape[1]
        ae_in_dim = ae_sd["encoder.0.weight"].shape[1]

        print(f"  - prep_indomain.joblib active numeric columns ({len(prep_in_cols)}): {prep_in_cols}")
        print(f"  - prep_common.joblib active numeric columns ({len(prep_c_cols)}): {prep_c_cols}")
        print(f"  - Random Forest input features (rf.n_features_in_): {rf_n_features}")
        print(f"  - PyTorch MLP input dimension (net.0.weight): {mlp_in_dim}")
        print(f"  - PyTorch Autoencoder input dimension (encoder.0.weight): {ae_in_dim}")
        print(f"  - Risk Layer calibration count: {len(risk_data['val_mse_sorted'])}")

        has_src_pkts = "src_pkts" in prep_in_cols or "src_pkts" in prep_c_cols
        has_dst_pkts = "dst_pkts" in prep_in_cols or "dst_pkts" in prep_c_cols
        print(f"  - Contains src_pkts/dst_pkts? {has_src_pkts or has_dst_pkts} (Expected: False)")

        checkpoint_info[ds] = {
            "indomain_cols": prep_in_cols,
            "indomain_count": len(prep_in_cols),
            "common_cols": prep_c_cols,
            "common_count": len(prep_c_cols),
            "rf_n_features": rf_n_features,
            "mlp_in_dim": mlp_in_dim,
            "ae_in_dim": ae_in_dim,
            "files": {
                "rf_model.joblib": get_file_info(rf_path),
                "mlp_model.pt": get_file_info(mlp_path),
                "ae_model.pt": get_file_info(ae_path),
                "prep_indomain.joblib": get_file_info(prep_in_path),
                "prep_common.joblib": get_file_info(prep_c_path),
                "risk_layer.json": get_file_info(risk_path),
            }
        }

    forensic_summary_path = REPO_ROOT / "scratch" / "checkpoint_forensics_summary.json"
    forensic_summary_path.write_text(json.dumps(checkpoint_info, indent=2), encoding="utf-8")
    print(f"\nSaved Checkpoint Forensics Summary to: {forensic_summary_path}\n")

if __name__ == "__main__":
    main()
