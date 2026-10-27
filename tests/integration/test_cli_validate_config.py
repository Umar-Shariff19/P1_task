import os
import subprocess
import sys
from pathlib import Path

# Path to the repository root (tests run from repo root)
REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_MODULE = REPO_ROOT / "src" / "iot_ids" / "cli.py"

def run_cli_validate(artifact_dir: str, test_domain: str = "SYNTHETIC_ONLY"):
    """Invoke validate; the authorization boundary must refuse before dispatch."""
    cmd = [sys.executable, str(CLI_MODULE), "validate", "--artifact-dir", artifact_dir, "--test-domain", test_domain]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT, env=env)
    return result

def test_validate_refuses_before_artifact_or_split_access():
    """The validation command must fail closed before inspecting any artifact."""
    result = run_cli_validate("synthetic-placeholder-never-opened")
    assert result.returncode == 2
    assert "REAL_AUTHORIZATION_DISABLED" in result.stderr
    assert "trusted root identity and owner approval are unavailable" in result.stderr
    assert "Traceback" not in result.stderr
    assert "[CONFIG] Loaded artifact directory" not in result.stdout
    assert "Status:    PASSED" not in result.stdout

def test_sklearn_version_compatibility():
    """Record the installed scikit-learn version for audit purposes."""
    import sklearn
    installed_version = sklearn.__version__
    assert installed_version, "scikit-learn version could not be determined"
    print(f"[INFO] Installed scikit-learn version: {installed_version}")
