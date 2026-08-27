"""Unit tests for Stage 11 submission packaging and final artifact verification."""

from pathlib import Path
import pandas as pd
import pytest


def test_stage11_submission_package_exists():
    sub_dir = Path("reports/stage11/submission")
    assert sub_dir.exists()
    assert (sub_dir / "IEEE_paper_final.tex").exists()
    assert (sub_dir / "references.bib").exists()
    assert (sub_dir / "figures").exists()


def test_stage11_checksums_csv():
    checksum_file = Path("reports/stage11/stage11_checksums.csv")
    assert checksum_file.exists()

    df = pd.read_csv(checksum_file)
    assert len(df) >= 10
    assert "sha256_checksum" in df.columns
    assert (df["size_bytes"] > 0).all()


def test_stage11_figures_tables_audit_pass():
    audit_file = Path("reports/stage11/stage11_figures_tables_audit.csv")
    assert audit_file.exists()

    df = pd.read_csv(audit_file)
    assert len(df) >= 17
    failing = df[df["status"] != "PASS"]
    assert len(failing) == 0, f"Discovered failing figure/table audit checks: {failing}"


def test_stage11_placeholder_audit_pass():
    audit_file = Path("reports/stage11/stage11_placeholder_audit.csv")
    assert audit_file.exists()

    df = pd.read_csv(audit_file)
    assert len(df) >= 7
    assert (df["status"] == "PASS").all()
