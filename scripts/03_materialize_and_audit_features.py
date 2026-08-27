"""Stage 3 Materialization and Statistical Audit Runner.

Ingests flows from ToN-IoT, Edge-IIoTset, NF-ToN-IoT-v2, and CICIoT2023,
materializes chronological 60/20/20 train/val/test feature splits with strict boundary state resets,
and generates empirical statistical quality audit reports (KS, Wasserstein, MI, correlation, VIF).
"""
from __future__ import annotations

from pathlib import Path
import time
import numpy as np
import pandas as pd

from iot_ids.data.adapters import (
    ToNIoTAdapter,
    EdgeIIoTsetAggregatorAdapter,
    NFToNIoTAdapter,
    CICIoT2023Adapter,
)
from iot_ids.features.canonical.flow_builder import CanonicalFlowBuilder, CANONICAL_18_FEATURE_NAMES
from iot_ids.features.quality import (
    compute_distribution_statistics,
    compute_distribution_shift,
    compute_mutual_information,
    compute_correlation,
    compute_vif,
)

FEATURE_PROFILES = {
    "baseline_common": [
        "flow_duration", "flow_bytes_per_sec", "proto_tcp", "proto_udp", "proto_icmp"
    ],
    "instant_only": [
        "flow_duration", "flow_bytes_per_sec", "flow_pkts_per_sec", "mean_pkt_size",
        "payload_byte_ratio", "pkt_count_ratio", "tcp_syn_ratio",
        "proto_tcp", "proto_udp", "proto_icmp", "proto_other"
    ],
    "instant_temporal": [
        "flow_duration", "flow_bytes_per_sec", "flow_pkts_per_sec", "mean_pkt_size",
        "payload_byte_ratio", "pkt_count_ratio", "tcp_syn_ratio",
        "proto_tcp", "proto_udp", "proto_icmp", "proto_other",
        "temporal_iat_mean", "temporal_iat_cv", "temporal_flow_rate_ewma",
        "temporal_byte_rate_ewma", "temporal_syn_rate_ewma"
    ],
    "instant_behavioral": [
        "flow_duration", "flow_bytes_per_sec", "flow_pkts_per_sec", "mean_pkt_size",
        "payload_byte_ratio", "pkt_count_ratio", "tcp_syn_ratio",
        "proto_tcp", "proto_udp", "proto_icmp", "proto_other",
        "behavioral_dst_diversity", "behavioral_port_entropy", "behavioral_fanout_ratio",
        "behavioral_unanswered_ratio", "behavioral_src_activity_ewma"
    ],
    "full_multilevel": CANONICAL_18_FEATURE_NAMES,
}


def materialize_dataset(
    dataset_name: str, adapter, sample_limit: int = 7000, output_dir: Path = Path("data/processed/stage3")
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    print(f"\n==========================================================================")
    print(f"=== MATERIALIZING STAGE 3 DATASET: {dataset_name} ===")
    print(f"==========================================================================")
    
    t0 = time.time()
    flow_gen = adapter.stream_canonical_flows(chunksize=50000)
    
    # Collect targeted dual-class flows (2000 Benign, 5000 Attack) to guarantee valid training in all datasets
    target_benign = 2000
    target_attack = 5000
    benign = []
    attack = []
    
    max_flows_scanned = 0
    for f in flow_gen:
        max_flows_scanned += 1
        if f.label == 0 and len(benign) < target_benign:
            benign.append(f)
        elif f.label == 1 and len(attack) < target_attack:
            attack.append(f)
        if (len(benign) >= target_benign and len(attack) >= target_attack) or max_flows_scanned >= 150000:
            break

    # Chronological partition within each class (60% Train, 20% Val, 20% Test)
    tr_b, v_b, te_b = benign[:int(len(benign)*0.6)], benign[int(len(benign)*0.6):int(len(benign)*0.8)], benign[int(len(benign)*0.8):]
    tr_a, v_a, te_a = attack[:int(len(attack)*0.6)], attack[int(len(attack)*0.6):int(len(attack)*0.8)], attack[int(len(attack)*0.8):]

    train_flows = sorted(tr_b + tr_a, key=lambda f: f.timestamp_start)
    val_flows = sorted(v_b + v_a, key=lambda f: f.timestamp_start)
    test_flows = sorted(te_b + te_a, key=lambda f: f.timestamp_start)

    n_total = len(train_flows) + len(val_flows) + len(test_flows)
    print(f"Total flows ingested: {n_total} in {time.time() - t0:.2f}s")
    print(f"Chronological Splits -> Train: {len(train_flows)} (Benign: {sum(1 for f in train_flows if f.label==0)}, Attack: {sum(1 for f in train_flows if f.label==1)}), "
          f"Val: {len(val_flows)} (Benign: {sum(1 for f in val_flows if f.label==0)}, Attack: {sum(1 for f in val_flows if f.label==1)}), "
          f"Test: {len(test_flows)} (Benign: {sum(1 for f in test_flows if f.label==0)}, Attack: {sum(1 for f in test_flows if f.label==1)})")

    builder = CanonicalFlowBuilder(alpha=0.1, window_seconds=30.0)

    def extract_split(split_flows: list, split_name: str) -> pd.DataFrame:
        # Strict boundary state reset!
        builder.reset_state()
        rows = []
        for flow in split_flows:
            feat_dict = builder.instant_extractor.extract(flow)
            feat_dict.update(builder.temporal_extractor.extract_and_update(flow))
            feat_dict.update(builder.behavioral_extractor.extract_and_update(flow))
            
            # Metadata
            feat_dict["dataset"] = dataset_name
            feat_dict["split"] = split_name
            feat_dict["timestamp_start"] = flow.timestamp_start
            feat_dict["label"] = flow.label
            feat_dict["attack_category"] = flow.attack_category
            rows.append(feat_dict)
        return pd.DataFrame(rows)

    df_train = extract_split(train_flows, "train")
    df_val = extract_split(val_flows, "val")
    df_test = extract_split(test_flows, "test")

    # Save materialized parquet splits
    ds_dir = output_dir / dataset_name
    ds_dir.mkdir(parents=True, exist_ok=True)
    df_train.to_parquet(ds_dir / "train.parquet", index=False)
    df_val.to_parquet(ds_dir / "val.parquet", index=False)
    df_test.to_parquet(ds_dir / "test.parquet", index=False)
    print(f"Saved materialized splits to {ds_dir}")

    return df_train, df_val, df_test


def run_stage3_audit():
    raw_dir = Path("data/raw")
    output_dir = Path("data/processed/stage3")
    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    adapters = [
        ("ToN-IoT", ToNIoTAdapter(raw_dir / "ToN-IoT")),
        ("Edge-IIoTset", EdgeIIoTsetAggregatorAdapter(raw_dir / "Edge-IIoTset")),
        ("NF-ToN-IoT-v2", NFToNIoTAdapter(raw_dir / "NF-ToN-IoT-v2")),
        ("CICIoT2023", CICIoT2023Adapter(raw_dir / "CICIOT23")),
    ]

    dataset_dfs = {}
    stats_list = []
    mi_list = []

    for name, adapter in adapters:
        df_tr, df_v, df_te = materialize_dataset(name, adapter, sample_limit=10000, output_dir=output_dir)
        full_df = pd.concat([df_tr, df_v, df_te], ignore_index=True)
        dataset_dfs[name] = full_df

        # 1. Distribution stats per split
        tr_stats = compute_distribution_statistics(df_tr, CANONICAL_18_FEATURE_NAMES)
        tr_stats["dataset"] = name
        tr_stats["split"] = "train"
        stats_list.append(tr_stats)

        # 2. Mutual Information (Training split only)
        mi_df = compute_mutual_information(df_tr, CANONICAL_18_FEATURE_NAMES, label_col="label")
        mi_df["dataset"] = name
        mi_list.append(mi_df)

    combined_stats = pd.concat(stats_list, ignore_index=True)
    combined_stats.to_csv(reports_dir / "stage3_feature_statistics.csv", index=False)

    combined_mi = pd.concat(mi_list, ignore_index=True)
    combined_mi.to_csv(reports_dir / "stage3_mutual_information.csv", index=False)

    # 3. Cross-Domain Distribution Shift (KS test & Wasserstein distance)
    names = list(dataset_dfs.keys())
    shift_list = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            s_name, t_name = names[i], names[j]
            s_df, t_df = dataset_dfs[s_name], dataset_dfs[t_name]
            shift_df = compute_distribution_shift(s_df, t_df, CANONICAL_18_FEATURE_NAMES)
            shift_df["source_dataset"] = s_name
            shift_df["target_dataset"] = t_name
            shift_list.append(shift_df)

    combined_shift = pd.concat(shift_list, ignore_index=True)
    combined_shift.to_csv(reports_dir / "stage3_distribution_shift.csv", index=False)

    # 4. Correlation & VIF on reference dataset (ToN-IoT)
    ref_df = dataset_dfs["ToN-IoT"]
    pearson_df, spearman_df = compute_correlation(ref_df, CANONICAL_18_FEATURE_NAMES)
    pearson_df.to_csv(reports_dir / "stage3_correlation.csv")

    vif_df = compute_vif(ref_df, CANONICAL_18_FEATURE_NAMES)
    vif_df.to_csv(reports_dir / "stage3_vif.csv", index=False)

    print("\n==========================================================================")
    print("=== STAGE 3 STATISTICAL AUDIT COMPLETED ===")
    print("==========================================================================")
    print(f"Generated Audit Reports in {reports_dir}:")
    print("  - stage3_feature_statistics.csv")
    print("  - stage3_distribution_shift.csv")
    print("  - stage3_mutual_information.csv")
    print("  - stage3_correlation.csv")
    print("  - stage3_vif.csv")


if __name__ == "__main__":
    run_stage3_audit()
