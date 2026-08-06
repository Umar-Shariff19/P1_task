from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
import pandas as pd

from iot_ids.data.schema.profile import DatasetAudit, FileProfile


LABEL_NAMES = {
    "label",
    "class",
    "attack",
    "attack label",
    "attack type",
    "attack category",
    "category",
    "subcategory",
    "sub category",
    "sub cat",
}
TEMPORAL_PATTERNS = ("timestamp", "time", "stime", "ltime", "date")
ENTITY_PATTERNS = (
    "flow id",
    "src ip",
    "dst ip",
    "source ip",
    "destination ip",
    "srcip",
    "dstip",
    "device",
    "host",
    "mac",
)
LEAKAGE_PATTERNS = ENTITY_PATTERNS + (
    "id",
    "uid",
    "source",
    "file",
    "dataset",
    "attack_cat",
    "attack_type",
)


def normalize_column_name(column: str) -> str:
    return " ".join(str(column).replace("_", " ").replace("-", " ").strip().lower().split())


def find_columns(columns: list[str], patterns: tuple[str, ...]) -> list[str]:
    normalized = {c: normalize_column_name(c) for c in columns}
    return [c for c, n in normalized.items() if any(pattern in n for pattern in patterns)]


def find_label_columns(columns: list[str]) -> list[str]:
    labels: list[str] = []
    for column in columns:
        normalized = normalize_column_name(column)
        dotted = normalized.replace(".", " ")
        if normalized in LABEL_NAMES or dotted in LABEL_NAMES:
            labels.append(column)
        elif normalized.endswith(" label") or normalized.endswith(" category"):
            labels.append(column)
    return labels


class DatasetAdapter(ABC):
    name: str

    def __init__(self, root: Path, sample_rows: int = 5000) -> None:
        self.root = root
        self.sample_rows = sample_rows

    @abstractmethod
    def discover_files(self) -> list[Path]:
        """Return candidate tabular source files for the adapter."""

    def audit(self) -> DatasetAudit:
        if not self.root.exists():
            return DatasetAudit(
                name=self.name,
                root=str(self.root),
                status="missing",
                notes=[f"Expected raw dataset root does not exist: {self.root}"],
            )

        files = self.discover_files()
        source_files = [p for p in self.root.rglob("*") if p.is_file()]
        audit = DatasetAudit(
            name=self.name,
            root=str(self.root),
            status="ok" if files else "empty",
            total_files=len(files),
            total_size_bytes=sum(path.stat().st_size for path in files if path.exists()),
            source_total_files=len(source_files),
            source_total_size_bytes=sum(path.stat().st_size for path in source_files if path.exists()),
        )
        if not files:
            audit.notes.append("No candidate CSV/tabular files discovered.")
            return audit

        schema_union: set[str] = set()
        label_seen: set[str] = set()
        leakage_seen: set[str] = set()
        temporal_seen: set[str] = set()
        entity_seen: set[str] = set()

        for path in files:
            profile = self.profile_file(path)
            audit.files.append(profile)
            schema_union.update(profile.columns)
            label_seen.update(profile.label_candidates)
            leakage_seen.update(profile.suspicious_leakage_columns)
            temporal_seen.update(find_columns(profile.columns, TEMPORAL_PATTERNS))
            entity_seen.update(find_columns(profile.columns, ENTITY_PATTERNS))

        audit.schema_union = sorted(schema_union)
        audit.label_columns_seen = sorted(label_seen)
        audit.leakage_columns_seen = sorted(leakage_seen)
        audit.temporal_columns_seen = sorted(temporal_seen)
        audit.entity_columns_seen = sorted(entity_seen)
        audit.label_distribution = self.aggregate_label_distribution(audit.files)
        audit.notes.extend(self.dataset_notes(audit))
        return audit

    def profile_file(self, path: Path) -> FileProfile:
        profile = FileProfile.from_path(path)
        profile.row_count = count_csv_rows(path) if path.suffix.lower() == ".csv" else None
        try:
            frame = pd.read_csv(path, nrows=self.sample_rows, low_memory=False, skipinitialspace=True)
        except Exception as exc:  # noqa: BLE001 - audit must keep going across bad files.
            profile.read_error = repr(exc)
            return profile

        frame.columns = [str(c).strip() for c in frame.columns]
        profile.rows_sampled = len(frame)
        profile.columns = [str(c) for c in frame.columns]
        profile.dtypes = {str(k): str(v) for k, v in frame.dtypes.items()}
        profile.label_candidates = find_label_columns(profile.columns)
        profile.suspicious_leakage_columns = find_columns(profile.columns, LEAKAGE_PATTERNS)

        for col in profile.label_candidates[:3]:
            counts = value_counts_csv(path, col)
            if counts:
                profile.label_distribution_sample[col] = counts

        missing = frame.isna().sum()
        profile.missing_sample = {str(k): int(v) for k, v in missing[missing > 0].items()}

        numeric = frame.select_dtypes(include=[np.number])
        if not numeric.empty:
            inf_counts = np.isinf(numeric.to_numpy(dtype=float, copy=False)).sum(axis=0)
            profile.inf_sample = {
                str(col): int(count)
                for col, count in zip(numeric.columns, inf_counts, strict=False)
                if count
            }

        nunique = frame.nunique(dropna=False)
        profile.constant_columns_sample = [str(k) for k, v in nunique.items() if v <= 1]
        profile.high_cardinality_columns_sample = [
            str(k) for k, v in nunique.items() if len(frame) and v / len(frame) > 0.95
        ]
        return profile

    def dataset_notes(self, audit: DatasetAudit) -> list[str]:
        return []

    def aggregate_label_distribution(self, files: list[FileProfile]) -> dict[str, dict[str, int]]:
        aggregate: dict[str, dict[str, int]] = {}
        for file_profile in files:
            for column, counts in file_profile.label_distribution_sample.items():
                target = aggregate.setdefault(column, {})
                for label, count in counts.items():
                    target[label] = target.get(label, 0) + count
        return aggregate


def count_csv_rows(path: Path) -> int | None:
    try:
        with path.open("rb") as handle:
            line_count = sum(chunk.count(b"\n") for chunk in iter(lambda: handle.read(1024 * 1024), b""))
    except OSError:
        return None
    return max(line_count - 1, 0)


def value_counts_csv(path: Path, column: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    try:
        chunks = pd.read_csv(
            path,
            usecols=[column],
            chunksize=250_000,
            low_memory=False,
            skipinitialspace=True,
        )
        for chunk in chunks:
            series = chunk[column].astype("string").fillna("<NA>")
            for label, count in series.value_counts(dropna=False).items():
                label_text = str(label)
                counts[label_text] = counts.get(label_text, 0) + int(count)
    except Exception:  # noqa: BLE001 - label distribution is best-effort audit metadata.
        return {}
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))
