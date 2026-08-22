from __future__ import annotations

from pathlib import Path
import pandas as pd

from iot_ids.pipeline.system import IDSSystemPipeline
from iot_ids.utils.paths import REPO_ROOT


def test_system_pipeline_end_to_end() -> None:
    base_dir = REPO_ROOT / "data" / "processed" / "final"
    for ds in ["Edge-IIoTset", "ToN-IoT"]:
        target_dir = [d for d in (base_dir / ds).iterdir() if d.is_dir()][0]
        test_df = pd.read_parquet(target_dir / "splits" / "test.parquet").head(10)

        pipeline = IDSSystemPipeline(dataset_name=ds)
        res = pipeline.predict_sample(test_df)

        assert len(res["p_sup"]) == 10
        assert len(res["s_ae"]) == 10
        assert len(res["risk_states"]) == 10
        assert all(state in ["BENIGN", "HIGH CONFIDENCE ATTACK", "SUSPICIOUS / ANOMALOUS"] for state in res["risk_states"])
        assert len(res["ae_feature_contributions"]) == len(pipeline.feature_names)
        assert res["feature_count"] == 13

        cd_res = pipeline.get_cross_domain_features(test_df)
        assert cd_res["common_feature_count"] == 6
        assert len(cd_res["common_feature_names"]) == 6
