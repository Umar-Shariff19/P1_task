from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from iot_ids.data.labels import nbaiot_label_from_filename


def safe_divide(numerator: pd.Series, denominator: pd.Series | float) -> pd.Series:
    result = pd.to_numeric(numerator, errors="coerce") / pd.to_numeric(denominator, errors="coerce")
    return result.replace([np.inf, -np.inf], np.nan)


def build_canonical_features(dataset: str, frame: pd.DataFrame, source_path: str | Path | None = None) -> pd.DataFrame:
    dataset_key = dataset.lower()
    if dataset_key == "cicids2017":
        out = _cicids_features(frame)
    if dataset_key == "edge-iiotset":
        out = _edge_features(frame)
    if dataset_key == "bot-iot":
        out = _bot_features(frame)
    if dataset_key == "n-baiot":
        if source_path is None:
            raise ValueError("N-BaIoT canonicalization requires source_path for filename labels.")
        out = _nbaiot_features(frame, source_path)
    if "out" not in locals():
        raise ValueError(f"Unsupported dataset: {dataset}")
    if source_path is not None:
        out["source_file"] = str(source_path)
    return out


def _base_output(frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(index=frame.index)


def _series(frame: pd.DataFrame, name: str, default: float | str | None = np.nan) -> pd.Series:
    if name in frame:
        return frame[name]
    return pd.Series(default, index=frame.index)


def _cicids_features(frame: pd.DataFrame) -> pd.DataFrame:
    out = _base_output(frame)
    duration_us = pd.to_numeric(_series(frame, "Flow Duration"), errors="coerce")
    out["duration_seconds"] = duration_us / 1_000_000.0
    out["dst_port"] = pd.to_numeric(_series(frame, "Destination Port"), errors="coerce")
    out["total_packets"] = pd.to_numeric(_series(frame, "Total Fwd Packets"), errors="coerce") + pd.to_numeric(
        _series(frame, "Total Backward Packets"), errors="coerce"
    )
    out["fwd_packets"] = pd.to_numeric(_series(frame, "Total Fwd Packets"), errors="coerce")
    out["bwd_packets"] = pd.to_numeric(_series(frame, "Total Backward Packets"), errors="coerce")
    out["total_bytes"] = pd.to_numeric(_series(frame, "Total Length of Fwd Packets"), errors="coerce") + pd.to_numeric(
        _series(frame, "Total Length of Bwd Packets"), errors="coerce"
    )
    out["fwd_bytes"] = pd.to_numeric(_series(frame, "Total Length of Fwd Packets"), errors="coerce")
    out["bwd_bytes"] = pd.to_numeric(_series(frame, "Total Length of Bwd Packets"), errors="coerce")
    out["bytes_per_second"] = pd.to_numeric(_series(frame, "Flow Bytes/s"), errors="coerce")
    out["packets_per_second"] = pd.to_numeric(_series(frame, "Flow Packets/s"), errors="coerce")
    out["packet_length_mean"] = pd.to_numeric(_series(frame, "Packet Length Mean"), errors="coerce")
    out["packet_length_std"] = pd.to_numeric(_series(frame, "Packet Length Std"), errors="coerce")
    out["packet_length_min"] = pd.to_numeric(_series(frame, "Min Packet Length"), errors="coerce")
    out["packet_length_max"] = pd.to_numeric(_series(frame, "Max Packet Length"), errors="coerce")
    out["flow_iat_mean"] = pd.to_numeric(_series(frame, "Flow IAT Mean"), errors="coerce")
    out["flow_iat_std"] = pd.to_numeric(_series(frame, "Flow IAT Std"), errors="coerce")
    out["syn_flag_count"] = pd.to_numeric(_series(frame, "SYN Flag Count"), errors="coerce")
    out["ack_flag_count"] = pd.to_numeric(_series(frame, "ACK Flag Count"), errors="coerce")
    out["rst_flag_count"] = pd.to_numeric(_series(frame, "RST Flag Count"), errors="coerce")
    out["traffic_asymmetry"] = safe_divide(out["fwd_bytes"] - out["bwd_bytes"], out["total_bytes"])
    out["packet_direction_ratio"] = safe_divide(out["fwd_packets"], out["bwd_packets"] + 1.0)
    out["canonical_label"] = np.where(_series(frame, "Label").astype(str).str.upper().eq("BENIGN"), "BENIGN", "ATTACK")
    out["raw_label"] = _series(frame, "Label").astype(str)
    return out


def _edge_features(frame: pd.DataFrame) -> pd.DataFrame:
    out = _base_output(frame)
    tcp_len = pd.to_numeric(_series(frame, "tcp.len"), errors="coerce")
    mqtt_len = pd.to_numeric(_series(frame, "mqtt.len"), errors="coerce")
    http_len = pd.to_numeric(_series(frame, "http.content_length"), errors="coerce")
    out["duration_seconds"] = pd.to_numeric(_series(frame, "udp.time_delta"), errors="coerce")
    out["src_port"] = pd.to_numeric(_series(frame, "tcp.srcport"), errors="coerce")
    out["dst_port"] = pd.to_numeric(_series(frame, "tcp.dstport"), errors="coerce").fillna(
        pd.to_numeric(_series(frame, "udp.port"), errors="coerce")
    )
    out["total_bytes"] = tcp_len.fillna(0) + mqtt_len.fillna(0) + http_len.fillna(0)
    out["packet_length_mean"] = out["total_bytes"]
    out["syn_flag_count"] = pd.to_numeric(_series(frame, "tcp.connection.syn"), errors="coerce")
    out["ack_flag_count"] = pd.to_numeric(_series(frame, "tcp.flags.ack"), errors="coerce")
    out["rst_flag_count"] = pd.to_numeric(_series(frame, "tcp.connection.rst"), errors="coerce")
    out["protocol_family"] = np.select(
        [
            _series(frame, "tcp.len").notna(),
            _series(frame, "udp.port").notna(),
            _series(frame, "icmp.checksum").notna(),
        ],
        ["tcp", "udp", "icmp"],
        default="other",
    )
    out["source_host"] = _series(frame, "ip.src_host").astype("string")
    out["destination_host"] = _series(frame, "ip.dst_host").astype("string")
    out["source_provided_delta_seconds"] = out["duration_seconds"]
    out["canonical_label"] = np.where(pd.to_numeric(_series(frame, "Attack_label"), errors="coerce").eq(0), "BENIGN", "ATTACK")
    out["raw_label"] = _series(frame, "Attack_type").astype(str)
    return out


def _bot_features(frame: pd.DataFrame) -> pd.DataFrame:
    out = _base_output(frame)
    out["duration_seconds"] = pd.to_numeric(_series(frame, "dur"), errors="coerce")
    out["protocol_family"] = _series(frame, "proto").astype("string")
    out["connection_state"] = _series(frame, "state").astype("string")
    out["src_port"] = pd.to_numeric(_series(frame, "sport"), errors="coerce")
    out["dst_port"] = pd.to_numeric(_series(frame, "dport"), errors="coerce")
    out["total_packets"] = pd.to_numeric(_series(frame, "pkts"), errors="coerce")
    out["fwd_packets"] = pd.to_numeric(_series(frame, "spkts"), errors="coerce")
    out["bwd_packets"] = pd.to_numeric(_series(frame, "dpkts"), errors="coerce")
    out["total_bytes"] = pd.to_numeric(_series(frame, "bytes"), errors="coerce")
    out["fwd_bytes"] = pd.to_numeric(_series(frame, "sbytes"), errors="coerce")
    out["bwd_bytes"] = pd.to_numeric(_series(frame, "dbytes"), errors="coerce")
    out["bytes_per_second"] = pd.to_numeric(_series(frame, "rate"), errors="coerce")
    out["packet_length_mean"] = pd.to_numeric(_series(frame, "mean"), errors="coerce")
    out["packet_length_std"] = pd.to_numeric(_series(frame, "stddev"), errors="coerce")
    out["packet_length_min"] = pd.to_numeric(_series(frame, "min"), errors="coerce")
    out["packet_length_max"] = pd.to_numeric(_series(frame, "max"), errors="coerce")
    out["source_host"] = _series(frame, "saddr").astype("string")
    out["destination_host"] = _series(frame, "daddr").astype("string")
    out["timestamp_start"] = pd.to_numeric(_series(frame, "stime"), errors="coerce")
    out["timestamp_end"] = pd.to_numeric(_series(frame, "ltime"), errors="coerce")
    out["traffic_asymmetry"] = safe_divide(out["fwd_bytes"] - out["bwd_bytes"], out["total_bytes"])
    out["packet_direction_ratio"] = safe_divide(out["fwd_packets"], out["bwd_packets"] + 1.0)
    out["canonical_label"] = np.where(pd.to_numeric(_series(frame, "attack"), errors="coerce").eq(0), "BENIGN", "ATTACK")
    out["raw_label"] = _series(frame, "category").astype(str)
    return out


def _nbaiot_features(frame: pd.DataFrame, source_path: str | Path) -> pd.DataFrame:
    aggregate_columns = [
        column
        for column in frame.columns
        if column.startswith(("MI_dir_", "H_", "HH_", "HH_jit_", "HpHp_"))
    ]
    out = pd.DataFrame(
        {
            f"source_agg_{column}": pd.to_numeric(frame[column], errors="coerce")
            for column in aggregate_columns
        },
        index=frame.index,
    )
    label = nbaiot_label_from_filename(Path(source_path).name)
    out["canonical_label"] = "BENIGN" if label == "benign" else "ATTACK"
    out["raw_label"] = label
    out["device_id"] = Path(source_path).name.split(".")[0]
    return out
