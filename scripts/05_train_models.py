import json
import sys
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


def train_mlp(X: np.ndarray, y: np.ndarray, epochs: int = 15, batch_size: int = 256) -> MLPModule:
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


def train_autoencoder(X_benign: np.ndarray, epochs: int = 15, batch_size: int = 256) -> AutoencoderModule:
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


def main():
    print("============================================================")
    print("=== STAGE 05: MODEL TRAINING (RF, MLP, AUTOENCODER) ===")
    print("============================================================\n")

    base_dir = REPO_ROOT / "data" / "processed" / "final"
    models_base = REPO_ROOT / "models" / "final"
    datasets = ["Edge-IIoTset", "ToN-IoT"]

    for ds in datasets:
        print(f"--- Training Component Models for {ds} ---")
        ds_dir = base_dir / ds
        fingerprint_dirs = [d for d in ds_dir.iterdir() if d.is_dir()]
        target_dir = fingerprint_dirs[0]
        splits_dir = target_dir / "splits"

        train_df = pd.read_parquet(splits_dir / "train.parquet")
        out_model_dir = models_base / ds
        out_model_dir.mkdir(parents=True, exist_ok=True)

        common_cols = [
            "duration", "src_bytes", "proto_tcp", "proto_udp", "proto_icmp", "is_well_known_port"
        ]
        
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

        prep_common = PreprocessingPipeline(numeric_cols=common_cols)
        X_tr_common = prep_common.fit_transform(train_df)

        prep_indomain = PreprocessingPipeline(numeric_cols=indomain_cols)
        X_tr_indomain = prep_indomain.fit_transform(train_df)
        y_train = train_df["label"].values

        joblib.dump(prep_common, out_model_dir / "prep_common.joblib")
        joblib.dump(prep_indomain, out_model_dir / "prep_indomain.joblib")

        print("  Training Random Forest (100 trees, max depth 15)...")
        rf = RandomForestClassifier(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)
        rf.fit(X_tr_indomain, y_train)
        joblib.dump(rf, out_model_dir / "rf_model.joblib")

        print("  Training MLP Classifier...")
        mlp = train_mlp(X_tr_indomain, y_train, epochs=15, batch_size=256)
        torch.save(mlp.state_dict(), out_model_dir / "mlp_model.pt")

        print("  Training Autoencoder on Benign Samples...")
        ben_mask = (y_train == 0)
        X_tr_benign = X_tr_indomain[ben_mask]
        
        ae = train_autoencoder(X_tr_benign, epochs=15, batch_size=256)
        torch.save(ae.state_dict(), out_model_dir / "ae_model.pt")

        print(f"Component models saved to {out_model_dir}\n")

    print("Stage 05 Complete: All component models trained successfully.")

if __name__ == "__main__":
    main()
