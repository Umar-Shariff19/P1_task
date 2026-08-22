import json
from pathlib import Path
import pandas as pd
import numpy as np

print("============================================================")
print("=== AUDIT 2: SPLIT / ENTITY / FEATURE LEAKAGE AUDIT ===")
print("============================================================\n")

base_dir = Path("data/processed/final")
datasets = ["Edge-IIoTset", "ToN-IoT"]

audit_table = []

for ds in datasets:
    ds_dir = base_dir / ds
    target_dir = [d for d in ds_dir.iterdir() if d.is_dir()][0]
    splits_dir = target_dir / "splits"

    train_df = pd.read_parquet(splits_dir / "train.parquet")
    val_df = pd.read_parquet(splits_dir / "val.parquet")
    test_df = pd.read_parquet(splits_dir / "test.parquet")

    # 1. Exact Row Overlap Check (via SHA256 of common feature string)
    def row_hashes(df):
        cols = [c for c in df.columns if c not in ["source_file", "timestamp"]]
        return set(pd.util.hash_pandas_object(df[cols], index=False))

    tr_h = row_hashes(train_df)
    val_h = row_hashes(val_df)
    tst_h = row_hashes(test_df)

    ov_tr_val = len(tr_h.intersection(val_h))
    ov_tr_tst = len(tr_h.intersection(tst_h))
    ov_val_tst = len(val_h.intersection(tst_h))

    # 2. Source-IP Overlap
    tr_ips = set(train_df["source_host"].dropna().unique())
    val_ips = set(val_df["source_host"].dropna().unique())
    tst_ips = set(test_df["source_host"].dropna().unique())

    ip_ov_tr_val = len(tr_ips.intersection(val_ips))
    ip_ov_tr_tst = len(tr_ips.intersection(tst_ips))

    # 3. Attack Family Representation
    tr_cats = set(train_df["attack_category"].unique())
    val_cats = set(val_df["attack_category"].unique())
    tst_cats = set(test_df["attack_category"].unique())

    cats_missing_val = tr_cats - val_cats
    cats_missing_tst = tr_cats - tst_cats

    print(f"--- Dataset: {ds} ---")
    print(f"  Rows -> Train: {len(train_df):,}, Val: {len(val_df):,}, Test: {len(test_df):,}")
    print(f"  Exact Row Hash Overlap -> Train-Val: {ov_tr_val}, Train-Test: {ov_tr_tst}, Val-Test: {ov_val_tst}")
    print(f"  Source IP Overlap      -> Train-Val: {ip_ov_tr_val}, Train-Test: {ip_ov_tr_tst}")
    print(f"  Attack Categories      -> Train: {len(tr_cats)}, Val: {len(val_cats)}, Test: {len(tst_cats)}")
    print(f"  Missing in Val: {cats_missing_val if cats_missing_val else 'None (All present)'}")
    print(f"  Missing in Test: {cats_missing_tst if cats_missing_tst else 'None (All present)'}")

    # Check ML input features (ensure IP addresses & labels are NOT model features)
    common_cols = [
        "duration", "src_bytes", "src_pkts", "dst_pkts",
        "proto_tcp", "proto_udp", "proto_icmp", "is_well_known_port"
    ]
    raw_ip_in_model = any(c in common_cols for c in ["source_host", "destination_host", "src_ip", "dst_ip", "ip.src_host", "ip.dst_host"])
    label_in_model = any(c in common_cols for c in ["label", "attack_category", "Attack_label", "type"])

    print(f"  Raw IP in Model Input: {raw_ip_in_model}")
    print(f"  Label Leakage in Model Input: {label_in_model}")
    print()

