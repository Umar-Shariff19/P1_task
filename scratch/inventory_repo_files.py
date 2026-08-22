import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from iot_ids.utils.paths import REPO_ROOT

def get_dir_size(path: Path):
    total = 0
    file_count = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            fp = Path(root) / f
            total += os.path.getsize(fp)
            file_count += 1
    return total, file_count

def main():
    print("============================================================")
    print("=== REPOSITORY FILE SIZE & CLASSIFICATION INVENTORY ===")
    print("============================================================\n")

    dirs_to_check = [
        "models/final",
        "models/verification_retrain",
        "data/processed/final",
        "reports",
        "scratch",
        "scripts",
        "src",
        "demo",
        "tests"
    ]

    for d in dirs_to_check:
        dp = REPO_ROOT / d
        if dp.exists():
            size, count = get_dir_size(dp)
            print(f"Directory [{d}]: {count} files, {size / (1024*1024):.2f} MB")
        else:
            print(f"Directory [{d}]: MISSING")

if __name__ == "__main__":
    main()
