"""Configurable Real-Time IoT Environment Traffic Generator Engine."""
from __future__ import annotations

import io
import threading
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Iterator
import numpy as np

from iot_ids.simulator.devices import IoTDevice, DeviceType, create_default_iot_network
from iot_ids.simulator.scenarios import SimulationScenario, ScenarioType, get_scenario


@dataclass
class GeneratedPacket:
    """Standardized synthetic packet representation for IDS ingestion."""
    timestamp: float
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    proto: str
    length: int
    syn: int = 0
    ack: int = 0
    fin: int = 0
    rst: int = 0
    payload: str = ""
    ground_truth: int = 0  # 0 = Benign, 1 = Attack
    scenario_name: str = "BENIGN_NORMAL"
    source_device_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "src_port": self.src_port,
            "dst_port": self.dst_port,
            "proto": self.proto,
            "length": self.length,
            "syn": self.syn,
            "ack": self.ack,
            "fin": self.fin,
            "rst": self.rst,
            "payload": self.payload,
            "ground_truth": self.ground_truth,
            "scenario_name": self.scenario_name,
            "source_device_id": self.source_device_id,
        }

    def to_scapy_packet(self) -> Any:
        """Converts into a Scapy frame if Scapy is available."""
        try:
            from scapy.layers.inet import IP, TCP, UDP
            from scapy.layers.l2 import Ether
            from scapy.packet import Raw

            eth = Ether()
            ip = IP(src=self.src_ip, dst=self.dst_ip)
            if self.proto == "tcp":
                flags = ""
                if self.syn: flags += "S"
                if self.ack: flags += "A"
                if self.fin: flags += "F"
                if self.rst: flags += "R"
                transport = TCP(sport=self.src_port, dport=self.dst_port, flags=flags or "A")
            else:
                transport = UDP(sport=self.src_port, dport=self.dst_port)

            raw_bytes = self.payload.encode("utf-8") if self.payload else b"\x00" * max(0, self.length - 40)
            return eth / ip / transport / Raw(load=raw_bytes)
        except ImportError:
            return None


class IoTSimulator:
    """Configurable, multi-device IoT traffic simulation engine.

    Generates realistic benign baseline telemetry and controlled laboratory attack scenarios
    with deterministic seeding, device tracking, and flow protocol fidelity.
    """

    def __init__(
        self,
        devices: Optional[List[IoTDevice]] = None,
        scenario: Optional[SimulationScenario | ScenarioType | str] = None,
        seed: int = 42,
        traffic_intensity: float = 1.0,
    ):
        self.devices = devices if devices is not None else create_default_iot_network()
        self.device_map = {d.device_id: d for d in self.devices}
        self.device_by_ip = {d.ip_address: d for d in self.devices}

        if scenario is None:
            self.scenario = get_scenario(ScenarioType.BENIGN_NORMAL)
        elif isinstance(scenario, (ScenarioType, str)):
            self.scenario = get_scenario(scenario)
        else:
            self.scenario = scenario

        self.seed = int(seed)
        self.rng = np.random.default_rng(self.seed)
        self.traffic_intensity = max(0.1, float(traffic_intensity))

        # Runtime State
        self.status: str = "IDLE"  # IDLE, RUNNING, PAUSED, STOPPED
        self.sim_time: float = 0.0
        self.packets_generated: int = 0
        self.flows_generated: int = 0
        self._lock = threading.Lock()

        # Ephemeral active connection states
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self._packet_buffer: List[GeneratedPacket] = []

    @property
    def running(self) -> bool:
        return self.status == "RUNNING"

    @property
    def paused(self) -> bool:
        return self.status == "PAUSED"

    def set_scenario(self, scenario: SimulationScenario | ScenarioType | str) -> SimulationScenario:
        """Dynamically switches the active scenario."""
        with self._lock:
            if isinstance(scenario, (ScenarioType, str)):
                self.scenario = get_scenario(scenario)
            else:
                self.scenario = scenario
            self._packet_buffer.clear()
            self._active_sessions.clear()
            self.traffic_intensity = float(self.scenario.traffic_multiplier)
            return self.scenario

    def set_seed(self, seed: int) -> None:
        """Reseeds the generator for exact deterministic reproducibility."""
        with self._lock:
            self.seed = int(seed)
            self.rng = np.random.default_rng(self.seed)

    def start(self) -> None:
        with self._lock:
            self.status = "RUNNING"

    def pause(self) -> None:
        with self._lock:
            if self.status == "RUNNING":
                self.status = "PAUSED"

    def resume(self) -> None:
        with self._lock:
            if self.status == "PAUSED":
                self.status = "RUNNING"

    def stop(self) -> None:
        with self._lock:
            self.status = "STOPPED"

    def reset(self) -> None:
        with self._lock:
            self.status = "IDLE"
            self.sim_time = 0.0
            self.packets_generated = 0
            self.flows_generated = 0
            self._active_sessions.clear()
            self._packet_buffer.clear()
            self.rng = np.random.default_rng(self.seed)
            self.scenario = get_scenario(ScenarioType.BENIGN_NORMAL)
            self.traffic_intensity = 1.0

    def step(self, dt_seconds: float = 1.0) -> List[GeneratedPacket]:
        """Generates synthetic packets for a specified time step dt."""
        with self._lock:
            if self.status not in ("RUNNING", "IDLE"):
                return []
            packets = self._generate_window_packets(self.sim_time, self.sim_time + dt_seconds)
            self.sim_time += dt_seconds
            self.packets_generated += len(packets)
            return packets

    def generate_batch(self, count: int = 50) -> List[GeneratedPacket]:
        """Generates a discrete batch of packets under the current scenario."""
        with self._lock:
            while len(self._packet_buffer) < count:
                step_pkts = self._generate_window_packets(self.sim_time, self.sim_time + 1.0)
                self.sim_time += 1.0
                self._packet_buffer.extend(step_pkts)
            result = self._packet_buffer[:count]
            self._packet_buffer = self._packet_buffer[count:]
            self.packets_generated += len(result)
            return result

    def _generate_window_packets(self, t_start: float, t_end: float) -> List[GeneratedPacket]:
        """Generates realistic interleaved benign and attack packets for interval [t_start, t_end]."""
        packets: List[GeneratedPacket] = []
        duration = t_end - t_start

        # 1. Generate Benign Baseline Traffic for non-attacker online devices
        for dev in self.devices:
            if dev.status != "ONLINE":
                continue
            if self.scenario.ground_truth_label == 1 and dev.device_id in self.scenario.attacker_devices:
                # Compromised device dedicated to attack execution during malicious scenario
                continue

            rate = dev.nominal_rate_pps * self.traffic_intensity
            expected_pkts = int(self.rng.poisson(rate * duration))

            for _ in range(expected_pkts):
                t_pkt = t_start + float(self.rng.uniform(0.0, duration))
                pkt = self._create_benign_packet(dev, t_pkt)
                packets.append(pkt)

        # 2. Inject Attack Scenario Traffic if scenario is malicious
        if self.scenario.ground_truth_label == 1:
            attack_pkts = self._inject_scenario_attack_packets(t_start, t_end)
            packets.extend(attack_pkts)

        # Chronologically sort all packets in this time window
        packets.sort(key=lambda p: p.timestamp)
        return packets

    def _create_benign_packet(self, dev: IoTDevice, timestamp: float) -> GeneratedPacket:
        """Synthesizes a realistic protocol-compliant benign packet from a specific IoT device."""
        gw_ip = "192.168.1.1"

        sess = self._active_sessions.setdefault(dev.device_id, {
            "src_port": int(self.rng.integers(49152, 65535)),
            "dst_port": int(self.rng.choice(dev.typical_ports) if dev.typical_ports else 1883),
            "pkt_count": 0,
        })
        sess["pkt_count"] += 1

        if dev.device_type == DeviceType.ENVIRONMENTAL_SENSOR:
            # Periodic MQTT telemetry (QoS 0 or 1)
            dst_ip = gw_ip
            dst_port = sess["dst_port"]
            length = int(self.rng.integers(64, 180))
            payload = f'{{"device":"{dev.device_id}","temp":{self.rng.uniform(20.0, 24.5):.2f},"humidity":{self.rng.uniform(45.0, 55.0):.1f}}}'
            return GeneratedPacket(
                timestamp=timestamp,
                src_ip=dev.ip_address,
                dst_ip=dst_ip,
                src_port=sess["src_port"],
                dst_port=dst_port,
                proto="tcp",
                length=length,
                syn=0,
                ack=1,
                payload=payload,
                ground_truth=0,
                scenario_name=self.scenario.scenario_type.value,
                source_device_id=dev.device_id,
            )

        elif dev.device_type == DeviceType.SMART_CAMERA:
            # RTSP / TCP high-bandwidth video frame packets
            dst_ip = "192.168.1.50"  # NVR Server
            dst_port = 554
            length = int(self.rng.integers(800, 1460))
            payload = f"RTSP/1.0 DATA seq={sess['pkt_count']} frame_chunk={self.rng.integers(1, 100)}"
            return GeneratedPacket(
                timestamp=timestamp,
                src_ip=dev.ip_address,
                dst_ip=dst_ip,
                src_port=sess["src_port"],
                dst_port=dst_port,
                proto="tcp",
                length=length,
                syn=0,
                ack=1,
                payload=payload,
                ground_truth=0,
                scenario_name=self.scenario.scenario_type.value,
                source_device_id=dev.device_id,
            )

        elif dev.device_type == DeviceType.SMART_CONTROLLER:
            # Modbus TCP periodic query / response
            dst_ip = "192.168.1.1"
            dst_port = 502
            length = int(self.rng.integers(70, 120))
            payload = f"MBTCP_RESP unit={dev.metadata.get('unit_id', 1)} fc=3 reg_count=8"
            return GeneratedPacket(
                timestamp=timestamp,
                src_ip=dev.ip_address,
                dst_ip=dst_ip,
                src_port=sess["src_port"],
                dst_port=dst_port,
                proto="tcp",
                length=length,
                syn=0,
                ack=1,
                payload=payload,
                ground_truth=0,
                scenario_name=self.scenario.scenario_type.value,
                source_device_id=dev.device_id,
            )

        else:
            # Industrial Gateway: DNS background lookup
            dst_ip = "8.8.8.8"
            dst_port = 53
            length = int(self.rng.integers(60, 95))
            payload = "DNS_QUERY a.root-servers.net"
            return GeneratedPacket(
                timestamp=timestamp,
                src_ip=dev.ip_address,
                dst_ip=dst_ip,
                src_port=sess["src_port"],
                dst_port=dst_port,
                proto="udp",
                length=length,
                syn=0,
                ack=0,
                payload=payload,
                ground_truth=0,
                scenario_name=self.scenario.scenario_type.value,
                source_device_id=dev.device_id,
            )

    def _inject_scenario_attack_packets(self, t_start: float, t_end: float) -> List[GeneratedPacket]:
        """Synthesizes attack packets matching the specific active threat scenario."""
        attack_packets: List[GeneratedPacket] = []
        duration = t_end - t_start
        stype = self.scenario.scenario_type

        if stype == ScenarioType.MIRAI_BOTNET_FLOOD:
            # Rapid SYN flood and horizontal port scanning
            syn_rate = float(self.scenario.parameters.get("syn_rate_pps", 60.0)) * self.traffic_intensity
            num_attack_pkts = int(self.rng.poisson(syn_rate * duration))
            scan_ports = self.scenario.parameters.get("port_scan_range", [22, 23, 80, 502, 1883, 8080])

            attacker_ip = self.device_map.get("dev_sensor_temp_01", self.devices[0]).ip_address
            target_ip = self.device_map.get("dev_gw_edge_master", self.devices[-1]).ip_address

            for _ in range(num_attack_pkts):
                t_pkt = t_start + float(self.rng.uniform(0.0, duration))
                dport = int(self.rng.choice(scan_ports))
                sport = int(self.rng.integers(1024, 65535))
                # SYN flood signature: small 60-byte frame, SYN=1, ACK=0
                attack_packets.append(
                    GeneratedPacket(
                        timestamp=t_pkt,
                        src_ip=attacker_ip,
                        dst_ip=target_ip,
                        src_port=sport,
                        dst_port=dport,
                        proto="tcp",
                        length=60,
                        syn=1,
                        ack=0,
                        fin=0,
                        rst=0,
                        payload="MIRAI_SCAN_PROBE",
                        ground_truth=1,
                        scenario_name=stype.value,
                        source_device_id="dev_sensor_temp_01",
                    )
                )

        elif stype == ScenarioType.SLOWLORIS_DOS:
            # Low-rate connection starvation
            attacker_ip = self.device_map.get("dev_cam_perimeter_01", self.devices[0]).ip_address
            target_ip = "192.168.1.1"
            sport = int(self.rng.integers(58900, 58950))
            t_syn = t_start + float(self.rng.uniform(0.0, 0.05))
            attack_packets.append(
                GeneratedPacket(
                    timestamp=t_syn,
                    src_ip=attacker_ip,
                    dst_ip=target_ip,
                    src_port=sport,
                    dst_port=80,
                    proto="tcp",
                    length=60,
                    syn=1,
                    ack=0,
                    fin=0,
                    rst=0,
                    payload="",
                    ground_truth=1,
                    scenario_name=stype.value,
                    source_device_id="dev_cam_perimeter_01",
                )
            )
            for h in range(int(self.rng.integers(2, 4))):
                t_hdr = t_syn + 0.01 * (h + 1)
                attack_packets.append(
                    GeneratedPacket(
                        timestamp=t_hdr,
                        src_ip=attacker_ip,
                        dst_ip=target_ip,
                        src_port=sport,
                        dst_port=80,
                        proto="tcp",
                        length=72,
                        syn=0,
                        ack=1,
                        fin=0,
                        rst=0,
                        payload=f"X-a: {h}\r\n",
                        ground_truth=1,
                        scenario_name=stype.value,
                        source_device_id="dev_cam_perimeter_01",
                    )
                )

        elif stype == ScenarioType.DATA_EXFILTRATION_MITM:
            # Abnormal large chunk exfiltration to external IP
            attacker_ip = self.device_map.get("dev_gw_field_node_02", self.devices[0]).ip_address
            external_ip = self.scenario.parameters.get("external_destination", "198.51.100.77")
            sport = int(self.rng.integers(54000, 56000))

            # Periodic exfiltration streams across the 1-second interval
            burst_offsets = [float(self.rng.uniform(0.01, 0.05)), float(self.rng.uniform(0.35, 0.45))]
            for b_idx, offset in enumerate(burst_offsets):
                t_syn = t_start + offset
                burst_sport = sport + b_idx * 10
                attack_packets.append(
                    GeneratedPacket(
                        timestamp=t_syn,
                        src_ip=attacker_ip,
                        dst_ip=external_ip,
                        src_port=burst_sport,
                        dst_port=443,
                        proto="tcp",
                        length=60,
                        syn=1,
                        ack=0,
                        fin=0,
                        rst=0,
                        payload="",
                        ground_truth=1,
                        scenario_name=stype.value,
                        source_device_id="dev_gw_field_node_02",
                    )
                )
                num_chunks = int(self.rng.integers(3, 5))
                for c in range(num_chunks):
                    t_chunk = t_syn + 0.005 * (c + 1)
                    attack_packets.append(
                        GeneratedPacket(
                            timestamp=t_chunk,
                            src_ip=attacker_ip,
                            dst_ip=external_ip,
                            src_port=burst_sport,
                            dst_port=443,
                            proto="tcp",
                            length=1420,  # Max MTU payload chunk
                            syn=0,
                            ack=1,
                            fin=0,
                            rst=0,
                            payload="EXFIL_RAW_SENSORY_ARCHIVE_CHUNK_ENCRYPTED",
                            ground_truth=1,
                            scenario_name=stype.value,
                            source_device_id="dev_gw_field_node_02",
                        )
                    )

        elif stype == ScenarioType.COMMAND_INJECTION:
            # Forged Modbus Function 16 Write Multiple Registers
            attacker_ip = self.device_map.get("dev_sensor_pressure_02", self.devices[0]).ip_address
            target_ip = self.device_map.get("dev_ctrl_water_pump_02", self.devices[0]).ip_address
            sport = int(self.rng.integers(50200, 50300))

            # Periodic command injection override bursts across the 1-second interval
            burst_offsets = [float(self.rng.uniform(0.01, 0.05)), float(self.rng.uniform(0.35, 0.45))]
            for b_idx, offset in enumerate(burst_offsets):
                t_syn = t_start + offset
                burst_sport = sport + b_idx * 10
                attack_packets.append(
                    GeneratedPacket(
                        timestamp=t_syn,
                        src_ip=attacker_ip,
                        dst_ip=target_ip,
                        src_port=burst_sport,
                        dst_port=502,
                        proto="tcp",
                        length=60,
                        syn=1,
                        ack=0,
                        fin=0,
                        rst=0,
                        payload="",
                        ground_truth=1,
                        scenario_name=stype.value,
                        source_device_id="dev_sensor_pressure_02",
                    )
                )
                num_writes = int(self.rng.integers(2, 4))
                for w in range(num_writes):
                    t_w = t_syn + 0.005 * (w + 1)
                    attack_packets.append(
                        GeneratedPacket(
                            timestamp=t_w,
                            src_ip=attacker_ip,
                            dst_ip=target_ip,
                            src_port=burst_sport,
                            dst_port=502,
                            proto="tcp",
                            length=98,
                            syn=0,
                            ack=1,
                            fin=0,
                            rst=0,
                            payload="MBTCP_FC16_PRESET_REGS:REG40102=0xDEAD_FORCE_VALVE_CLOSE",
                            ground_truth=1,
                            scenario_name=stype.value,
                            source_device_id="dev_sensor_pressure_02",
                        )
                    )

        return attack_packets

    def export_pcap(self, pcap_path: str, packet_count: int = 100) -> str:
        """Exports a generated packet stream to an offline PCAP file for replay testing."""
        try:
            from scapy.utils import wrpcap
            pkts = self.generate_batch(packet_count)
            scapy_pkts = [p.to_scapy_packet() for p in pkts if p.to_scapy_packet() is not None]
            wrpcap(pcap_path, scapy_pkts)
            return pcap_path
        except ImportError:
            raise RuntimeError("Scapy is required for PCAP file export")
