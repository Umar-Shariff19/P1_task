"""Unit tests for Level B Causal Temporal Feature Extractor."""

import pytest
from iot_ids.data.flow_object import CanonicalFlow
from iot_ids.features.canonical.temporal import TemporalFeatureExtractor, TEMPORAL_FEATURE_NAMES


def test_temporal_causal_execution_and_initialization():
    extractor = TemporalFeatureExtractor(alpha=0.1)

    f1 = CanonicalFlow(
        timestamp_start=100.0,
        timestamp_end=101.0,
        src_host="10.0.0.5",
        dst_host="10.0.0.1",
        src_port=100,
        dst_port=80,
        protocol="tcp",
        bytes_src=500,
        bytes_dst=200,
        pkts_src=5,
        pkts_dst=2,
        syn_count_src=1,
        ack_count_src=1,
        rst_count_src=0,
        conn_state_code=0,
        label=0,
        attack_category="Normal",
    )

    # Event 1: First event initialization policy
    feat1 = extractor.extract_and_update(f1)
    assert feat1["temporal_iat_mean"] == 0.0
    assert feat1["temporal_iat_cv"] == 0.0
    assert feat1["temporal_flow_rate_ewma"] == 0.0
    assert extractor.first_event_count == 1

    # Event 2: Should read state from Event 1 (READ BEFORE WRITE)
    f2 = CanonicalFlow(
        timestamp_start=105.0,  # delta_t = 5.0s
        timestamp_end=106.0,
        src_host="10.0.0.5",
        dst_host="10.0.0.2",
        src_port=101,
        dst_port=80,
        protocol="tcp",
        bytes_src=300,
        bytes_dst=100,
        pkts_src=3,
        pkts_dst=1,
        syn_count_src=1,
        ack_count_src=1,
        rst_count_src=0,
        conn_state_code=0,
        label=0,
        attack_category="Normal",
    )

    feat2 = extractor.extract_and_update(f2)
    # Event 2 features must read previous state (iat_mean from state updated after f1)
    assert feat2["temporal_flow_rate_ewma"] > 0.0
    assert feat2["temporal_byte_rate_ewma"] > 0.0


def test_temporal_state_reset():
    extractor = TemporalFeatureExtractor()
    f1 = CanonicalFlow(
        timestamp_start=100.0,
        timestamp_end=101.0,
        src_host="10.0.0.5",
        dst_host="10.0.0.1",
        src_port=100,
        dst_port=80,
        protocol="tcp",
        bytes_src=500,
        bytes_dst=200,
        pkts_src=5,
        pkts_dst=2,
        syn_count_src=1,
        ack_count_src=1,
        rst_count_src=0,
        conn_state_code=0,
        label=0,
        attack_category="Normal",
    )
    extractor.extract_and_update(f1)
    assert len(extractor.host_states) == 1

    extractor.reset_state()
    assert len(extractor.host_states) == 0


def _build_test_flow(
    ts_start: float,
    ts_end: float,
    src_host: str = "10.0.0.5",
    dst_host: str = "10.0.0.1",
    bytes_src: int = 500,
    bytes_dst: int = 200,
    syn_count_src: int = 0,
) -> CanonicalFlow:
    return CanonicalFlow(
        timestamp_start=float(ts_start),
        timestamp_end=float(ts_end),
        src_host=src_host,
        dst_host=dst_host,
        src_port=100,
        dst_port=80,
        protocol="tcp",
        bytes_src=bytes_src,
        bytes_dst=bytes_dst,
        pkts_src=5,
        pkts_dst=2,
        syn_count_src=syn_count_src,
        ack_count_src=1,
        rst_count_src=0,
        conn_state_code=0,
        label=0,
        attack_category="Normal",
    )


def test_temporal_first_event_zero_duration():
    """Verify first event with zero duration initializes safely to 0.0 without rate explosion."""
    extractor = TemporalFeatureExtractor(alpha=0.1)
    f1 = _build_test_flow(100.0, 100.0, bytes_src=800, bytes_dst=0)

    feat1 = extractor.extract_and_update(f1)
    # First-event read-before-write output
    assert feat1["temporal_flow_rate_ewma"] == 0.0
    assert feat1["temporal_byte_rate_ewma"] == 0.0

    # Internal state after updating with duration=0.0 flow
    state = extractor.host_states["10.0.0.5"]
    assert state.flow_rate_ewma == 0.0
    assert state.byte_rate_ewma == 0.0
    assert state.iat_mean == 0.0


def test_temporal_repeated_zero_duration_flows():
    """Verify sequence of zero-duration flows does not produce byte rate spikes."""
    extractor = TemporalFeatureExtractor(alpha=0.1)

    for i in range(10):
        t = 100.0 + i * 1.0  # delta_t = 1.0s, duration = 0.0s
        flow = _build_test_flow(t, t, bytes_src=1200, bytes_dst=0)
        feat = extractor.extract_and_update(flow)

        # Byte rate must never spike when flow durations are zero
        assert feat["temporal_byte_rate_ewma"] == 0.0
        # Flow rate should track inter-arrival time (1 flow/sec)
        assert 0.0 <= feat["temporal_flow_rate_ewma"] <= 1.5


def test_temporal_strictly_increasing_timestamps():
    """Verify standard chronological flow stream with positive durations."""
    extractor = TemporalFeatureExtractor(alpha=0.1)

    # Flow 1 at t=10.0, duration=2.0s, 1000 bytes
    f1 = _build_test_flow(10.0, 12.0, bytes_src=1000, bytes_dst=0)
    extractor.extract_and_update(f1)

    # Flow 2 at t=14.0 (delta_t=4.0s), duration=1.0s, 600 bytes
    f2 = _build_test_flow(14.0, 15.0, bytes_src=600, bytes_dst=0)
    feat2 = extractor.extract_and_update(f2)

    # Reads prior state from f1: initial flow rate 1/2.0=0.5, byte rate 0.1 * (1000/2)=50.0
    assert feat2["temporal_flow_rate_ewma"] == pytest.approx(0.5, rel=1e-3)
    assert feat2["temporal_byte_rate_ewma"] == pytest.approx(50.0, rel=1e-3)

    # Flow 3 at t=18.0 (delta_t=4.0s)
    f3 = _build_test_flow(18.0, 19.0, bytes_src=600, bytes_dst=0)
    feat3 = extractor.extract_and_update(f3)
    assert feat3["temporal_flow_rate_ewma"] > 0.0
    assert feat3["temporal_byte_rate_ewma"] > 0.0


def test_temporal_identical_timestamps():
    """Verify concurrent/simultaneous flows with delta_t=0 do not divide by zero."""
    extractor = TemporalFeatureExtractor(alpha=0.1)

    # Multiple flows arriving at the exact same timestamp
    f1 = _build_test_flow(50.0, 50.0, bytes_src=500, bytes_dst=0)
    extractor.extract_and_update(f1)

    f2 = _build_test_flow(50.0, 50.0, bytes_src=500, bytes_dst=0)
    feat2 = extractor.extract_and_update(f2)
    assert feat2["temporal_flow_rate_ewma"] == 0.0
    assert feat2["temporal_byte_rate_ewma"] == 0.0

    f3 = _build_test_flow(50.0, 50.0, bytes_src=500, bytes_dst=0)
    feat3 = extractor.extract_and_update(f3)
    assert feat3["temporal_flow_rate_ewma"] == 0.0
    assert feat3["temporal_byte_rate_ewma"] == 0.0


def test_temporal_finite_nonnegative_rate_outputs():
    """Verify all temporal features remain strictly finite and non-negative across arbitrary edge flows."""
    import math
    extractor = TemporalFeatureExtractor(alpha=0.2)

    test_cases = [
        (10.0, 10.0, 0, 0),       # zero duration, zero bytes
        (10.0, 10.0, 1500, 500),  # zero delta_t, zero duration, large bytes
        (10.5, 10.5, 200, 100),   # small delta_t, zero duration
        (12.0, 14.0, 800, 400),   # positive delta_t, positive duration
        (12.0, 12.0, 100, 50),    # out-of-order / non-monotonic timestamp
        (20.0, 20.0, 10000, 0),   # large delta_t, zero duration, huge bytes
    ]

    for ts_start, ts_end, b_src, b_dst in test_cases:
        flow = _build_test_flow(ts_start, ts_end, bytes_src=b_src, bytes_dst=b_dst)
        features = extractor.extract_and_update(flow)
        for name in TEMPORAL_FEATURE_NAMES:
            val = features[name]
            assert math.isfinite(val), f"Feature {name} produced non-finite value: {val}"
            assert val >= 0.0, f"Feature {name} produced negative value: {val}"

