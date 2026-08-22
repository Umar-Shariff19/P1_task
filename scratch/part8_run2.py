import json
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from scratch.part3_fresh_retrain import run_fresh_retraining

def main():
    print("============================================================")
    print("=== PART 8: REPRODUCIBILITY STABILITY TEST (RUN 2) ===")
    print("============================================================\n")

    # Run retraining for Run 2
    run_fresh_retraining(seed=42, output_suffix="run2")

if __name__ == "__main__":
    main()
