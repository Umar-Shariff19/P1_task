import os
import pandas as pd
import numpy as np

print("============================================================")
print("=== ISSUE 1 FORENSIC AUDIT: F_common RAW COLUMN PROVENANCE ===")
print("============================================================\n")

# 1. Edge-IIoTset Raw Inspection
edge_path = "data/raw/Edge-IIoTset/Edge-IIoTset dataset/Selected dataset for ML and DL/ML-EdgeIIoT-dataset.csv"
print(f"Loading Edge-IIoTset ML benchmark ({edge_path})...")
df_edge = pd.read_csv(edge_path, nrows=5000, low_memory=False)

print("\n--- Edge-IIoTset Candidate Column Properties ---")
edge_candidate_cols = [
    'udp.time_delta', 'tcp.len', 'tcp.flags.ack', 'tcp.connection.ack',
    'tcp.flags', 'tcp.srcport', 'tcp.dstport', 'udp.port', 'icmp.checksum',
    'http.content_length', 'mqtt.len'
]

for col in edge_candidate_cols:
    if col in df_edge.columns:
        s = pd.to_numeric(df_edge[col], errors='coerce')
        print(f"  {col:<24} | type: {str(df_edge[col].dtype):<8} | min: {s.min():<6.1f} | max: {s.max():<8.1f} | mean: {s.mean():<8.2f} | unique: {s.nunique()}")
    else:
        print(f"  MISSING COLUMN: {col}")

# 2. ToN-IoT Raw Inspection
ton_path = "data/raw/ToN-IoT/train_test_network.csv"
print(f"\nLoading ToN-IoT Network ({ton_path})...")
df_ton = pd.read_csv(ton_path, nrows=5000)

print("\n--- ToN-IoT Candidate Column Properties ---")
ton_candidate_cols = [
    'duration', 'src_bytes', 'dst_bytes', 'src_pkts', 'dst_pkts',
    'src_ip_bytes', 'dst_ip_bytes', 'proto', 'src_port', 'dst_port'
]

for col in ton_candidate_cols:
    if col in df_ton.columns:
        s = df_ton[col]
        if pd.api.types.is_numeric_dtype(s):
            print(f"  {col:<24} | type: {str(s.dtype):<8} | min: {s.min():<6.1f} | max: {s.max():<8.1f} | mean: {s.mean():<8.2f} | unique: {s.nunique()}")
        else:
            print(f"  {col:<24} | type: {str(s.dtype):<8} | sample: {s.iloc[0]} | unique: {s.nunique()}")
    else:
        print(f"  MISSING COLUMN: {col}")

