from __future__ import annotations

from pathlib import Path

from iot_ids.data.adapters.base import DatasetAdapter
from iot_ids.data.schema.profile import DatasetAudit


class EdgeIIoTsetAdapter(DatasetAdapter):
    name = "Edge-IIoTset"

    def discover_files(self) -> list[Path]:
        csvs = sorted(self.root.rglob("*.csv"))
        preferred = [
            p
            for p in csvs
            if any(token in p.name.lower() for token in ("ml", "dl", "selected", "processed"))
        ]
        return preferred or csvs

    def dataset_notes(self, audit: DatasetAudit) -> list[str]:
        return [
            "Prepared ML/DL CSVs are preferred for initial P1 tabular modeling when present.",
            "PCAP files are preserved as source/reference material and are not re-extracted by the initial adapter.",
        ]

