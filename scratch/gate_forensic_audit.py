import os
import glob
import pandas as pd
import numpy as np

print("============================================================")
print("=== DEEP READ-ONLY FORENSIC AUDIT: Edge-IIoTset & ToN-IoT ===")
print("============================================================\n")

# 1. Edge-IIoTset Forensic Inspection
print("--- GATE 1A: Edge-IIoTset Raw Schema & Column Semantics ---")
edge_main = "data/raw/Edge-IIoTset/Edge-IIoTset dataset/Selected dataset for ML and DL/DNN-EdgeIIoT-Dataset.csv"
if os.path.exists(edge_main):
    print(f"Main CSV Path: {edge_main}")
    print(f"File Size: {os.path.getsize(edge_main) / (1024*1024):.2f} MB")
    
    # Read sample
    df_edge = pd.read_csv(edge_main, nrows=2000, low_memory=False)
    print(f"Total Columns ({len(df_edge.columns)}):")
    print(list(df_edge.columns))
    
    # Check null/zero rates for key candidate columns
    print("\nKey Candidate Columns Sample & Null Rate:")
    key_edge_cols = [
        'frame.time', 'ip.src_host', 'ip.dst_host', 'tcp.srcport', 'tcp.dstport',
        'udp.port', 'tcp.len', 'tcp.flags', 'tcp.connection.syn', 'tcp.connection.ack',
        'tcp.connection.fin', 'tcp.connection.rst', 'udp.time_delta', 'icmp.checksum',
        'http.request.method', 'mqtt.topic', 'mbtcp.len', 'Attack_label', 'Attack_type'
    ]
    for col in key_edge_cols:
        if col in df_edge.columns:
            null_cnt = df_edge[col].isna().sum()
            zero_cnt = (df_edge[col] == 0).sum() if df_edge[col].dtype in ['int64', 'float64'] else (df_edge[col] == '0').sum()
            print(f"  {col:<26} | type: {str(df_edge[col].dtype):<8} | nulls: {null_cnt:<4} | zeros: {zero_cnt:<4} | sample: {df_edge[col].iloc[0]}")
        else:
            print(f"  MISSING COLUMN: {col}")

print("\n------------------------------------------------------------\n")

# 2. ToN-IoT Network Forensic Inspection
print("--- GATE 1B: ToN-IoT Network Raw Schema & Column Semantics ---")
ton_main = "data/raw/ToN-IoT/train_test_network.csv"
if os.path.exists(ton_main):
    print(f"Main CSV Path: {ton_main}")
    print(f"File Size: {os.path.getsize(ton_main) / (1024*1024):.2f} MB")
    
    df_ton = pd.read_csv(ton_main, nrows=2000)
    print(f"Total Columns ({len(df_ton.columns)}):")
    print(list(df_ton.columns))
    
    print("\nKey Candidate Columns Sample & Null Rate:")
    key_ton_cols = [
        'src_ip', 'src_port', 'dst_ip', 'dst_port', 'proto', 'service',
        'duration', 'src_bytes', 'dst_bytes', 'conn_state', 'src_pkts',
        'src_ip_bytes', 'dst_pkts', 'dst_ip_bytes', 'http_method', 'dns_query',
        'ssl_version', 'label', 'type'
    ]
    for col in key_ton_cols:
        if col in df_ton.columns:
            null_cnt = df_ton[col].isna().sum()
            dash_cnt = (df_ton[col] == '-').sum() if df_ton[col].dtype == 'object' else 0
            print(f"  {col:<22} | type: {str(df_ton[col].dtype):<8} | nulls: {null_cnt:<4} | dashes: {dash_cnt:<4} | sample: {df_ton[col].iloc[0]}")
        else:
            print(f"  MISSING COLUMN: {col}")

