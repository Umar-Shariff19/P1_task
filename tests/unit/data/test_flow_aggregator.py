"""Unit tests for FlowAggregator engine."""

import pytest
from iot_ids.data.flow_aggregator import FlowAggregator, normalize_5tuple


def test_normalize_5tuple():
    key1, is_fw1 = normalize_5tuple("1.1.1.1", "2.2.2.2", 100, 200, "tcp")
    key2, is_fw2 = normalize_5tuple("2.2.2.2", "1.1.1.1", 200, 100, "tcp")

    assert key1 == key2
    assert is_fw1 != is_fw2


def test_flow_aggregator_reconstruction():
    aggregator = FlowAggregator(inactivity_timeout=5.0, max_flow_duration=10.0)

    # Frame 1: Forward SYN
    f1 = aggregator.process_frame(
        timestamp=100.0,
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        src_port=1234,
        dst_port=80,
        proto="tcp",
        length=60,
        syn=1,
        ack=0,
        label=1,
        attack_category="DDoS",
    )
    assert f1 is None

    # Frame 2: Reverse ACK (Response)
    f2 = aggregator.process_frame(
        timestamp=101.0,
        src_ip="10.0.0.2",
        dst_ip="10.0.0.1",
        src_port=80,
        dst_port=1234,
        proto="tcp",
        length=100,
        syn=0,
        ack=1,
        label=1,
        attack_category="DDoS",
    )
    assert f2 is None

    # Frame 3: Expired by inactivity timeout (t = 110.0 > 101.0 + 5.0)
    f3 = aggregator.process_frame(
        timestamp=110.0,
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        src_port=1234,
        dst_port=80,
        proto="tcp",
        length=50,
        label=1,
        attack_category="DDoS",
    )
    assert f3 is not None
    assert f3.pkts_src == 1
    assert f3.pkts_dst == 1
    assert f3.bytes_src == 60
    assert f3.bytes_dst == 100
    assert f3.duration == 1.0

    # Flush remaining flows
    flushed = aggregator.flush()
    assert len(flushed) == 1
    assert flushed[0].bytes_src == 50


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"inactivity_timeout": 0}, "inactivity_timeout"),
        ({"inactivity_timeout": -1}, "inactivity_timeout"),
        ({"inactivity_timeout": float("nan")}, "inactivity_timeout"),
        ({"max_flow_duration": float("inf")}, "max_flow_duration"),
        ({"max_active_flows": 0}, "max_active_flows"),
        ({"max_active_flows": 1.5}, "max_active_flows"),
        ({"max_active_flows": True}, "max_active_flows"),
    ],
)
def test_flow_aggregator_rejects_invalid_limits(kwargs, message):
    with pytest.raises(ValueError, match=message):
        FlowAggregator(**kwargs)


def test_flow_aggregator_accepts_valid_limits():
    aggregator = FlowAggregator(
        inactivity_timeout=0.5,
        max_flow_duration=2,
        max_active_flows=1,
    )

    assert aggregator.inactivity_timeout == 0.5
    assert aggregator.max_flow_duration == 2
    assert aggregator.max_active_flows == 1


def test_flow_aggregator_reverse_lexical_direction_initiator():
    """Verifies flow initiated from higher-sorting IP to lower-sorting IP preserves initiator and SYN."""
    aggregator = FlowAggregator(inactivity_timeout=5.0, max_flow_duration=10.0)

    # Frame 1: SYN from higher IP (192.168.1.101) to lower IP (192.168.1.1)
    f1 = aggregator.process_frame(
        timestamp=200.0,
        src_ip="192.168.1.101",
        dst_ip="192.168.1.1",
        src_port=46764,
        dst_port=21,
        proto="tcp",
        length=60,
        syn=1,
        ack=0,
        label=1,
        attack_category="Mirai",
    )
    assert f1 is None

    # Frame 2: Response from lower IP (192.168.1.1) to higher IP (192.168.1.101)
    f2 = aggregator.process_frame(
        timestamp=201.0,
        src_ip="192.168.1.1",
        dst_ip="192.168.1.101",
        src_port=21,
        dst_port=46764,
        proto="tcp",
        length=120,
        syn=0,
        ack=1,
        label=1,
        attack_category="Mirai",
    )
    assert f2 is None

    # Flush flow to verify attributes
    flushed = aggregator.flush()
    assert len(flushed) == 1
    flow = flushed[0]

    # Verify initiator preservation and directional statistics
    assert flow.src_host == "192.168.1.101"
    assert flow.dst_host == "192.168.1.1"
    assert flow.src_port == 46764
    assert flow.dst_port == 21
    assert flow.pkts_src == 1
    assert flow.pkts_dst == 1
    assert flow.bytes_src == 60
    assert flow.bytes_dst == 120
    assert flow.syn_count_src == 1
    assert flow.ack_count_src == 0


def test_flow_aggregator_initiator_preservation_symmetry():
    """Verifies that bidirectional connections initiated in either direction correctly preserve initiator."""
    # Test A: Initiator 10.0.0.1 -> 10.0.0.2
    agg_a = FlowAggregator(inactivity_timeout=5.0)
    agg_a.process_frame(timestamp=1.0, src_ip="10.0.0.1", dst_ip="10.0.0.2", src_port=1000, dst_port=80, proto="tcp", length=50, syn=1)
    agg_a.process_frame(timestamp=2.0, src_ip="10.0.0.2", dst_ip="10.0.0.1", src_port=80, dst_port=1000, proto="tcp", length=70, syn=0, ack=1)
    flow_a = agg_a.flush()[0]
    assert flow_a.src_host == "10.0.0.1"
    assert flow_a.dst_host == "10.0.0.2"
    assert flow_a.pkts_src == 1
    assert flow_a.pkts_dst == 1
    assert flow_a.bytes_src == 50
    assert flow_a.bytes_dst == 70
    assert flow_a.syn_count_src == 1

    # Test B: Initiator 10.0.0.2 -> 10.0.0.1
    agg_b = FlowAggregator(inactivity_timeout=5.0)
    agg_b.process_frame(timestamp=1.0, src_ip="10.0.0.2", dst_ip="10.0.0.1", src_port=2000, dst_port=80, proto="tcp", length=50, syn=1)
    agg_b.process_frame(timestamp=2.0, src_ip="10.0.0.1", dst_ip="10.0.0.2", src_port=80, dst_port=2000, proto="tcp", length=70, syn=0, ack=1)
    flow_b = agg_b.flush()[0]
    assert flow_b.src_host == "10.0.0.2"
    assert flow_b.dst_host == "10.0.0.1"
    assert flow_b.pkts_src == 1
    assert flow_b.pkts_dst == 1
    assert flow_b.bytes_src == 50
    assert flow_b.bytes_dst == 70
    assert flow_b.syn_count_src == 1

