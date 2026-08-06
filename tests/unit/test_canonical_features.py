from __future__ import annotations

import pandas as pd

from iot_ids.features.canonical.builder import build_canonical_features


def test_cicids_canonical_features() -> None:
    frame = pd.DataFrame(
        {
            "Flow Duration": [1_000_000],
            "Destination Port": [80],
            "Total Fwd Packets": [3],
            "Total Backward Packets": [2],
            "Total Length of Fwd Packets": [300],
            "Total Length of Bwd Packets": [200],
            "Flow Bytes/s": [500.0],
            "Flow Packets/s": [5.0],
            "Packet Length Mean": [100.0],
            "Packet Length Std": [2.0],
            "Min Packet Length": [90],
            "Max Packet Length": [110],
            "Flow IAT Mean": [10],
            "Flow IAT Std": [1],
            "SYN Flag Count": [1],
            "ACK Flag Count": [1],
            "RST Flag Count": [0],
            "Label": ["BENIGN"],
        }
    )
    out = build_canonical_features("CICIDS2017", frame)
    assert out.loc[0, "duration_seconds"] == 1
    assert out.loc[0, "total_packets"] == 5
    assert out.loc[0, "canonical_label"] == "BENIGN"


def test_bot_canonical_features() -> None:
    frame = pd.DataFrame(
        {
            "dur": [2.0],
            "proto": ["tcp"],
            "state": ["CON"],
            "sport": [123],
            "dport": [80],
            "pkts": [10],
            "spkts": [6],
            "dpkts": [4],
            "bytes": [1000],
            "sbytes": [700],
            "dbytes": [300],
            "rate": [500],
            "mean": [100],
            "stddev": [10],
            "min": [40],
            "max": [200],
            "saddr": ["a"],
            "daddr": ["b"],
            "stime": [1],
            "ltime": [3],
            "attack": [1],
            "category": ["DoS"],
        }
    )
    out = build_canonical_features("BoT-IoT", frame)
    assert out.loc[0, "canonical_label"] == "ATTACK"
    assert out.loc[0, "traffic_asymmetry"] == 0.4


def test_nbaiot_canonical_features_excludes_device_as_model_prefix() -> None:
    frame = pd.DataFrame({"MI_dir_L0.01_mean": [1.2], "HH_L1_std": [0.3]})
    out = build_canonical_features("N-BaIoT", frame, source_path="1.gafgyt.combo.csv")
    assert out.loc[0, "source_agg_MI_dir_L0.01_mean"] == 1.2
    assert out.loc[0, "raw_label"] == "gafgyt.combo"
    assert out.loc[0, "device_id"] == "1"

