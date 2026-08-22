import pandas as pd
import numpy as np

print("=== EDGE-IIOTSET FLOW AGGREGATION & FEATURE AUDIT ===")

edge_path = "data/raw/Edge-IIoTset/Edge-IIoTset dataset/Selected dataset for ML and DL/DNN-EdgeIIoT-Dataset.csv"
df_edge = pd.read_csv(edge_path, nrows=50000, low_memory=False)

print("Unique ip.src_host in 50k sample:", df_edge['ip.src_host'].nunique())
print("Unique ip.dst_host in 50k sample:", df_edge['ip.dst_host'].nunique())

# Check how many packets per (ip.src_host, ip.dst_host) pair
flow_groups = df_edge.groupby(['ip.src_host', 'ip.dst_host']).size()
print("\nTop 10 Flow Groups (packets per IP pair):")
print(flow_groups.head(10))

# Compute class distributions for Benign vs Attack on Edge-IIoTset
ben = df_edge[df_edge['Attack_label'] == 0]
att = df_edge[df_edge['Attack_label'] == 1]

print(f"\nSample Breakdown: {len(ben)} Benign, {len(att)} Attack")

# Check features that discriminate Benign vs Attack in Edge-IIoTset
print("\nEdge-IIoTset Feature Means (Benign vs Attack):")
for col in ['tcp.len', 'tcp.ack', 'tcp.flags', 'tcp.connection.syn', 'tcp.connection.rst', 'udp.port', 'tcp.srcport', 'tcp.dstport']:
    if col in df_edge.columns:
        b_val = ben[col].astype(float).fillna(0.0).mean()
        a_val = att[col].astype(float).fillna(0.0).mean()
        print(f"  {col:<22} | Benign Mean: {b_val:<10.2f} | Attack Mean: {a_val:<10.2f}")

print("\nToN-IoT Feature Means (Benign vs Attack):")
ton_path = "data/raw/ToN-IoT/train_test_network.csv"
df_ton = pd.read_csv(ton_path, nrows=50000)
ton_ben = df_ton[df_ton['label'] == 0]
ton_att = df_ton[df_ton['label'] == 1]
print(f"Sample Breakdown: {len(ton_ben)} Benign, {len(ton_att)} Attack")

for col in ['duration', 'src_bytes', 'dst_bytes', 'src_pkts', 'dst_pkts', 'src_port', 'dst_port']:
    if col in df_ton.columns:
        b_val = ton_ben[col].astype(float).fillna(0.0).mean()
        a_val = ton_att[col].astype(float).fillna(0.0).mean()
        print(f"  {col:<22} | Benign Mean: {b_val:<10.2f} | Attack Mean: {a_val:<10.2f}")

