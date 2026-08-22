from __future__ import annotations

import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import torch

from iot_ids.models.ensemble.risk_layer import RiskLayer
from iot_ids.preprocessing.pipeline import PreprocessingPipeline
from iot_ids.utils.paths import REPO_ROOT


class MLPModule(torch.nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Linear(input_dim, 128),
            torch.nn.BatchNorm1d(128),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.2),
            torch.nn.Linear(128, 64),
            torch.nn.BatchNorm1d(64),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.2),
            torch.nn.Linear(64, 32),
            torch.nn.ReLU(),
            torch.nn.Linear(32, 1),
        )

    def forward(self, x):
        return self.net(x)


class AutoencoderModule(torch.nn.Module):
    def __init__(self, input_dim: int, bottleneck_dim: int = 16):
        super().__init__()
        self.encoder = torch.nn.Sequential(
            torch.nn.Linear(input_dim, 64),
            torch.nn.ReLU(),
            torch.nn.Linear(64, bottleneck_dim),
            torch.nn.ReLU(),
        )
        self.decoder = torch.nn.Sequential(
            torch.nn.Linear(bottleneck_dim, 64),
            torch.nn.ReLU(),
            torch.nn.Linear(64, input_dim),
        )

    def forward(self, x):
        code = self.encoder(x)
        return self.decoder(code)


class IDSSystemPipeline:
    """Unified single-source-of-truth system pipeline wrapper for the frozen IoT IDS architecture.
    Consumes ONLY frozen model checkpoints from models/final/.
    """

    def __init__(self, dataset_name: str, models_root: Path | None = None):
        self.dataset_name = dataset_name
        self.models_dir = (models_root or (REPO_ROOT / "models" / "final")) / dataset_name

        if not self.models_dir.exists():
            raise FileNotFoundError(f"Model directory not found for {dataset_name}: {self.models_dir}")

        # Load frozen artifacts
        self.preprocessor: PreprocessingPipeline = joblib.load(self.models_dir / "prep_indomain.joblib")
        self.prep_common: PreprocessingPipeline = joblib.load(self.models_dir / "prep_common.joblib")
        self.rf_model = joblib.load(self.models_dir / "rf_model.joblib")

        self.feature_names = self.preprocessor.numeric_cols
        self.common_feature_names = self.prep_common.numeric_cols
        input_dim = len(self.feature_names)

        self.mlp_model = MLPModule(input_dim=input_dim)
        self.mlp_model.load_state_dict(torch.load(self.models_dir / "mlp_model.pt"))
        self.mlp_model.eval()

        self.ae_model = AutoencoderModule(input_dim=input_dim, bottleneck_dim=16)
        self.ae_model.load_state_dict(torch.load(self.models_dir / "ae_model.pt"))
        self.ae_model.eval()

        self.risk_layer = RiskLayer.load(self.models_dir / "risk_layer.json")

    def predict_sample(self, df_sample: pd.DataFrame) -> dict:
        """Executes end-to-end inference and attribution over input dataframe samples (In-Domain 13-feature path)."""
        X_scaled = self.preprocessor.transform(df_sample)

        # 1. Supervised Predictions
        p_rf = self.rf_model.predict_proba(X_scaled)[:, 1]

        with torch.no_grad():
            X_tensor = torch.tensor(X_scaled, dtype=torch.float32)
            p_mlp = torch.sigmoid(self.mlp_model(X_tensor)).squeeze().numpy()
            if X_scaled.shape[0] == 1:
                p_mlp = np.array([float(p_mlp)])

            recon = self.ae_model(X_tensor).numpy()
            sq_err = (X_scaled - recon) ** 2
            mse = np.mean(sq_err, axis=1)

        p_sup = 0.5 * p_rf + 0.5 * p_mlp
        decisions = self.risk_layer.predict(p_rf, p_mlp, mse)
        s_ae = self.risk_layer.calibrate_ae_score(mse)

        # 2. Per-feature AE MSE Breakdown
        mean_sq_err_per_feature = dict(zip(self.feature_names, np.mean(sq_err, axis=0).tolist()))
        sorted_ae_err = dict(sorted(mean_sq_err_per_feature.items(), key=lambda x: x[1], reverse=True))

        return {
            "p_rf": p_rf,
            "p_mlp": p_mlp,
            "p_sup": p_sup,
            "ae_mse": mse,
            "s_ae": s_ae,
            "risk_states": [d.risk_state for d in decisions],
            "ae_feature_contributions": sorted_ae_err,
            "X_scaled": X_scaled,
            "feature_names": self.feature_names,
            "feature_count": len(self.feature_names),
        }

    def get_cross_domain_features(self, df_sample: pd.DataFrame) -> dict:
        """Extracts the frozen 6-feature F_common cross-domain representation."""
        X_common_scaled = self.prep_common.transform(df_sample)
        return {
            "X_common_scaled": X_common_scaled,
            "common_feature_names": self.common_feature_names,
            "common_feature_count": len(self.common_feature_names),
        }
