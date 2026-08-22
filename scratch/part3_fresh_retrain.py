import json
import sys
import time
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.ensemble import RandomForestClassifier

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from iot_ids.preprocessing.pipeline import PreprocessingPipeline
from iot_ids.models.ensemble.risk_layer import RiskLayer
from iot_ids.utils.paths import REPO_ROOT

class MLPModule(nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
        )

    def forward(self, x):
        return self.net(x)

class AutoencoderModule(nn.Module):
    def __init__(self, input_dim: int, bottleneck_dim: int = 16):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, bottleneck_dim),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(bottleneck_dim, 64),
            nn.ReLU(),
            nn.Linear(64, input_dim),
        )

    def forward(self, x):
        code = self.encoder(x)
        return self.decoder(code)

def train_fresh_mlp(X: np.ndarray, y: np.ndarray, seed: int = 42, epochs: int = 15, batch_size: int = 256) -> MLPModule:
    torch.manual_seed(seed)
    np.random.seed(seed)
    model = MLPModule(input_dim=X.shape[1])
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    ds = TensorDataset(torch.tensor(X, dtype=torch.float32), torch.tensor(y, dtype=torch.float32).unsqueeze(1))
    loader = DataLoader(ds, batch_size=batch_size, shuffle=True)

    model.train()
    for epoch in range(epochs):
        for bx, by in loader:
            optimizer.zero_grad()
            out = model(bx)
            loss = criterion(out, by)
            loss.backward()
            optimizer.step()

    return model

def train_fresh_autoencoder(X_benign: np.ndarray, seed: int = 42, epochs: int = 15, batch_size: int = 256) -> AutoencoderModule:
    torch.manual_seed(seed)
    np.random.seed(seed)
    model = AutoencoderModule(input_dim=X_benign.shape[1], bottleneck_dim=16)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    ds = TensorDataset(torch.tensor(X_benign, dtype=torch.float32))
    loader = DataLoader(ds, batch_size=batch_size, shuffle=True)

    model.train()
    for epoch in range(epochs):
        for (bx,) in loader:
            optimizer.zero_grad()
            out = model(bx)
            loss = criterion(out, bx)
            loss.backward()
            optimizer.step()

    return model

def run_fresh_retraining(seed: int = 42, output_suffix: str = "run1"):
    print(f"============================================================")
    print(f"=== PART 3: FRESH RETRAINING (SEED={seed}, SUFFIX={output_suffix}) ===")
    print(f"============================================================\n")

    base_dir = REPO_ROOT / "data" / "processed" / "final"
    exp_dir = Path("reproducibility/fresh_retraining_20260821_010000") / output_suffix
    exp_dir.mkdir(parents=True, exist_ok=True)

    datasets = ["Edge-IIoTset", "ToN-IoT"]
    common_cols = ["duration", "src_bytes", "proto_tcp", "proto_udp", "proto_icmp", "is_well_known_port"]

    training_manifest = {}

    for ds in datasets:
        t0 = time.time()
        print(f"--- Fresh Training for {ds} (Seed={seed}) ---")
        ds_dir = base_dir / ds
        target_dir = [d for d in ds_dir.iterdir() if d.is_dir()][0]
        splits_dir = target_dir / "splits"

        train_df = pd.read_parquet(splits_dir / "train.parquet")
        val_df = pd.read_parquet(splits_dir / "val.parquet")

        ds_out_dir = exp_dir / ds
        ds_out_dir.mkdir(parents=True, exist_ok=True)

        if ds == "Edge-IIoTset":
            indomain_cols = common_cols + [
                "temporal_causal_count", "temporal_causal_rate", "temporal_iat_mean",
                "behavioral_dest_diversity", "behavioral_src_activity",
                "mqtt_msgtype", "mbtcp_unit_id"
            ]
        else:
            indomain_cols = common_cols + [
                "temporal_causal_count", "temporal_causal_rate", "temporal_iat_mean",
                "behavioral_dest_diversity", "behavioral_src_activity",
                "conn_state_encoded", "http_method_encoded"
            ]

        # Fit preprocessors freshly
        prep_common = PreprocessingPipeline(numeric_cols=common_cols)
        X_tr_c = prep_common.fit_transform(train_df)

        prep_indomain = PreprocessingPipeline(numeric_cols=indomain_cols)
        X_tr_in = prep_indomain.fit_transform(train_df)
        y_tr = train_df["label"].values

        joblib.dump(prep_common, ds_out_dir / "prep_common.joblib")
        joblib.dump(prep_indomain, ds_out_dir / "prep_indomain.joblib")

        print(f"  Train samples: {len(train_df):,}, Active In-Domain features: {X_tr_in.shape[1]}")

        # 1. Fresh Random Forest
        rf = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=seed, n_jobs=-1)
        rf.fit(X_tr_in, y_tr)
        joblib.dump(rf, ds_out_dir / "rf_model.joblib")

        # 2. Fresh MLP Classifier
        mlp = train_fresh_mlp(X_tr_in, y_tr, seed=seed, epochs=15, batch_size=256)
        torch.save(mlp.state_dict(), ds_out_dir / "mlp_model.pt")

        # 3. Fresh Autoencoder
        ben_mask = (y_tr == 0)
        X_tr_benign = X_tr_in[ben_mask]
        ae = train_fresh_autoencoder(X_tr_benign, seed=seed, epochs=15, batch_size=256)
        torch.save(ae.state_dict(), ds_out_dir / "ae_model.pt")

        # 4. Calibrate Risk Layer on Fresh Validation Split
        X_val_in = prep_indomain.transform(val_df)
        y_val = val_df["label"].values
        val_benign_mask = (y_val == 0)
        X_val_benign = X_val_in[val_benign_mask]

        with torch.no_grad():
            val_benign_tensor = torch.tensor(X_val_benign, dtype=torch.float32)
            recon_val = ae(val_benign_tensor).numpy()
            val_benign_mse = np.mean((X_val_benign - recon_val) ** 2, axis=1)

        risk_layer = RiskLayer(tau_sup=0.50, tau_ae=0.80)
        risk_layer.fit_ae_calibration(val_benign_mse)
        risk_layer.save(ds_out_dir / "risk_layer.json")

        t_elapsed = time.time() - t0
        print(f"  Fresh Training Complete in {t_elapsed:.2f}s -> Saved to {ds_out_dir}\n")

        training_manifest[ds] = {
            "train_rows": len(train_df),
            "val_rows": len(val_df),
            "feature_count": X_tr_in.shape[1],
            "feature_names": prep_indomain.numeric_cols,
            "seed": seed,
            "training_time_sec": t_elapsed,
            "output_dir": str(ds_out_dir)
        }

    manifest_path = exp_dir / "training_manifest.json"
    manifest_path.write_text(json.dumps(training_manifest, indent=2), encoding="utf-8")
    print(f"Fresh Retraining Manifest Saved: {manifest_path}\n")

if __name__ == "__main__":
    run_fresh_retraining(seed=42, output_suffix="run1")
