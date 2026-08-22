import os
import glob
import pandas as pd

print("=== ToN-IoT Detailed Inspection ===")
ton_path = "data/raw/ToN-IoT/train_test_network.csv"
if os.path.exists(ton_path):
    df_ton = pd.read_csv(ton_path, nrows=5)
    print("Columns:", list(df_ton.columns))
    print("\nFirst row:")
    for col, val in df_ton.iloc[0].items():
        print(f"  {col}: {val}")
    
    # Read types and labels distribution
    df_labels = pd.read_csv(ton_path, usecols=['type', 'label'])
    print("\nTotal Rows:", len(df_labels))
    print("\nLabel Count:")
    print(df_labels['label'].value_counts())
    print("\nType (Attack Category) Count:")
    print(df_labels['type'].value_counts())

print("\n=== Edge-IIoTset Detailed Inspection ===")
edge_path = "data/raw/Edge-IIoTset/Edge-IIoTset dataset/Selected dataset for ML and DL/DNN-EdgeIIoT-Dataset.csv"
if os.path.exists(edge_path):
    df_edge = pd.read_csv(edge_path, nrows=5, low_memory=False)
    print("Columns:", list(df_edge.columns))
    print("\nFirst row sample:")
    for col, val in list(df_edge.iloc[0].items())[:15]:
        print(f"  {col}: {val}")
    
    df_edge_labels = pd.read_csv(edge_path, usecols=['Attack_type', 'Attack_label'], low_memory=False)
    print("\nTotal Rows:", len(df_edge_labels))
    print("\nAttack_label Count:")
    print(df_edge_labels['Attack_label'].value_counts())
    print("\nAttack_type Count:")
    print(df_edge_labels['Attack_type'].value_counts())
else:
    print("Edge-IIoTset DNN file not found at path:", edge_path)

