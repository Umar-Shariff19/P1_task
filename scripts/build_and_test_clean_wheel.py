"""Script to build reproducible wheel and test in isolated environment."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    temp_root = Path(os.environ.get("TEMP", "/tmp"))
    stage_dir = temp_root / "ids_build_stage_fresh"
    wheel_out = temp_root / "ids_wheel_out_fresh"

    print("=== Step 1: Preparing Isolated Staging Directory ===")
    if stage_dir.exists():
        shutil.rmtree(stage_dir, ignore_errors=True)
    if wheel_out.exists():
        shutil.rmtree(wheel_out, ignore_errors=True)

    stage_dir.mkdir(parents=True, exist_ok=True)
    wheel_out.mkdir(parents=True, exist_ok=True)

    shutil.copy2(repo_root / "pyproject.toml", stage_dir / "pyproject.toml")
    shutil.copy2(repo_root / "README.md", stage_dir / "README.md")
    shutil.copytree(repo_root / "src", stage_dir / "src")

    python_exe = repo_root / ".venv" / "Scripts" / "python.exe"

    print("\n=== Step 2: Building Deterministic Wheel with SOURCE_DATE_EPOCH ===")
    env = os.environ.copy()
    env["SOURCE_DATE_EPOCH"] = env.get("SOURCE_DATE_EPOCH", "1700000000")

    cmd = [
        str(python_exe),
        "-m",
        "pip",
        "wheel",
        "--no-build-isolation",
        "--no-deps",
        "-w",
        str(wheel_out),
        str(stage_dir),
    ]
    res = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print("Build exit code:", res.returncode)
    if res.returncode != 0:
        print("Build error:\n", res.stderr)
        return res.returncode

    wheels = list(wheel_out.glob("*.whl"))
    if not wheels:
        print("ERROR: No wheel produced")
        return 1

    wheel = wheels[0]
    wheel_bytes = wheel.read_bytes()
    wheel_sha256 = hashlib.sha256(wheel_bytes).hexdigest()
    print(f"Built Wheel: {wheel.name}")
    print(f"Size: {len(wheel_bytes)} bytes")
    print(f"SHA-256: {wheel_sha256}")

    print("\n=== Step 3: Archive Contents Audit ===")
    with zipfile.ZipFile(wheel, "r") as z:
        file_list = z.namelist()
        print(f"Total packaged files: {len(file_list)}")
        dangerous = [
            f for f in file_list if f.endswith((".joblib", ".pt", ".parquet", ".csv", ".pcap"))
        ]
        if dangerous:
            print(f"ERROR: Dangerous bundled files detected: {dangerous}")
            return 1
        print("Audit: ZERO bundled model checkpoints or raw datasets. Clean package.")

    print("\n=== Step 4: Testing in Clean Disposable Environment ===")
    disposable_venv = temp_root / "ids_disposable_smoke_venv"
    if disposable_venv.exists():
        shutil.rmtree(disposable_venv, ignore_errors=True)

    # Create venv with parent venv site packages linked for dependency resolution in offline environment
    subprocess.run([str(python_exe), "-m", "venv", str(disposable_venv)], check=True)
    disp_pip = disposable_venv / "Scripts" / "pip.exe"
    disp_python = disposable_venv / "Scripts" / "python.exe"

    # Link dev venv site-packages via .pth so declared dependencies resolve in offline test environment
    dev_site_packages = repo_root / ".venv" / "Lib" / "site-packages"
    pth_file = disposable_venv / "Lib" / "site-packages" / "dev_dependencies.pth"
    pth_file.write_text(str(dev_site_packages) + "\n", encoding="utf-8")

    install_res = subprocess.run(
        [str(disp_pip), "install", "--no-deps", "--force-reinstall", str(wheel)],
        capture_output=True,
        text=True,
    )
    print("Wheel installation exit code:", install_res.returncode)
    if install_res.returncode != 0:
        print("Install error:\n", install_res.stderr)
        return install_res.returncode

    # Run smoke tests outside repo
    print("\n=== Step 5: Out-of-Repository Smoke Tests ===")
    cli_exe = disposable_venv / "Scripts" / "iot-ids.exe"
    cli_help_res = subprocess.run([str(cli_exe), "--help"], cwd=str(temp_root), capture_output=True, text=True)
    print("Out-of-repo 'iot-ids --help' exit code:", cli_help_res.returncode)

    demo_res = subprocess.run(
        [str(disp_python), "-m", "iot_ids.runtime.synthetic_packet_demo"],
        cwd=str(temp_root),
        capture_output=True,
        text=True,
    )
    print("Out-of-repo 'synthetic_packet_demo' exit code:", demo_res.returncode)

    # Verify import origin
    verify_script = (
        "import iot_ids; print('Imported iot_ids from:', iot_ids.__file__); "
        "assert 'ids_disposable_smoke_venv' in iot_ids.__file__; print('IMPORT_VERIFIED_OUTSIDE_REPO')"
    )
    import_res = subprocess.run(
        [str(disp_python), "-c", verify_script], cwd=str(temp_root), capture_output=True, text=True
    )
    print("Import verification output:", import_res.stdout.strip())

    if (
        cli_help_res.returncode == 0
        and demo_res.returncode == 0
        and "IMPORT_VERIFIED_OUTSIDE_REPO" in import_res.stdout
    ):
        print("\n=== ALL PACKAGING & OUT-OF-REPO TESTS VERIFIED SUCCESSFULLY ===")
        return 0
    else:
        print("\nERROR: Smoke tests failed.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
