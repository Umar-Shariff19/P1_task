import subprocess
import sys
import os
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_MODULE = REPO_ROOT / "src" / "iot_ids" / "cli.py"

def run_cli(args):
    env = os.environ.copy()
    # Make the optional-dependency condition deterministic even on machines
    # that have Scapy installed. This prevents tests from opening live capture.
    with tempfile.TemporaryDirectory() as shim_dir:
        shim = Path(shim_dir) / "sitecustomize.py"
        shim.write_text(
            "import builtins\n"
            "_original_import = builtins.__import__\n"
            "def _without_scapy(name, *args, **kwargs):\n"
            "    if name == 'scapy' or name.startswith('scapy.'):\n"
            "        raise ImportError('Scapy disabled by isolated CLI test')\n"
            "    return _original_import(name, *args, **kwargs)\n"
            "builtins.__import__ = _without_scapy\n",
            encoding="utf-8",
        )
        env["PYTHONPATH"] = os.pathsep.join([str(shim_dir), str(REPO_ROOT / "src")])
        return subprocess.run(
            [sys.executable, str(CLI_MODULE)] + args,
            capture_output=True,
            text=True,
            env=env,
        )


def test_predict_live_refuses_before_scapy_or_artifact_access():
    args = ["predict-live", "--artifact-dir", "synthetic-placeholder-never-opened"]
    result = run_cli(args)
    assert result.returncode == 2
    assert "REAL_AUTHORIZATION_DISABLED" in result.stderr
    assert "Traceback" not in result.stderr
    assert "requires Scapy" not in result.stderr


def test_replay_pcap_refuses_before_scapy_or_file_access():
    args = [
        "replay-pcap",
        "--artifact-dir",
        "synthetic-placeholder-never-opened",
        "--pcap-file",
        "synthetic-placeholder-never-opened.pcap",
    ]
    result = run_cli(args)
    assert result.returncode == 2
    assert "REAL_AUTHORIZATION_DISABLED" in result.stderr
    assert "Traceback" not in result.stderr
    assert "requires Scapy" not in result.stderr


def test_run_daemon_refuses_before_scapy_or_artifact_access():
    args = [
        "run-daemon",
        "--artifact-dir",
        "synthetic-placeholder-never-opened",
    ]
    result = run_cli(args)
    assert result.returncode == 2
    assert "REAL_AUTHORIZATION_DISABLED" in result.stderr
    assert "Traceback" not in result.stderr
    assert "requires Scapy" not in result.stderr
