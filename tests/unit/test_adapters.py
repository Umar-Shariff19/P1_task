from __future__ import annotations

from pathlib import Path

from iot_ids.data.adapters import build_default_adapters
from iot_ids.data.adapters.base import normalize_column_name


def test_normalize_column_name() -> None:
    assert normalize_column_name(" Flow_ID ") == "flow id"
    assert normalize_column_name("Src-IP") == "src ip"


def test_missing_roots_report_missing(tmp_path: Path) -> None:
    adapters = build_default_adapters(tmp_path / "raw")
    audits = [adapter.audit() for adapter in adapters]
    assert {audit.status for audit in audits} == {"missing"}
    assert {audit.name for audit in audits} == {"CICIDS2017", "Edge-IIoTset", "BoT-IoT", "N-BaIoT"}


def test_cicids_profile_detects_label_and_leakage(tmp_path: Path) -> None:
    root = tmp_path / "raw" / "CICIDS2017"
    root.mkdir(parents=True)
    (root / "Monday.csv").write_text(
        "Flow ID, Source IP, Timestamp, Flow Duration, Label\n"
        "a,10.0.0.1,2026-01-01,10,BENIGN\n"
        "b,10.0.0.2,2026-01-01,20,DoS\n",
        encoding="utf-8",
    )

    audit = build_default_adapters(tmp_path / "raw", sample_rows=10)[0].audit()
    assert audit.status == "ok"
    assert "Label" in audit.label_columns_seen
    assert "Flow ID" in audit.leakage_columns_seen
    assert "Timestamp" in audit.temporal_columns_seen

