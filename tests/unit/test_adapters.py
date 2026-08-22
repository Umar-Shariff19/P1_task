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
    assert {audit.name for audit in audits} == {"Edge-IIoTset", "ToN-IoT"}
