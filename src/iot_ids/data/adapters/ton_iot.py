from __future__ import annotations

from pathlib import Path

from iot_ids.data.adapters.base import DatasetAdapter
from iot_ids.data.schema.profile import DatasetAudit


class ToN_IoTAdapter(DatasetAdapter):
    name = "ToN-IoT"

    def discover_files(self) -> list[Path]:
        csvs = sorted(self.root.rglob("*.csv"))
        preferred = [
            p
            for p in csvs
            if any(token in p.name.lower() for token in ("train_test_network", "network", "ton"))
        ]
        return preferred or csvs

    def dataset_notes(self, audit: DatasetAudit) -> list[str]:
        return [
            "ToN-IoT Network CSV dataset (train_test_network.csv) containing Zeek flow telemetry.",
            "Features include IP/port headers, flow duration, directional packet/byte counts, and service metadata.",
        ]
