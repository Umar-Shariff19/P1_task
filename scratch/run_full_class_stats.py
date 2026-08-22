import os
import pandas as pd
import numpy as np
from sklearn.feature_selection import mutual_info_classif

print("=== STRATIFIED EMPIRICAL AUDIT: EDGE-IIOTSET & TON-IOT ===")

# 1. ToN-IoT Row Indices
df_ton_all = pd.read_csv("data/raw/ToN-IoT/train_test_network.csv", usecols=['label'])
ton_y_all = pd.to_numeric(df_ton_all['label'], errors='coerce').fillna(-1).values
ben_idx = np.where(ton_y_all == 0)[0]
att_idx = np.where(ton_y_all == 1)[0]

print(f"Total ToN-IoT Rows: {len(df_ton_all)}")
print(f"Benign Count: {len(ben_idx)} | Attack Count: {len(att_idx)}")

ton_sample_idx = list(ben_idx[:20000]) + list(att_idx[:20000])
df_ton = pd.read_csv("data/raw/ToN-IoT/train_test_network.csv").iloc[ton_sample_idx]

# 2. Edge-IIoTset Row Indices
df_edge_all = pd.read_csv("data/raw/Edge-IIoTset/Edge-IIoTset dataset/Selected dataset for ML and DL/DNN-EdgeIIoT-Dataset.csv", usecols=['Attack_label'], low_memory=False)
edge_y_all = pd.to_numeric(df_edge_all['Attack_label'], errors='coerce').fillna(-1).values
e_ben_idx = np.where(edge_y_all == 0)[0]
e_att_idx = np.where(edge_y_all == 1)[0]

print(f"Total Edge-IIoTset Rows: {len(df_edge_all)}")
print(f"Benign Count: {len(e_ben_idx)} | Attack Count: {len(e_att_idx)}")

edge_sample_idx = list(e_ben_idx[:20000]) + list(e_att_idx[:20000])
df_edge = pd.read_csv("data/raw/Edge-IIoTset/Edge-IIoTset dataset/Selected dataset for ML and DL/DNN-EdgeIIoT-Dataset.csv", low_memory=False).iloc[edge_sample_idx]

# Convert Edge-IIoTset numeric columns safely
def safe_num(series):
    return pd.to_numeric(series, errors='coerce').fillna(0.0).values

# Feature Construction
# Edge-IIoTset
edge_dur = safe_num(df_edge['udp.time_delta'])
edge_src_b = safe_num(df_edge['tcp.len'])
edge_dst_b = safe_num(df_edge['http.content_length'])
edge_src_p = np.ones(len(df_edge))
edge_dst_p = (safe_num(df_edge['tcp.flags.ack']) > 0).astype(float)
edge_srcport = safe_num(df_edge['tcp.srcport'])
edge_dstport = safe_num(df_edge['tcp.dstport'])
edge_udpport = safe_num(df_edge['udp.port'])
edge_icmpcksum = safe_num(df_edge['icmp.checksum'])

edge_p_tcp = ((edge_srcport > 0) | (edge_dstport > 0)).astype(float)
edge_p_udp = (edge_udpport > 0).astype(float)
edge_p_icmp = (edge_icmpcksum > 0).astype(float)
edge_wk_port = ((edge_dstport < 1024) & (edge_dstport > 0)).astype(float)
edge_y = pd.to_numeric(df_edge['Attack_label'], errors='coerce').fillna(0).astype(int).values

# ToN-IoT
ton_dur = safe_num(df_ton['duration'])
ton_src_b = safe_num(df_ton['src_bytes'])
ton_dst_b = safe_num(df_ton['dst_bytes'])
ton_src_p = safe_num(df_ton['src_pkts'])
ton_dst_p = safe_num(df_ton['dst_pkts'])
ton_dstport = safe_num(df_ton['dst_port'])
ton_proto = df_ton['proto'].astype(str).str.lower().values

ton_p_tcp = (ton_proto == 'tcp').astype(float)
ton_p_udp = (ton_proto == 'udp').astype(float)
ton_p_icmp = (ton_proto == 'icmp').astype(float)
ton_wk_port = (ton_dstport < 1024).astype(float)
ton_y = pd.to_numeric(df_ton['label'], errors='coerce').fillna(0).astype(int).values

feature_names = [
    'duration', 'src_bytes', 'dst_bytes', 'src_pkts', 'dst_pkts',
    'proto_tcp', 'proto_udp', 'proto_icmp', 'is_well_known_port'
]

X_edge = pd.DataFrame({
    'duration': edge_dur, 'src_bytes': edge_src_b, 'dst_bytes': edge_dst_b,
    'src_pkts': edge_src_p, 'dst_pkts': edge_dst_p, 'proto_tcp': edge_p_tcp,
    'proto_udp': edge_p_udp, 'proto_icmp': edge_p_icmp, 'is_well_known_port': edge_wk_port
})

X_ton = pd.DataFrame({
    'duration': ton_dur, 'src_bytes': ton_src_b, 'dst_bytes': ton_dst_b,
    'src_pkts': ton_src_p, 'dst_pkts': ton_dst_p, 'proto_tcp': ton_p_tcp,
    'proto_udp': ton_p_udp, 'proto_icmp': ton_p_icmp, 'is_well_known_port': ton_wk_port
})

print("\n============================================================")
print("=== EXACT SIDE-BY-SIDE STATISTICAL TABLE (TEST 1) ===")
print("============================================================\n")

def get_stats_row(s, name, dataset):
    q25, q50, q75 = np.percentile(s, [25, 50, 75])
    return {
        'Dataset': dataset,
        'Feature': name,
        'Min': round(float(s.min()), 2),
        'Max': round(float(s.max()), 2),
        'Median': round(float(q50), 2),
        'Mean': round(float(s.mean()), 2),
        'Std': round(float(s.std()), 2),
        '%Null': round(float(s.isna().mean() * 100), 1),
        '%Zero': round(float((s == 0).mean() * 100), 1),
        'Q25': round(float(q25), 2),
        'Q75': round(float(q75), 2)
    }

stats_list = []
for fn in feature_names:
    stats_list.append(get_stats_row(X_edge[fn], fn, 'Edge-IIoTset'))
    stats_list.append(get_stats_row(X_ton[fn], fn, 'ToN-IoT'))

df_stats = pd.DataFrame(stats_list)
print(df_stats.to_string(index=False))

print("\n============================================================")
print("=== CLASS-WISE MEDIANS & COHEN'S D SIGNAL STRENGTH (TEST 4) ===")
print("============================================================\n")

print(f"{'Feature':<20} | {'Edge Benign':<12} {'Edge Att':<12} {'Edge d':<8} | {'ToN Benign':<12} {'ToN Att':<12} {'ToN d':<8}")
print("-" * 95)

for fn in feature_names:
    eb = np.log1p(X_edge[fn][edge_y == 0])
    ea = np.log1p(X_edge[fn][edge_y == 1])
    tb = np.log1p(X_ton[fn][ton_y == 0])
    ta = np.log1p(X_ton[fn][ton_y == 1])
    
    ed = (ea.mean() - eb.mean()) / np.sqrt((ea.std()**2 + eb.std()**2) / 2 + 1e-9)
    td = (ta.mean() - tb.mean()) / np.sqrt((ta.std()**2 + tb.std()**2) / 2 + 1e-9)
    
    print(f"{fn:<20} | {np.median(eb):<12.2f} {np.median(ea):<12.2f} {ed:<+8.3f} | {np.median(tb):<12.2f} {np.median(ta):<12.2f} {td:<+8.3f}")

print("\n============================================================")
print("=== MUTUAL INFORMATION SIGNAL STRENGTH ===")
print("============================================================\n")

mi_edge = mutual_info_classif(X_edge, edge_y, random_state=42)
mi_ton = mutual_info_classif(X_ton, ton_y, random_state=42)

for fn, me, mt in zip(feature_names, mi_edge, mi_ton):
    print(f"  {fn:<20} | Edge Mutual Info: {me:.4f} | ToN Mutual Info: {mt:.4f}")

