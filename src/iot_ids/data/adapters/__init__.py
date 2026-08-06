from __future__ import annotations

from pathlib import Path

from iot_ids.data.adapters.base import DatasetAdapter
from iot_ids.data.adapters.bot_iot import BoTIoTAdapter
from iot_ids.data.adapters.cicids2017 import CICIDS2017Adapter
from iot_ids.data.adapters.edge_iiotset import EdgeIIoTsetAdapter
from iot_ids.data.adapters.nbaiot import NBaIoTAdapter


def build_default_adapters(data_root: Path, sample_rows: int = 5000) -> list[DatasetAdapter]:
    return [
        CICIDS2017Adapter(data_root / "CICIDS2017", sample_rows=sample_rows),
        EdgeIIoTsetAdapter(data_root / "Edge-IIoTset", sample_rows=sample_rows),
        BoTIoTAdapter(data_root / "BoT-IoT", sample_rows=sample_rows),
        NBaIoTAdapter(data_root / "N-BaIoT", sample_rows=sample_rows),
    ]

