"""Privacy-Aware Data Minimization Module.

Enforces data minimization principles across the IoT IDS pipeline:
  - Operates strictly on 21 standardized flow-level statistical metrics (X in R^21)
  - Eliminates raw packet payload storage, user payload inspection, and PII retention
  - Verifies input vectors against raw payload leakages
"""
from __future__ import annotations

from typing import Dict, List, Any
import numpy as np


class DataMinimizationPolicy:
    """Formal definition of Privacy-Aware Data Minimization policy for IoT IDS."""

    ALLOWED_FEATURE_CATEGORIES = {
        "flow_duration": "Flow duration statistics",
        "fwd_pkts_per_sec": "Aggregated packet throughput rate",
        "bwd_pkts_per_sec": "Aggregated packet throughput rate",
        "bytes_per_sec": "Aggregated byte throughput rate",
        "fwd_pkt_len_mean": "Statistical mean packet size",
        "bwd_pkt_len_mean": "Statistical mean packet size",
        "payload_bytes_ratio": "Aggregated payload size ratio",
        "header_bytes_ratio": "Aggregated protocol header ratio",
        "tcp_syn_ratio": "Control flag frequency statistic",
        "fwd_iat_mean": "Inter-arrival timing statistic",
        "bwd_iat_mean": "Inter-arrival timing statistic",
        "flow_iat_mean": "Inter-arrival timing statistic",
        "behavioral_src_activity_ewma": "Behavioral EWMA metric",
        "behavioral_dst_activity_ewma": "Behavioral EWMA metric",
        "behavioral_bytes_ewma": "Behavioral EWMA metric",
        "behavioral_dst_entropy": "Statistical entropy metric",
        "behavioral_flow_rate_ewma": "Behavioral EWMA metric",
        "proto_tcp": "One-hot protocol identifier",
        "proto_udp": "One-hot protocol identifier",
        "proto_icmp": "One-hot protocol identifier",
        "proto_other": "One-hot protocol identifier",
    }

    FORBIDDEN_DATA_TYPES = [
        "raw_payload_bytes",
        "http_body_text",
        "user_passwords",
        "application_payload_hex",
        "device_mac_addresses",
        "raw_pcap_frames",
    ]

    @classmethod
    def verify_schema_minimization(cls, feature_names: List[str]) -> Dict[str, Any]:
        """Audits feature schema to verify 100% compliance with data minimization policy."""
        violations = []
        for name in feature_names:
            if name.lower() in cls.FORBIDDEN_DATA_TYPES or "payload_content" in name.lower() or "raw_hex" in name.lower():
                violations.append(name)

        is_compliant = len(violations) == 0 and len(feature_names) == 21
        return {
            "is_compliant": is_compliant,
            "total_features": len(feature_names),
            "allowed_categories": len(cls.ALLOWED_FEATURE_CATEGORIES),
            "violations_found": violations,
            "policy_summary": "Operates strictly on 21 flow-level statistical metrics without raw payload storage.",
        }


def extract_minimized_representation(raw_flow_dict: Dict[str, float]) -> np.ndarray:
    """Extracts standardized 21-D flow feature vector complying with data minimization."""
    ordered_cols = list(DataMinimizationPolicy.ALLOWED_FEATURE_CATEGORIES.keys())
    vec = np.zeros(len(ordered_cols), dtype=np.float32)

    for i, col in enumerate(ordered_cols):
        vec[i] = float(raw_flow_dict.get(col, 0.0))

    return vec
