"""Simulation Scenarios for IoT Environment Traffic Generator."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any


class ScenarioType(str, Enum):
    BENIGN_NORMAL = "BENIGN_NORMAL"
    MIRAI_BOTNET_FLOOD = "MIRAI_BOTNET_FLOOD"
    SLOWLORIS_DOS = "SLOWLORIS_DOS"
    DATA_EXFILTRATION_MITM = "DATA_EXFILTRATION_MITM"
    COMMAND_INJECTION = "COMMAND_INJECTION"


@dataclass
class SimulationScenario:
    """Configuration contract for a reproducible IoT simulation scenario."""
    scenario_type: ScenarioType
    name: str
    description: str
    ground_truth_label: int  # 0 = Benign, 1 = Attack
    attack_vector: str
    target_devices: List[str]
    attacker_devices: List[str]
    nominal_duration_sec: float = 30.0
    traffic_multiplier: float = 1.0
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_type": self.scenario_type.value,
            "name": self.name,
            "description": self.description,
            "ground_truth_label": self.ground_truth_label,
            "attack_vector": self.attack_vector,
            "target_devices": self.target_devices,
            "attacker_devices": self.attacker_devices,
            "nominal_duration_sec": self.nominal_duration_sec,
            "traffic_multiplier": self.traffic_multiplier,
            "parameters": self.parameters,
        }


SCENARIOS: Dict[ScenarioType, SimulationScenario] = {
    ScenarioType.BENIGN_NORMAL: SimulationScenario(
        scenario_type=ScenarioType.BENIGN_NORMAL,
        name="Benign Operational Baseline",
        description="Standard operational traffic: periodic MQTT telemetry, RTSP video streaming, Modbus control polling, and DNS queries.",
        ground_truth_label=0,
        attack_vector="NONE",
        target_devices=[],
        attacker_devices=[],
        nominal_duration_sec=30.0,
        traffic_multiplier=1.0,
        parameters={"jitter_ms": 15.0, "packet_loss_rate": 0.001},
    ),
    ScenarioType.MIRAI_BOTNET_FLOOD: SimulationScenario(
        scenario_type=ScenarioType.MIRAI_BOTNET_FLOOD,
        name="Mirai IoT Botnet (Scan & SYN Flood)",
        description="Compromised sensors execute rapid horizontal port scanning followed by high-rate TCP SYN flood against the Industrial Gateway and HVAC Controller.",
        ground_truth_label=1,
        attack_vector="SYN_FLOOD_AND_PORT_SCAN",
        target_devices=["dev_gw_edge_master", "dev_ctrl_hvac_01"],
        attacker_devices=["dev_sensor_temp_01", "dev_cam_hallway_02"],
        nominal_duration_sec=20.0,
        traffic_multiplier=4.5,
        parameters={"syn_rate_pps": 120.0, "port_scan_range": [21, 22, 23, 80, 443, 502, 1883, 8080]},
    ),
    ScenarioType.SLOWLORIS_DOS: SimulationScenario(
        scenario_type=ScenarioType.SLOWLORIS_DOS,
        name="Slowloris Low-Rate Connection Exhaustion",
        description="Stealthy low-rate HTTP DoS maintaining incomplete request headers with maximum inter-arrival delays to starve connection pools without triggering rate thresholds.",
        ground_truth_label=1,
        attack_vector="LOW_RATE_DENIAL_OF_SERVICE",
        target_devices=["dev_gw_edge_master"],
        attacker_devices=["dev_cam_perimeter_01"],
        nominal_duration_sec=40.0,
        traffic_multiplier=0.6,
        parameters={"header_interval_sec": 8.0, "concurrent_connections": 24},
    ),
    ScenarioType.DATA_EXFILTRATION_MITM: SimulationScenario(
        scenario_type=ScenarioType.DATA_EXFILTRATION_MITM,
        name="Man-in-the-Middle & Sensor Data Exfiltration",
        description="Attacker impersonates field repeater gateway, intercepting Modbus registers and exfiltrating bulk unencrypted sensory archives to external egress.",
        ground_truth_label=1,
        attack_vector="DATA_TAMPERING_AND_EXFILTRATION",
        target_devices=["dev_ctrl_water_pump_02", "dev_gw_edge_master"],
        attacker_devices=["dev_gw_field_node_02"],
        nominal_duration_sec=25.0,
        traffic_multiplier=2.0,
        parameters={"exfil_chunk_bytes": 1420, "external_destination": "198.51.100.77"},
    ),
    ScenarioType.COMMAND_INJECTION: SimulationScenario(
        scenario_type=ScenarioType.COMMAND_INJECTION,
        name="Industrial Control Command Injection",
        description="Forged Modbus TCP Function 16 (Preset Multiple Registers) commands injected into chiller pump controller attempting unauthorized valve shutdown.",
        ground_truth_label=1,
        attack_vector="UNAUTHORIZED_PLC_CONTROL_INJECTION",
        target_devices=["dev_ctrl_water_pump_02"],
        attacker_devices=["dev_sensor_pressure_02"],
        nominal_duration_sec=15.0,
        traffic_multiplier=1.2,
        parameters={"modbus_function": 16, "target_register": 40102, "malicious_payload": "FORCED_EMERGENCY_SHUTDOWN"},
    ),
}


def get_scenario(scenario_type: ScenarioType | str) -> SimulationScenario:
    """Retrieves scenario contract by key or enum."""
    if isinstance(scenario_type, str):
        try:
            scenario_type = ScenarioType(scenario_type)
        except ValueError:
            return SCENARIOS[ScenarioType.BENIGN_NORMAL]
    return SCENARIOS.get(scenario_type, SCENARIOS[ScenarioType.BENIGN_NORMAL])
