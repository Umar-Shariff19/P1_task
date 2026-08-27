"""Dataset Ingestion Adapters Module."""

from pathlib import Path
from iot_ids.data.adapters.base import DatasetAdapter, IngestionAuditReport
from iot_ids.data.adapters.ton_iot import ToNIoTAdapter
from iot_ids.data.adapters.edge_iiotset import EdgeIIoTsetAggregatorAdapter
from iot_ids.data.adapters.nf_ton_iot import NFToNIoTAdapter
from iot_ids.data.adapters.ciciot2023 import CICIoT2023Adapter


def build_default_adapters(raw_dir: Path, sample_rows: int = 1000) -> list[DatasetAdapter]:
    return [
        ToNIoTAdapter(raw_dir / "ToN-IoT"),
        EdgeIIoTsetAggregatorAdapter(raw_dir / "Edge-IIoTset"),
        NFToNIoTAdapter(raw_dir / "NF-ToN-IoT-v2"),
        CICIoT2023Adapter(raw_dir / "CICIoT2023"),
    ]


__all__ = [
    "DatasetAdapter",
    "IngestionAuditReport",
    "ToNIoTAdapter",
    "EdgeIIoTsetAggregatorAdapter",
    "NFToNIoTAdapter",
    "CICIoT2023Adapter",
    "build_default_adapters",
]
