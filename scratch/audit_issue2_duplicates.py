import json
from pathlib import Path
import pandas as pd
import numpy as np

print("============================================================")
print("=== ISSUE 2 FORENSIC AUDIT: DUPLICATION & SPLIT LEAKAGE ===")
print("============================================================\n")

base_dir = Path("data/processed/final")
datasets = ["Edge-IIoTset", "ToN-IoT"]

# Core physical features (excluding labels, IPs, temporal, and behavioral)
core_features = [
    "duration", "src_bytes", "proto_tcp", "proto_udp", "proto_icmp", "is_well_known_port"
]

for ds in datasets:
    ds_dir = base_dir / ds
    target_dir = [d for d in ds_dir.iterdir() if d.is_dir()][0]
    splits_dir = target_dir / "splits"

    train_df = pd.read_parquet(splits_dir / "train.parquet")
    val_df = pd.read_parquet(splits_dir / "val.parquet")
    test_df = pd.read_parquet(splits_dir / "test.parquet")

    # Content hash excluding labels, IPs, temporal, behavioral
    def get_content_hashes(df):
        return pd.util.hash_pandas_object(df[core_features], index=False)

    tr_h = set(get_content_hashes(train_df))
    val_h = set(get_content_hashes(val_df))
    tst_h = set(get_content_hashes(test_df))

    # Exact duplicates across split pairs
    tr_val_dups = len(tr_h.intersection(val_h))
    tr_tst_dups = len(tr_h.intersection(tst_h))
    val_tst_dups = len(val_h.intersection(tst_h))

    # Total unique patterns per split
    print(f"=== Dataset: {ds} ===")
    print(f"  Train Total Rows: {len(train_df):,} | Unique Core Patterns: {len(tr_h):,}")
    print(f"  Val Total Rows:   {len(val_df):,} | Unique Core Patterns: {len(val_h):,}")
    print(f"  Test Total Rows:  {len(test_df):,} | Unique Core Patterns: {len(tst_h):,}")
    print()
    print(f"  Split Pair Duplication (Core Physical Features Only):")
    print(f"    Train <-> Val  Exact Duplicate Patterns: {tr_val_dups} / {len(val_h)} ({tr_val_dups/len(val_h)*100:.1f}% of Val patterns)")
    print(f"    Train <-> Test Exact Duplicate Patterns: {tr_tst_dups} / {len(tst_h)} ({tr_tst_dups/len(tst_h)*100:.1f}% of Test patterns)")
    print(f"    Val <-> Test   Exact Duplicate Patterns: {val_tst_dups} / {len(tst_h)} ({val_tst_dups/len(tst_h)*100:.1f}% of Test patterns)")

    # Inspect Benign vs Attack pattern duplication
    train_att = train_df[train_df['label'] == 1]
    train_ben = train_df[train_df['label'] == 0]
    test_att = test_df[test_df['label'] == 1]
    test_ben = test_df[test_df['label'] == 0]

    tr_att_h = set(get_content_hashes(train_att))
    tst_att_h = set(get_content_hashes(test_att))
    tr_ben_h = set(get_content_hashes(train_ben))
    tst_ben_h = set(get_content_hashes(test_ben))

    att_dups = len(tr_att_h.intersection(tst_att_h))
    ben_dups = len(tr_ben_h.intersection(tst_ben_h))

    print(f"\n  Attack Class Duplicate Patterns (Train <-> Test):  {att_dups} / {len(tst_att_h)}")
    print(f"  Benign Class Duplicate Patterns (Train <-> Test):  {ben_dups} / {len(tst_ben_h)}")
    print("------------------------------------------------------------\n")

