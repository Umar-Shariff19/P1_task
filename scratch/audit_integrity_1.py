import json
from pathlib import Path
import pandas as pd

print("============================================================")
print("=== AUDIT 1: FROZEN F_common CONTRACT TRACE ===")
print("============================================================\n")

schema_path = Path("configs/features/canonical_schema.json")
schema = json.loads(schema_path.read_text(encoding="utf-8"))

f_common_config = schema["profiles"]["F_COMMON"]
print(f"F_COMMON in canonical_schema.json ({len(f_common_config)} features):")
for f in f_common_config:
    print(f"  - {f}")

expected_6 = ["duration", "src_bytes", "proto_tcp", "proto_udp", "proto_icmp", "is_well_known_port"]
exact_match = (f_common_config == expected_6)
print(f"\nExact 6-Feature F_common Match: {exact_match}")

# Check if src_pkts or dst_pkts are in F_COMMON
has_src_pkts = "src_pkts" in f_common_config
has_dst_pkts = "dst_pkts" in f_common_config
has_raw_ip = any(f in f_common_config for f in ["source_host", "destination_host", "src_ip", "dst_ip"])
has_label = any(f in f_common_config for f in ["label", "attack_category"])

print(f"src_pkts in F_common: {has_src_pkts}")
print(f"dst_pkts in F_common: {has_dst_pkts}")
print(f"Raw IPs in F_common:  {has_raw_ip}")
print(f"Labels in F_common:   {has_label}")

# Verify Materialized Parquet columns
base_dir = Path("data/processed/final")
for ds in ["Edge-IIoTset", "ToN-IoT"]:
    ds_dir = base_dir / ds
    target_dir = [d for d in ds_dir.iterdir() if d.is_dir()][0]
    p_file = list(target_dir.glob("part-*.parquet"))[0]
    df_sample = pd.read_parquet(p_file)
    cols = list(df_sample.columns)
    print(f"\nDataset {ds} Materialized Parquet Columns ({len(cols)} total):")
    for c in cols:
        print(f"  - {c}")
    
    missing_f_common = [f for f in expected_6 if f not in cols]
    print(f"  Missing F_common features: {missing_f_common if missing_f_common else 'None (All 6 Present)'}")

