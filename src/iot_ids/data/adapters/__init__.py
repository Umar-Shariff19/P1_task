from __future__ import annotations

from pathlib import Path

from iot_ids.data.adapters.base import DatasetAdapter
from iot_ids.data.adapters.bot_iot import BoTIoTAdapter  # Legacy/Deprecated
from iot_ids.data.adapters.cicids2017 import CICIDS2017Adapter  # Legacy/Deprecated
from iot_ids.data.adapters.edge_iiotset import EdgeIIoTsetAdapter
from iot_ids.data.adapters.nbaiot import NBaIoTAdapter  # Legacy/Deprecated
from iot_ids.data.adapters.ton_iot import ToN_IoTAdapter


def build_default_adapters(data_root: Path) -> list[DatasetAdapter]:
    """Active production dataset adapters: Edge-IIoTset and ToN-IoT Network only."""
    return [
        EdgeIIoTsetAdapter(data_root / "Edge-IIoTset"),
        ToN_IoTAdapter(data_root / "ToN-IoT"),
    ]


__all__ = [
    "DatasetAdapter",
    "EdgeIIoTsetAdapter",
    "ToN_IoTAdapter",
    "BoTIoTAdapter",
    "CICIDS2017Adapter",
    "NBaIoTAdapter",
    "build_default_adapters",
]
