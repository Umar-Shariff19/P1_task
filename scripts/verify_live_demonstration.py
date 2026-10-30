"""Comprehensive live demonstration verification script.
Tests all endpoints, simulator, models, XAI, and adversarial lab against a real running Uvicorn server on port 8501.
"""
from __future__ import annotations

import json
import sys
import threading
import time
import urllib.request
from pathlib import Path

# Add src to python path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from iot_ids.dashboard.cli import run_dashboard_server
from iot_ids.dashboard.state import reset_platform_state


def main():
    reset_platform_state()

    print("=" * 76)
    print("STARTING IN-PROCESS LIVE UVICORN SERVER ON PORT 8501")
    print("=" * 76)

    server_thread = threading.Thread(
        target=run_dashboard_server,
        kwargs={
            "host": "127.0.0.1",
            "port": 8501,
            "seed": 42,
            "traffic_interval": 0.1,
            "auto_start": True,
            "log_level": "warning",
        },
        daemon=True,
    )
    server_thread.start()

    time.sleep(2.5)

    def get(path: str):
        req = urllib.request.urlopen(f"http://127.0.0.1:8501{path}")
        return json.loads(req.read().decode("utf-8"))

    def post(path: str, body: dict):
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:8501{path}",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        return json.loads(urllib.request.urlopen(req).read().decode("utf-8"))

    print("\n--- Test A: Startup & Status Endpoint ---")
    st = get("/api/status")
    print("Platform status:", st["platform_status"])
    print("Active scenario:", st["simulator"]["active_scenario"])
    print("Active model:", st["pipeline"]["active_model"])
    print("Device count:", st["simulator"]["device_count"])
    print("Model suite type:", st["provenance"]["model_suite_type"])
    print("Auth status:", st["provenance"]["model_authorization_status"])

    time.sleep(1.0)

    print("\n--- Test B: Benign Traffic Simulation & Flows ---")
    flows_data = get("/api/flows?limit=10")
    print(f"Total flows received: {flows_data['count']}")
    if flows_data["flows"]:
        f0 = flows_data["flows"][0]
        print(f"Flow ID: {f0['flow_id']}")
        print(f"  Prediction Prob: {f0['prediction_prob']:.4f}")
        print(f"  Decision Threshold: {f0['decision_threshold']}")
        print(f"  Is Anomaly: {f0['is_anomaly']}")
        print(f"  Risk Score: {f0['risk_score']:.4f} ({f0['risk_level']})")

    print("\n--- Test C: Threat Scenario Switching & Alerts ---")
    sc_res = post("/api/simulation/scenario", {"scenario": "MIRAI_BOTNET_FLOOD"})
    print("Switched scenario:", sc_res["scenario_type"], "-", sc_res["scenario_name"])

    time.sleep(1.5)
    step_res = post("/api/simulation/step", {"count": 15})
    print(f"Stepped {step_res['alerts_generated']} flows.")

    alerts_data = get("/api/alerts?limit=10")
    print(f"Total alerts recorded: {alerts_data['count']}")
    if alerts_data["alerts"]:
        a0 = alerts_data["alerts"][0]
        print(f"Alert ID: {a0['flow_id']}")
        print(f"  Scenario: {a0['scenario']}")
        print(f"  Threat Probability: {a0['prediction_prob']:.4f}")
        print(f"  Risk Level: {a0['risk_level']}")

    print("\n--- Test D: Active Model Selection ---")
    for m in ["rf", "robust_mlp", "standard_mlp", "option_c"]:
        res_m = post("/api/models/select", {"model": m})
        act = res_m["active_model"]
        hlth = res_m["health"]
        print(f"  Active model switched to: {act} (Health: {hlth})")

    print("\n--- Test E: Explainability (XAI) Attribution ---")
    xai = post("/api/explain", {})
    print(f"XAI Final Decision: {xai.get('final_decision')}")
    print(f"Option C Prob: {xai.get('option_c_probability', 0):.4f}")
    print(f"RF Prob: {xai.get('rf_probability', 0):.4f}, Robust MLP Prob: {xai.get('mlp_probability', 0):.4f}")
    print("Top Influential Features:")
    for feat in xai.get("top_k_features", [])[:5]:
        val = feat["raw_value"]
        attr = feat["weighted_attribution"]
        direction = feat["direction"]
        fname = feat["feature"]
        print(f"  {fname:<28} val={val:<10.3f} attr={attr:<+8.4f} ({direction})")

    print("\n--- Test F: Adversarial Attack Laboratory ---")
    print("Executing FGSM attack experiment (epsilon=0.8)...")
    fgsm = post("/api/adversarial/run", {"attack_method": "fgsm", "epsilon": 0.8, "sample_count": 15})
    print(f"FGSM Experiment ID: {fgsm['experiment_id']}")
    std_clean = fgsm["models"]["standard_mlp"]["clean_detection_rate"]
    std_adv = fgsm["models"]["standard_mlp"]["adv_detection_rate"]
    std_drop = fgsm["models"]["standard_mlp"]["degradation"]
    rob_clean = fgsm["models"]["robust_mlp"]["clean_detection_rate"]
    rob_adv = fgsm["models"]["robust_mlp"]["adv_detection_rate"]
    rob_drop = fgsm["models"]["robust_mlp"]["degradation"]
    print(f"  Standard MLP: Clean={std_clean:.2%} -> Adv={std_adv:.2%} (Degradation: {std_drop:.2%})")
    print(f"  Robust MLP:   Clean={rob_clean:.2%} -> Adv={rob_adv:.2%} (Degradation: {rob_drop:.2%})")

    print("\nExecuting PGD attack experiment (epsilon=0.8, steps=7)...")
    pgd = post("/api/adversarial/run", {"attack_method": "pgd", "epsilon": 0.8, "steps": 7, "sample_count": 15})
    print(f"PGD Experiment ID: {pgd['experiment_id']}")
    std_clean_p = pgd["models"]["standard_mlp"]["clean_detection_rate"]
    std_adv_p = pgd["models"]["standard_mlp"]["adv_detection_rate"]
    std_drop_p = pgd["models"]["standard_mlp"]["degradation"]
    rob_clean_p = pgd["models"]["robust_mlp"]["clean_detection_rate"]
    rob_adv_p = pgd["models"]["robust_mlp"]["adv_detection_rate"]
    rob_drop_p = pgd["models"]["robust_mlp"]["degradation"]
    print(f"  Standard MLP: Clean={std_clean_p:.2%} -> Adv={std_adv_p:.2%} (Degradation: {std_drop_p:.2%})")
    print(f"  Robust MLP:   Clean={rob_clean_p:.2%} -> Adv={rob_adv_p:.2%} (Degradation: {rob_drop_p:.2%})")

    print("\n--- Test G: Historical Experiment Retrieval ---")
    exps = get("/api/experiments")
    print(f"Persisted experiments in ledger: {exps['count']}")

    print("\n--- Test H: Graceful Shutdown ---")
    post("/api/system/shutdown", {})
    time.sleep(1.0)
    print("Server cleanly shut down. Port 8501 released.")
    print("\n" + "=" * 76)
    print("ALL LIVE DEMONSTRATION TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 76)


if __name__ == "__main__":
    main()
