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
    print("=== PART 10: FROZEN ARTIFACT INTEGRITY CHECKSUM AUDIT ===")
    print("============================================================\n")

    exp_dir = Path("reproducibility/fresh_retraining_20260821_010000")
    before_json = exp_dir / "frozen_checksums_before.json"

    if not before_json.exists():
        raise FileNotFoundError(f"Missing Part 0 snapshot: {before_json}")

    checksums_before = json.loads(before_json.read_text(encoding="utf-8"))
    checksums_after = {}

    models_dir = Path("models/final").resolve()
    data_dir = Path("data/processed/final").resolve()
    cwd = Path.cwd().resolve()

    for path in list(models_dir.rglob("*")) + list(data_dir.rglob("*")):
        if path.is_file():
            rel_path = str(path.resolve().relative_to(cwd)).replace("\\", "/")
            checksums_after[rel_path] = compute_md5(path)

    mismatches = []
    missing = []

    for rel_path, md5_before in checksums_before.items():
        if rel_path not in checksums_after:
            missing.append(rel_path)
        elif checksums_after[rel_path] != md5_before:
            mismatches.append((rel_path, md5_before, checksums_after[rel_path]))

    after_json = exp_dir / "frozen_checksums_after.json"
    after_json.write_text(json.dumps(checksums_after, indent=2), encoding="utf-8")

    print(f"Total Files Checked: {len(checksums_before)}")
    print(f"Missing Files: {len(missing)}")
    print(f"Checksum Mismatches: {len(mismatches)}")

    if len(missing) == 0 and len(mismatches) == 0:
        print("\nSUCCESS: All frozen artifacts in models/final/ and data/processed/final/ remain 100% BYTE-FOR-BYTE UNCHANGED.\n")
    else:
        print(f"\nFAILURE: Integrity breach detected! Missing: {missing}, Mismatches: {mismatches}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
