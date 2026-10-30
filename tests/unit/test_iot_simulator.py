"""Unit tests for IoT Network Traffic Simulator Subsystem."""
from __future__ import annotations

import pytest
import numpy as np

from iot_ids.simulator.devices import DeviceType, create_default_iot_network, IoTDevice
from iot_ids.simulator.scenarios import ScenarioType, get_scenario, SimulationScenario
from iot_ids.simulator.generator import IoTSimulator, GeneratedPacket


def test_default_iot_network_topology():
    devices = create_default_iot_network()
    assert len(devices) == 8
    
    types = [d.device_type for d in devices]
    assert types.count(DeviceType.ENVIRONMENTAL_SENSOR) == 2
    assert types.count(DeviceType.SMART_CAMERA) == 2
    assert types.count(DeviceType.SMART_CONTROLLER) == 2
    assert types.count(DeviceType.INDUSTRIAL_GATEWAY) == 2

    for dev in devices:
        assert dev.ip_address.startswith("192.168.1.")
        assert len(dev.mac_address.split(":")) == 6
        assert dev.status == "ONLINE"
        assert dev.nominal_rate_pps > 0.0
        d_dict = dev.to_dict()
        assert d_dict["device_id"] == dev.device_id
        assert d_dict["ip_address"] == dev.ip_address


def test_scenario_retrieval_and_switching():
    benign = get_scenario(ScenarioType.BENIGN_NORMAL)
    assert benign.scenario_type == ScenarioType.BENIGN_NORMAL
    assert benign.ground_truth_label == 0

    mirai = get_scenario(ScenarioType.MIRAI_BOTNET_FLOOD)
    assert mirai.scenario_type == ScenarioType.MIRAI_BOTNET_FLOOD
    assert mirai.ground_truth_label == 1

    slowloris = get_scenario("SLOWLORIS_DOS")
    assert slowloris.scenario_type == ScenarioType.SLOWLORIS_DOS

    fallback = get_scenario("NON_EXISTENT_SCENARIO")
    assert fallback.scenario_type == ScenarioType.BENIGN_NORMAL


def test_simulator_deterministic_generation():
    sim1 = IoTSimulator(seed=42)
    pkts1 = sim1.generate_batch(count=20)

    sim2 = IoTSimulator(seed=42)
    pkts2 = sim2.generate_batch(count=20)

    assert len(pkts1) == 20
    assert len(pkts2) == 20

    for p1, p2 in zip(pkts1, pkts2):
        assert p1.src_ip == p2.src_ip
        assert p1.dst_ip == p2.dst_ip
        assert p1.src_port == p2.src_port
        assert p1.dst_port == p2.dst_port
        assert p1.proto == p2.proto
        assert p1.length == p2.length
        assert p1.ground_truth == p2.ground_truth
        assert p1.scenario_name == p2.scenario_name


def test_simulator_attack_packet_injection():
    sim = IoTSimulator(seed=99)
    sim.set_scenario(ScenarioType.MIRAI_BOTNET_FLOOD)
    
    pkts = sim.generate_batch(count=30)
    attack_pkts = [p for p in pkts if p.ground_truth == 1]
    
    assert len(attack_pkts) > 0
    for ap in attack_pkts:
        assert ap.scenario_name == ScenarioType.MIRAI_BOTNET_FLOOD.value
        assert ap.proto == "tcp"
        assert ap.syn == 1


def test_generated_packet_to_dict_and_scapy():
    pkt = GeneratedPacket(
        timestamp=100.0,
        src_ip="192.168.1.10",
        dst_ip="10.0.0.1",
        src_port=12345,
        dst_port=80,
        proto="tcp",
        length=64,
        syn=1,
        ack=0,
        payload="SYN_TEST",
        ground_truth=1,
        scenario_name="TEST_SCENARIO",
        source_device_id="sensor_01",
    )

    p_dict = pkt.to_dict()
    assert p_dict["timestamp"] == 100.0
    assert p_dict["src_ip"] == "192.168.1.10"
    assert p_dict["ground_truth"] == 1

    scapy_frame = pkt.to_scapy_packet()
    if scapy_frame is not None:
        assert scapy_frame.haslayer("IP")
        assert scapy_frame["IP"].src == "192.168.1.10"


def test_simulator_lifecycle_controls():
    sim = IoTSimulator(seed=42)
    assert sim.running is False

    sim.start()
    assert sim.running is True
    assert sim.paused is False

    sim.pause()
    assert sim.paused is True

    sim.resume()
    assert sim.paused is False

    sim.stop()
    assert sim.running is False

    sim.generate_batch(count=10)
    assert sim.packets_generated > 0

    sim.reset()
    assert sim.packets_generated == 0
    assert sim.running is False
