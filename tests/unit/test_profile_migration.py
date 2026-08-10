import pytest
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

from src.iot_ids.preprocessing.pipeline import get_model_feature_columns

def test_cross_domain_profile_preservation():
    """Verify the original 4-feature universal profile remains strictly intact."""
    for ds in ["CICIDS2017", "Edge-IIoTset", "BoT-IoT"]:
        cols = get_model_feature_columns(ds, profile="cross_domain")
        assert cols == ["duration_seconds", "dst_port", "total_bytes", "packet_length_mean"]
        
def test_in_domain_profile_richness():
    """Verify in-domain profiles contain the multi-level features."""
    cicids = get_model_feature_columns("CICIDS2017", profile="in_domain")
    assert len(cicids) == 18
    # Instant
    assert "total_packets" in cicids
    # Temporal
    assert "flow_iat_mean" in cicids
    # Behavioral
    assert "traffic_asymmetry" in cicids
    
    edge = get_model_feature_columns("Edge-IIoTset", profile="in_domain")
    assert len(edge) == 7
    # Temporal
    assert "source_provided_delta_seconds" in edge
    
    bot = get_model_feature_columns("BoT-IoT", profile="in_domain")
    assert len(bot) == 18
    # Behavioral
    assert "packet_direction_ratio" in bot
    
def test_nbaiot_profile_independence():
    """N-BaIoT should ignore the profile flag and always return its source aggregates."""
    cols_in = get_model_feature_columns("N-BaIoT", profile="in_domain")
    cols_out = get_model_feature_columns("N-BaIoT", profile="cross_domain")
    assert cols_in == cols_out
    assert cols_in == ["source_agg_*"]
    
def test_invalid_profile_rejection():
    """The resolver must strictly reject typos and unknown profiles."""
    with pytest.raises(ValueError, match="Invalid profile requested"):
        get_model_feature_columns("CICIDS2017", profile="invalid_profile_name")
        
def test_default_profile_is_in_domain():
    """The default profile must be 'in_domain' to satisfy the methodology's primary claim."""
    cols_default = get_model_feature_columns("CICIDS2017")
    cols_in = get_model_feature_columns("CICIDS2017", profile="in_domain")
    assert cols_default == cols_in
    assert len(cols_default) == 18

def test_ablation_filtering():
    """Verify that semantic level filtering correctly subsets the profile."""
    # CICIDS2017 instant-only should be 14 features (18 total - 2 temporal - 2 behavioral)
    instant_only = get_model_feature_columns("CICIDS2017", profile="in_domain", levels=["instant"])
    assert len(instant_only) == 14
    assert "duration_seconds" in instant_only
    assert "flow_iat_mean" not in instant_only
    assert "traffic_asymmetry" not in instant_only
    
    # CICIDS2017 instant+temporal should be 16 features (13 instant + 3 temporal)
    inst_temp = get_model_feature_columns("CICIDS2017", profile="in_domain", levels=["instant", "temporal"])
    assert len(inst_temp) == 16
    assert "flow_iat_mean" in inst_temp
    assert "traffic_asymmetry" not in inst_temp
    
    # N-BaIoT is purely behavioral. If we ask for instant only, it should return an empty list.
    nbaiot_inst = get_model_feature_columns("N-BaIoT", profile="in_domain", levels=["instant"])
    assert len(nbaiot_inst) == 0
    
    nbaiot_beh = get_model_feature_columns("N-BaIoT", profile="in_domain", levels=["behavioral"])
    assert len(nbaiot_beh) == 1
    assert nbaiot_beh == ["source_agg_*"]
