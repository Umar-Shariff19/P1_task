import os
import glob
import pandas as pd

print("=== TIMESTAMP & TIME-SERIES AUDIT ACROSS ALL 5 DATASETS ===")

# 1. ToN-IoT
ton_files = glob.glob("data/raw/ToN-IoT/**/*.csv", recursive=True)
print(f"\n1. ToN-IoT Files found: {len(ton_files)}")
for f in ton_files:
    df = pd.read_csv(f, nrows=2)
    time_cols = [c for c in df.columns if any(t in c.lower() for t in ['time', 'ts', 'date', 'stime', 'ltime', 'duration', 'dur'])]
    print(f"  {os.path.basename(f)}: Time/Duration columns -> {time_cols}")
    print(f"  Columns list: {list(df.columns)}")

# 2. Edge-IIoTset
edge_files = glob.glob("data/raw/Edge-IIoTset/**/*.csv", recursive=True)
print(f"\n2. Edge-IIoTset Files found: {len(edge_files)}")
for f in edge_files[:3]:
    df = pd.read_csv(f, nrows=2, low_memory=False)
    time_cols = [c for c in df.columns if any(t in c.lower() for t in ['time', 'ts', 'date', 'stime', 'ltime', 'duration', 'dur'])]
    print(f"  {os.path.basename(f)}: Time/Duration columns -> {time_cols}")

# 3. CICIDS2017
cic_files = glob.glob("data/raw/CICIDS2017/*.csv")
print(f"\n3. CICIDS2017 Files found: {len(cic_files)}")
for f in cic_files[:3]:
    df = pd.read_csv(f, nrows=2)
    time_cols = [c for c in df.columns if any(t in c.lower() for t in ['time', 'ts', 'date', 'stime', 'ltime', 'duration', 'dur', 'timestamp'])]
    print(f"  {os.path.basename(f)}: Time/Duration columns -> {time_cols}")

# 4. BoT-IoT
bot_files = glob.glob("data/raw/BoT-IoT/*.csv")
print(f"\n4. BoT-IoT Files found: {len(bot_files)}")
for f in bot_files[:3]:
    df = pd.read_csv(f, nrows=2)
    time_cols = [c for c in df.columns if any(t in c.lower() for t in ['time', 'ts', 'date', 'stime', 'ltime', 'duration', 'dur'])]
    print(f"  {os.path.basename(f)}: Time/Duration columns -> {time_cols}")

# 5. N-BaIoT
nb_files = glob.glob("data/raw/N-BaIoT/*.csv")
print(f"\n5. N-BaIoT Files found: {len(nb_files)}")
for f in nb_files[:3]:
    df = pd.read_csv(f, nrows=2)
    time_cols = [c for c in df.columns if any(t in c.lower() for t in ['time', 'ts', 'date', 'stime', 'ltime', 'duration', 'dur'])]
    print(f"  {os.path.basename(f)}: Time/Duration columns -> {time_cols}")

