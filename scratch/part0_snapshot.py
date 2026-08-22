import hashlib
import json
from pathlib import Path

def compute_md5(file_path: Path) -> str:
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def main():
    print("============================================================")
    print("=== PART 0: FROZEN BASELINE CHECKSUM SNAPSHOT ===")
    print("============================================================\n")

    timestamp = "20260821_010000"
    exp_dir = Path("reproducibility") / f"fresh_retraining_{timestamp}"
    exp_dir.mkdir(parents=True, exist_ok=True)

    models_dir = Path("models/final").resolve()
    data_dir = Path("data/processed/final").resolve()
    cwd = Path.cwd().resolve()

    checksums = {}

    for path in list(models_dir.rglob("*")) + list(data_dir.rglob("*")):
        if path.is_file():
            rel_path = str(path.resolve().relative_to(cwd)).replace("\\", "/")
            checksums[rel_path] = compute_md5(path)

    snapshot_file = exp_dir / "frozen_checksums_before.json"
    snapshot_file.write_text(json.dumps(checksums, indent=2), encoding="utf-8")

    print(f"Snapshot Created: {snapshot_file}")
    print(f"Total Frozen Files Tracked: {len(checksums)}")
    print(f"Isolated Experiment Directory: {exp_dir}\n")

if __name__ == "__main__":
    main()
