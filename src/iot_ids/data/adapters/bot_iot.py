from __future__ import annotations

from pathlib import Path

from iot_ids.data.adapters.base import DatasetAdapter
from iot_ids.data.schema.profile import DatasetAudit


class BoTIoTAdapter(DatasetAdapter):
    name = "BoT-IoT"

    def discover_files(self) -> list[Path]:
        return sorted(p for p in self.root.rglob("*.csv") if p.name.lower() != "data_names.csv")

    def dataset_notes(self, audit: DatasetAudit) -> list[str]:
        has_names = (self.root / "data_names.csv").exists()
        return [
            f"data_names.csv present: {has_names}. Use it to validate partition schemas before full processing.",
            "Adapters must stream partitions/chunks instead of concatenating all CSVs into memory.",
        ]

