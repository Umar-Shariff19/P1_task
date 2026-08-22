import pandas as pd
import numpy as np

print("=== DEEP SEMANTIC OVERLAP ANALYSIS: Edge-IIoTset vs ToN_IoT Network ===")

# Load sample of ToN-IoT
ton_path = "data/raw/ToN-IoT/train_test_network.csv"
df_ton = pd.read_csv(ton_path, nrows=1000)

# Load sample of Edge-IIoTset
edge_path = "data/raw/Edge-IIoTset/Edge-IIoTset dataset/Selected dataset for ML and DL/DNN-EdgeIIoT-Dataset.csv"
df_edge = pd.read_csv(edge_path, nrows=1000, low_memory=False)

print("\n--- ToN-IoT Features & Types ---")
for col in df_ton.columns:
    sample_val = df_ton[col].iloc[0]
    print(f"  {col:<22} | Type: {str(df_ton[col].dtype):<10} | Sample: {sample_val}")

print("\n--- Edge-IIoTset Features & Types ---")
for col in df_edge.columns:
    sample_val = df_edge[col].iloc[0]
    print(f"  {col:<28} | Type: {str(df_edge[col].dtype):<10} | Sample: {sample_val}")

