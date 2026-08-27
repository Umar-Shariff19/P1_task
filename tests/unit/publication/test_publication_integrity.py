"""Unit tests for Stage 8 publication integrity and evidence verification."""

from pathlib import Path
import pandas as pd
import pytest


def test_publication_audit_csv_exists_and_passes():
    audit_file = Path("reports/stage8/stage8_publication_audit.csv")
    assert audit_file.exists()

    df = pd.read_csv(audit_file)
    assert len(df) >= 12

    # Verify that all claim audits achieved PASS status
    failing_claims = df[df["status"] != "PASS"]
    assert len(failing_claims) == 0, f"Discovered failing publication audit claims: {failing_claims}"


def test_artifact_manifest_exists():
    manifest_file = Path("reports/stage8/stage8_artifact_manifest.csv")
    assert manifest_file.exists()

    df = pd.read_csv(manifest_file)
    assert len(df) >= 6
    assert (df["verification_status"] == "VERIFIED").all()


def test_reproducibility_scripts_exist():
    required_scripts = [
        "scripts/03_materialize_and_audit_features.py",
        "scripts/04_benchmark_models.py",
        "scripts/05_domain_adaptation.py",
        "scripts/06_statistical_robustness.py",
        "scripts/07_generate_claim_evidence_matrix.py",
        "scripts/08_run_publication_audit.py",
    ]
    for script_path in required_scripts:
        assert Path(script_path).exists(), f"Missing required script: {script_path}"
