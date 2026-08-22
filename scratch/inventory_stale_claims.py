import json
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from iot_ids.utils.paths import REPO_ROOT

def main():
    stale_queries = ["99.60", "86.59", "0.8547", "86.47", "0.7073", "15 Features", "8-feature"]
    doc_files = sorted(list(REPO_ROOT.glob("*.md")) + list((REPO_ROOT / "reports").rglob("*.md")) + list((REPO_ROOT / "docs").rglob("*.md")))

    findings = []

    for fpath in doc_files:
        rel_path = str(fpath.relative_to(REPO_ROOT))
        content = fpath.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()

        for line_idx, line in enumerate(lines, start=1):
            for q in stale_queries:
                if q in line:
                    line_lower = line.lower()
                    is_hist_context = any(w in line_lower for w in ["superseded", "historical", "reconciliation", "old", "replaced", "audit", "draft"])
                    
                    if "FINAL_PROJECT_FREEZE.md" in rel_path or "FINAL_PAPER_EVIDENCE_PACKAGE.md" in rel_path or "FINAL_RETRAINING_AND_FROZEN_RECONCILIATION.md" in rel_path:
                        classification = "LEGITIMATE HISTORICAL/SUPERSEDED DOCUMENTATION"
                    elif is_hist_context:
                        classification = "LEGITIMATE HISTORICAL/SUPERSEDED DOCUMENTATION"
                    else:
                        classification = "STALE CLAIM IN HISTORICAL REPORT (DOCUMENTATION CLEANUP NEEDED)"

                    findings.append({
                        "file": rel_path,
                        "line": line_idx,
                        "query": q,
                        "snippet": line.strip()[:110],
                        "classification": classification
                    })

    df = pd.DataFrame(findings)
    print(df.to_string(index=False))

    summary_path = REPO_ROOT / "scratch" / "stale_claims_inventory.json"
    summary_path.write_text(json.dumps(findings, indent=2), encoding="utf-8")
    print(f"\nSaved Stale Claims Inventory to: {summary_path}\n")

if __name__ == "__main__":
    main()
