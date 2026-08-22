import json
import sys
from pathlib import Path
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from iot_ids.pipeline.system import IDSSystemPipeline
from iot_ids.utils.paths import REPO_ROOT

st.set_page_config(
    page_title="Multi-Level IoT IDS Demonstration System",
    page_icon="🛡️",
    layout="wide",
)

st.title("🛡️ Multi-Level IoT Intrusion Detection System")
st.markdown(
    "**Interactive Research Demonstration & Inspection Interface** | *Frozen Benchmark Architecture (Edge-IIoTset & ToN-IoT)*"
)

# Sidebar Setup
st.sidebar.header("⚙️ Configuration")
dataset_name = st.sidebar.selectbox("Target IoT Dataset", ["Edge-IIoTset", "ToN-IoT"])

@st.cache_resource
def get_pipeline(ds: str):
    return IDSSystemPipeline(dataset_name=ds)

pipeline = get_pipeline(dataset_name)

base_dir = REPO_ROOT / "data" / "processed" / "final"

@st.cache_data
def load_test_samples(ds_name: str):
    t_dir = [d for d in (base_dir / ds_name).iterdir() if d.is_dir()][0]
    df = pd.read_parquet(t_dir / "splits" / "test.parquet")
    return df

test_df = load_test_samples(dataset_name)

sample_mode = st.sidebar.radio(
    "Inspection Mode",
    ["Clean Benign Flow", "Clean Attack Flow", "Pre-Computed Adversarial Evasion"]
)

if sample_mode == "Clean Benign Flow":
    sub = test_df[test_df["label"] == 0]
    sample_idx = st.sidebar.number_input("Sample Index", min_value=0, max_value=len(sub)-1, value=0)
    sample_row = sub.iloc[sample_idx:sample_idx+1]
elif sample_mode == "Clean Attack Flow":
    sub = test_df[test_df["label"] == 1]
    sample_idx = st.sidebar.number_input("Sample Index", min_value=0, max_value=len(sub)-1, value=0)
    sample_row = sub.iloc[sample_idx:sample_idx+1]
else:
    sub = test_df[test_df["label"] == 1]
    sample_row = sub.iloc[0:1]

# Execute Inference
res = pipeline.predict_sample(sample_row)

p_rf = float(res["p_rf"][0])
p_mlp = float(res["p_mlp"][0])
p_sup = float(res["p_sup"][0])
s_ae = float(res["s_ae"][0])
risk_state = res["risk_states"][0]

# Display Risk Decision State Header
st.subheader("1. Design B Risk Layer Decision")
if risk_state == "BENIGN":
    st.success(f"🟢 **BENIGN** (P_sup = {p_sup:.4f} < 0.50, S_ae = {s_ae:.4f} < 0.80)")
elif risk_state == "HIGH CONFIDENCE ATTACK":
    st.error(f"🔴 **HIGH CONFIDENCE ATTACK** (P_sup = {p_sup:.4f} ≥ 0.50)")
else:
    st.warning(f"🟡 **SUSPICIOUS / ANOMALOUS** (P_sup = {p_sup:.4f} < 0.50, S_ae = {s_ae:.4f} ≥ 0.80 - Anomaly Triggered)")

# Display Metric Gauges
col1, col2, col3, col4 = st.columns(4)
col1.metric("P_rf (Random Forest)", f"{p_rf*100:.2f}%")
col2.metric("P_mlp (Neural Network)", f"{p_mlp*100:.2f}%")
col3.metric("P_sup (Ensemble)", f"{p_sup*100:.2f}%")
col4.metric("S_ae (Autoencoder Anomaly)", f"{s_ae:.4f}")

st.markdown("---")

# Main Multi-Tab Inspection Workspace
tab_indomain, tab_crossdomain, tab_xai, tab_adv = st.tabs([
    "📊 In-Domain (13 Features)",
    "🌐 Cross-Domain F_common (6 Features)",
    "💡 XAI & Attribution",
    "🛡️ Adversarial Robustness"
])

with tab_indomain:
    st.write(f"**In-Domain Multi-Level Feature Representation ({res['feature_count']} Active Features)**")
    st.caption("Combines static flow features, causal temporal rates/counts, and behavioral destination diversity.")
    df_disp = pd.DataFrame(res["X_scaled"], columns=res["feature_names"]).T
    df_disp.columns = ["Scaled Value"]
    st.dataframe(df_disp.style.format("{:.4f}"), use_container_width=True)

with tab_crossdomain:
    cd_info = pipeline.get_cross_domain_features(sample_row)
    st.write(f"**Harmonized Cross-Domain Space ({cd_info['common_feature_count']} Features)**")
    st.caption("Strictly physical network flow quantities: duration, src_bytes, proto_tcp, proto_udp, proto_icmp, is_well_known_port.")
    df_cd = pd.DataFrame(cd_info["X_common_scaled"], columns=cd_info["common_feature_names"]).T
    df_cd.columns = ["Harmonized Value"]
    st.dataframe(df_cd.style.format("{:.4f}"), use_container_width=True)

with tab_xai:
    st.write("**Autoencoder Per-Feature Reconstruction Error Breakdown ($e_i = (x_i - \\hat{x}_i)^2$)**")
    ae_series = pd.Series(res["ae_feature_contributions"]).head(8)
    st.bar_chart(ae_series)
    st.caption("XAI metric measures statistical feature contribution and model reliance, NOT physical causality.")

with tab_adv:
    st.write("**Pre-Computed Adversarial Evasion & Risk Layer Response**")
    adv_json = REPO_ROOT / "results" / "adversarial" / "adversarial_results.json"
    if adv_json.exists():
        adv_data = json.loads(adv_json.read_text(encoding="utf-8"))
        ds_adv = [r for r in adv_data if r["dataset"] == dataset_name]
        df_adv_summary = pd.DataFrame(ds_adv)[["attack", "epsilon", "n_attacked", "attack_success_rate", "ae_catch_rate"]]
        df_adv_summary["attack_success_rate"] = df_adv_summary["attack_success_rate"].apply(lambda x: f"{x*100:.2f}%")
        df_adv_summary["ae_catch_rate"] = df_adv_summary["ae_catch_rate"].apply(lambda x: f"{x*100:.2f}%")
        st.table(df_adv_summary)
    st.caption("Adversarial evaluation uses continuous feature perturbation with discrete protocol indicators strictly unperturbed.")

st.markdown("---")
st.caption("Multi-Level IoT Intrusion Detection System | Frozen Benchmark Architecture")
