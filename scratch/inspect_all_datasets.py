import os
import glob
import pandas as pd
import numpy as np

print("============================================================")
print("=== SCIENTIFIC DATASET SCHEMA & TELEMETRY INSPECTION ===")
print("============================================================\n")

# 1. ToN-IoT
print("--- 1. ToN-IoT Network Dataset ---")
ton_path = "data/raw/ToN-IoT/train_test_network.csv"
if os.path.exists(ton_path):
    df_ton = pd.read_csv(ton_path, nrows=1000)
    print(f"File: {ton_path}")
    print(f"Columns ({len(df_ton.columns)}): {list(df_ton.columns)}")
    print("Sample Row:")
    print(df_ton.iloc[0].to_dict())
    
    # Check total rows efficiently
    with open(ton_path, 'r', encoding='utf-8', errors='ignore') as f:
        tot_ton = sum(1 for _ in f) - 1
    print(f"Total Rows: {tot_ton:,}")
    
    # Check label distribution on full file or sample
    df_ton_full = pd.read_csv(ton_path, usecols=['type', 'label'] if 'label' in df_ton.columns else [df_ton.columns[-1]])
    print("Label Distribution:")
    print(df_ton_full.value_counts())
else:
    print(f"FILE NOT FOUND: {ton_path}")

print("\n------------------------------------------------------------\n")

# 2. Edge-IIoTset
print("--- 2. Edge-IIoTset Dataset ---")
edge_files = glob.glob("data/raw/Edge-IIoTset/**/*.csv", recursive=True)
print(f"Found {len(edge_files)} CSV files for Edge-IIoTset.")
if edge_files:
    # Pick main dataset file if present
    main_edge = [f for f in edge_files if "Selected dataset for ML" in f or "Edge-IIoTset" in f]
    edge_sample_path = main_edge[0] if main_edge else edge_files[0]
    print(f"Sample File: {edge_sample_path}")
    df_edge = pd.read_csv(edge_sample_path, nrows=500, low_memory=False)
    print(f"Columns ({len(df_edge.columns)}): {list(df_edge.columns)}")
    print("Sample Row:")
    print(df_edge.iloc[0].to_dict())

print("\n------------------------------------------------------------\n")

# 3. CICIDS2017
print("--- 3. CICIDS2017 Dataset ---")
cic_files = glob.glob("data/raw/CICIDS2017/*.csv")
print(f"Found {len(cic_files)} CSV files for CICIDS2017.")
if cic_files:
    df_cic = pd.read_csv(cic_files[0], nrows=500)
    print(f"Sample File: {cic_files[0]}")
    print(f"Columns ({len(df_cic.columns)}): {list(df_cic.columns)}")
    print("Sample Row:")
    print(df_cic.iloc[0].to_dict())

print("\n------------------------------------------------------------\n")

# 4. BoT-IoT
print("--- 4. BoT-IoT Dataset ---")
bot_files = glob.glob("data/raw/BoT-IoT/*.csv")
print(f"Found {len(bot_files)} CSV files for BoT-IoT.")
if bot_files:
    df_bot = pd.read_csv(bot_files[0], nrows=500)
    print(f"Sample File: {bot_files[0]}")
    print(f"Columns ({len(df_bot.columns)}): {list(df_bot.columns)}")
    print("Sample Row:")
    print(df_bot.iloc[0].to_dict())

print("\n------------------------------------------------------------\n")

# 5. N-BaIoT
print("--- 5. N-BaIoT Dataset ---")
nb_files = glob.glob("data/raw/N-BaIoT/*.csv")
print(f"Found {len(nb_files)} CSV files for N-BaIoT.")
if nb_files:
    df_nb = pd.read_csv(nb_files[0], nrows=500)
    print(f"Sample File: {nb_files[0]}")
    print(f"Columns ({len(df_nb.columns)}): {list(df_nb.columns)}")
    print("Sample Row (first 10 features):")
    print({k: df_nb.iloc[0][k] for k in list(df_nb.columns)[:10]})

