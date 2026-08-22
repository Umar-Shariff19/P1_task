import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from iot_ids.utils.paths import REPO_ROOT

def clean_caches():
    print("============================================================")
    print("=== PHASE 3: SAFE CACHE & TEMPORARY CLUTTER CLEANUP ===")
    print("============================================================\n")

    cache_dirs_removed = 0
    pyc_files_removed = 0

    for root, dirs, files in os.walk(REPO_ROOT):
        # Remove __pycache__, .pytest_cache, .mypy_cache, .ruff_cache
        for d in list(dirs):
            if d in ["__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"]:
                target = Path(root) / d
                shutil.rmtree(target, ignore_errors=True)
                cache_dirs_removed += 1
                dirs.remove(d)

        for f in files:
            if f.endswith(".pyc") or f.endswith(".pyo") or f.endswith(".log"):
                target = Path(root) / f
                try:
                    os.remove(target)
                    pyc_files_removed += 1
                except Exception:
                    pass

    print(f"Removed {cache_dirs_removed} cache directories (__pycache__, .pytest_cache).")
    print(f"Removed {pyc_files_removed} temporary .pyc/.log files.")

if __name__ == "__main__":
    clean_caches()
