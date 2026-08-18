from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import psutil

from iot_ids.data.adapters import build_default_adapters
from iot_ids.data.cache import cache_fingerprint
from iot_ids.features.canonical.builder import build_canonical_features
from iot_ids.features.temporal.causal import add_causal_rolling_count
from iot_ids.features.behavioral.network import add_historical_destination_diversity


def materialize_dataset(
    dataset: str,
    data_root: Path,
    output_root: Path,
    chunksize: int = 250_000,
    debug_rows_per_file: int | None = None,
    schema_version: str = "raw-schema-v1",
    label_mapping_version: str = "label-taxonomy-v1",
    feature_version: str = "canonical-features-v1",
    force: bool = False,
) -> dict[str, object]:
    adapters = {adapter.name: adapter for adapter in build_default_adapters(data_root)}
    adapter = adapters[dataset]
    files = adapter.discover_files()
    fingerprint = cache_fingerprint(
        files,
        schema_version,
        label_mapping_version,
        feature_version,
        {"chunksize": chunksize, "debug_rows_per_file": debug_rows_per_file},
    )
    out_dir = output_root / dataset / fingerprint
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"
    if not force:
        cached = load_valid_manifest(manifest_path, out_dir)
        if cached is not None:
            cached["cache_status"] = "reused"
            return cached

    start = time.perf_counter()
    process = psutil.Process()
    rows = 0
    partitions = 0
    peak_rss_bytes = process.memory_info().rss
    for stale in out_dir.glob("part-*.parquet"):
        stale.unlink()
    # Cross-chunk state for temporal/behavioral features (Issue 1 & 2 fix)
    temporal_state: dict[str, int] = {}
    behavioral_state: dict[str, list[str]] = {}
    for file_index, path in enumerate(files):
        reader = pd.read_csv(path, chunksize=chunksize, low_memory=False, skipinitialspace=True)
        remaining = debug_rows_per_file

        for chunk_index, chunk in enumerate(reader):
            if remaining is not None:
                if remaining <= 0:
                    break
                chunk = chunk.head(remaining)
                remaining -= len(chunk)
            features = build_canonical_features(dataset, chunk, source_path=path)
            
            # Phase 2: Temporal (Level 2)
            # We attempt to create a causal rolling count grouped by source_host, ordered by timestamp
            if "source_host" in features.columns and "timestamp_start" in features.columns:
                features, temporal_state = add_causal_rolling_count(
                    features, 
                    group_col="source_host", 
                    order_col="timestamp_start", 
                    output_col="temporal_causal_count", 
                    window=100,
                    prior_counts=temporal_state,
                )
            else:
                features["temporal_causal_count"] = pd.NA

            # Phase 3: Behavioral (Level 3)
            # We attempt to create a destination diversity feature
            if "source_host" in features.columns and "destination_host" in features.columns:
                features, behavioral_state = add_historical_destination_diversity(
                    features,
                    source_col="source_host",
                    destination_col="destination_host",
                    output_col="behavioral_dest_diversity",
                    window=50,
                    prior_history=behavioral_state,
                )
            else:
                features["behavioral_dest_diversity"] = pd.NA

            target = out_dir / f"part-{file_index:04d}-{chunk_index:04d}.parquet"
            features.to_parquet(target, index=False)
            rows += len(features)
            partitions += 1
            peak_rss_bytes = max(peak_rss_bytes, process.memory_info().rss)

    elapsed = time.perf_counter() - start
    manifest = {
        "dataset": dataset,
        "fingerprint": fingerprint,
        "rows": rows,
        "partitions": partitions,
        "elapsed_seconds": elapsed,
        "rows_per_second": rows / elapsed if elapsed else None,
        "peak_rss_bytes": peak_rss_bytes,
        "output_bytes": sum(path.stat().st_size for path in out_dir.glob("part-*.parquet")),
        "debug_rows_per_file": debug_rows_per_file,
        "schema_version": schema_version,
        "label_mapping_version": label_mapping_version,
        "feature_version": feature_version,
        "source_files": [str(path) for path in files],
        "complete": True,
        "cache_status": "built",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def load_valid_manifest(manifest_path: Path, out_dir: Path) -> dict[str, object] | None:
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    parquet_count = len(list(out_dir.glob("part-*.parquet")))
    if not manifest.get("complete"):
        return None
    if parquet_count != manifest.get("partitions"):
        return None
    if int(manifest.get("rows", 0)) <= 0:
        return None
    return manifest
