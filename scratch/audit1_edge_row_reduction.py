import os
from pathlib import Path
import pandas as pd

print("============================================================")
print("=== AUDIT 1: EDGE-IIOTSET ROW REDUCTION FORENSIC TRACE ===")
print("============================================================\n")

data_root = Path("data/raw/Edge-IIoTset")
csv_files = sorted(data_root.rglob("*.csv"))

print(f"Total CSV Files Found under {data_root}: {len(csv_files)}")
for p in csv_files:
    size_mb = p.stat().st_size / (1024 * 1024)
    print(f"  - {p.relative_to(data_root)} ({size_mb:.2f} MB)")

# Inspect adapter discovery logic
from iot_ids.data.adapters.edge_iiotset import EdgeIIoTsetAdapter
adapter = EdgeIIoTsetAdapter(data_root)
discovered = adapter.discover_files()

print(f"\nAdapter Discovered Files ({len(discovered)}):")
for p in discovered:
    size_mb = p.stat().st_size / (1024 * 1024)
    print(f"  -> Discovered: {p.relative_to(data_root)} ({size_mb:.2f} MB)")

# Read row counts of discovered files vs all CSV files
print("\nCounting rows in each CSV file:")
for p in csv_files:
    # Read row count efficiently
    with open(p, 'rb') as f:
        num_lines = sum(1 for _ in f) - 1
    print(f"  File: {p.name:<45} | Row Count: {num_lines:,}")

