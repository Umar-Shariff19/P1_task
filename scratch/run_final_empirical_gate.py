import os
import pandas as pd
import numpy as np
from sklearn.feature_selection import mutual_info_classif

print("============================================================")
print("=== FINAL EMPIRICAL FEASIBILITY GATE: RAW DATA STATS ===")
print("============================================================\n")

# Load Edge-IIoTset sample
edge_path = "data/raw/Edge-IIoTset/Edge-IIoTset dataset/Selected dataset for ML and DL/DNN-EdgeIIoT-Dataset.csv"
print("Loading Edge-IIoTset sample (50,000 rows)...")
df_edge = pd.read_csv(edge_path, nrows=50000, low_memory=False)

# Load ToN-IoT sample
ton_path = "data/raw/ToN-IoT/train_test_network.csv"
print("Loading ToN-IoT sample (50,000 rows)...")
df_ton = pd.read_csv(ton_path, nrows=50000)

print("\n--- Constructing Proposed F_common Candidates ---")

# 1. Edge-IIoTset Feature Construction
# duration: udp.time_delta
edge_dur = df_edge['udp.time_delta'].astype(float).fillna(0.0)
# src_bytes: tcp.len
edge_src_b = df_edge['tcp.len'].astype(float).fillna(0.0)
# dst_bytes: http.content_length or 0 for packet-level frame
edge_dst_b = df_edge['http.content_length'].astype(float).fillna(0.0)
# src_pkts: 1.0 per frame (packet record)
edge_src_p = np.ones(len(df_edge))
# dst_pkts: 0.0 or 1.0 (response frame indicator)
edge_dst_p = (df_edge['tcp.flags.ack'].fillna(0.0) > 0).astype(float)
# proto_tcp: tcp.srcport > 0 or tcp.dstport > 0 or tcp.flags > 0
edge_p_tcp = ((df_edge['tcp.srcport'].fillna(0) > 0) | (df_edge['tcp.dstport'].fillna(0) > 0)).astype(float)
# proto_udp: udp.port > 0
edge_p_udp = (df_edge['udp.port'].fillna(0) > 0).astype(float)
# proto_icmp: icmp.checksum > 0
edge_p_icmp = (df_edge['icmp.checksum'].fillna(0) > 0).astype(float)
# is_well_known_port: dstport < 1024
edge_wk_port = ((df_edge['tcp.dstport'].fillna(0) < 1024) & (df_edge['tcp.dstport'].fillna(0) > 0)).astype(float)
edge_target = df_edge['Attack_label'].astype(int)

# 2. ToN-IoT Feature Construction
ton_dur = df_ton['duration'].astype(float).fillna(0.0)
ton_src_b = df_ton['src_bytes'].astype(float).fillna(0.0)
ton_dst_b = df_ton['dst_bytes'].astype(float).fillna(0.0)
ton_src_p = df_ton['src_pkts'].astype(float).fillna(0.0)
ton_dst_p = df_ton['dst_pkts'].astype(float).fillna(0.0)
ton_p_tcp = (df_ton['proto'].str.lower() == 'tcp').astype(float)
ton_p_udp = (df_ton['proto'].str.lower() == 'udp').astype(float)
ton_p_icmp = (df_ton['proto'].str.lower() == 'icmp').astype(float)
ton_wk_port = (df_ton['dst_port'].fillna(0) < 1024).astype(float)
ton_target = df_ton['label'].astype(int)

feature_names = [
    'duration', 'src_bytes', 'dst_bytes', 'src_pkts', 'dst_pkts',
    'proto_tcp', 'proto_udp', 'proto_icmp', 'is_well_known_port'
]

edge_feats = pd.DataFrame({
    'duration': edge_dur, 'src_bytes': edge_src_b, 'dst_bytes': edge_dst_b,
    'src_pkts': edge_src_p, 'dst_pkts': edge_dst_p, 'proto_tcp': edge_p_tcp,
    'proto_udp': edge_p_udp, 'proto_icmp': edge_p_icmp, 'is_well_known_port': edge_wk_port
})

ton_feats = pd.DataFrame({
    'duration': ton_dur, 'src_bytes': ton_src_b, 'dst_bytes': ton_dst_b,
    'src_pkts': ton_src_p, 'dst_pkts': ton_dst_p, 'proto_tcp': ton_p_tcp,
    'proto_udp': ton_p_udp, 'proto_icmp': ton_p_icmp, 'is_well_known_port': ton_wk_port
})

def calc_stats(s):
    q25, q50, q75 = np.percentile(s, [25, 50, 75])
    return {
        'min': float(s.min()),
        'max': float(s.max()),
        'median': float(q50),
        'mean': float(s.mean()),
        'std': float(s.std()),
        'pct_null': float(s.isna().mean() * 100),
        'pct_zero': float((s == 0).mean() * 100),
        'q25': float(q25),
        'q75': float(q75)
    }

print("\n============================================================")
print("=== TEST 1: SIDE-BY-SIDE STATISTICAL COMPARISON ===")
print("============================================================\n")

for fn in feature_names:
    es = calc_stats(edge_feats[fn])
    ts = calc_stats(ton_feats[fn])
    print(f"--- Feature: {fn} ---")
    print(f"  Edge-IIoTset -> min: {es['min']:.2f}, max: {es['max']:.2f}, med: {es['median']:.2f}, mean: {es['mean']:.2f}, std: {es['std']:.2f}, %0: {es['pct_zero']:.1f}%, q25: {es['q25']:.2f}, q75: {es['q75']:.2f}")
    print(f"  ToN-IoT      -> min: {ts['min']:.2f}, max: {ts['max']:.2f}, med: {ts['median']:.2f}, mean: {ts['mean']:.2f}, std: {ts['std']:.2f}, %0: {ts['pct_zero']:.1f}%, q25: {ts['q25']:.2f}, q75: {ts['q75']:.2f}")
    print()

print("\n============================================================")
print("=== TEST 4: CROSS-DOMAIN UNIVARIATE SIGNAL STRENGTH ===")
print("============================================================\n")

print("Class-Wise Medians & Effect Sizes (Cohen's d on Log1p transformed features):")

for fn in feature_names:
    e_ben = np.log1p(edge_feats[fn][edge_target == 0])
    e_att = np.log1p(edge_feats[fn][edge_target == 1])
    t_ben = np.log1p(ton_feats[fn][ton_target == 0])
    t_att = np.log1p(ton_feats[fn][ton_target == 1])
    
    # Cohen's d for Edge
    e_d = (e_att.mean() - e_ben.mean()) / np.sqrt((e_att.std()**2 + e_ben.std()**2) / 2 + 1e-9)
    # Cohen's d for ToN
    t_d = (t_att.mean() - t_ben.mean()) / np.sqrt((t_att.std()**2 + t_ben.std()**2) / 2 + 1e-9)
    
    print(f"Feature: {fn:<20} | Edge Benign Med: {np.median(e_ben):.2f}, Att Med: {np.median(e_att):.2f}, Cohen's d: {e_d:+.3f} | ToN Benign Med: {np.median(t_ben):.2f}, Att Med: {np.median(t_att):.2f}, Cohen's d: {t_d:+.3f}")

