"""IoT Device Definitions and Inventory for Realistic Environment Simulation."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any


class DeviceType(str, Enum):
    ENVIRONMENTAL_SENSOR = "ENVIRONMENTAL_SENSOR"
    SMART_CAMERA = "SMART_CAMERA"
    INDUSTRIAL_GATEWAY = "INDUSTRIAL_GATEWAY"
    SMART_CONTROLLER = "SMART_CONTROLLER"


@dataclass
class IoTDevice:
    """Represents a simulated IoT network endpoint."""
    device_id: str
    name: str
    device_type: DeviceType
    ip_address: str
    mac_address: str
    typical_ports: List[int]
    typical_protocols: List[str]
    nominal_rate_pps: float
    status: str = "ONLINE"
    firmware_version: str = "1.4.2"
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "device_type": self.device_type.value,
            "ip_address": self.ip_address,
            "mac_address": self.mac_address,
            "typical_ports": self.typical_ports,
            "typical_protocols": self.typical_protocols,
            "nominal_rate_pps": self.nominal_rate_pps,
            "status": self.status,
            "firmware_version": self.firmware_version,
            "description": self.description,
            "metadata": self.metadata,
        }


def create_default_iot_network() -> List[IoTDevice]:
    """Instantiates a realistic 8-node heterogeneous IoT network topology."""
    return [
        IoTDevice(
            device_id="dev_sensor_temp_01",
            name="Climate Sensor #1 (Lab North)",
            device_type=DeviceType.ENVIRONMENTAL_SENSOR,
            ip_address="192.168.1.101",
            mac_address="00:1a:2b:3c:4d:5e",
            typical_ports=[1883, 8883],
            typical_protocols=["tcp"],
            nominal_rate_pps=1.5,
            description="Periodic temperature and humidity telemetry via MQTT",
            metadata={"sensor_type": "DHT22", "location": "Building A - Floor 1"},
        ),
        IoTDevice(
            device_id="dev_sensor_pressure_02",
            name="Pressure Transducer #2 (Pump Room)",
            device_type=DeviceType.ENVIRONMENTAL_SENSOR,
            ip_address="192.168.1.102",
            mac_address="00:1a:2b:3c:4d:5f",
            typical_ports=[1883],
            typical_protocols=["tcp"],
            nominal_rate_pps=2.0,
            description="Industrial pipeline hydraulic pressure sensor",
            metadata={"sensor_type": "BMP388", "location": "Mechanical Vault"},
        ),
        IoTDevice(
            device_id="dev_cam_perimeter_01",
            name="Perimeter Surveillance Camera",
            device_type=DeviceType.SMART_CAMERA,
            ip_address="192.168.1.110",
            mac_address="00:1a:2b:5a:6b:7c",
            typical_ports=[554, 80, 8080],
            typical_protocols=["tcp", "udp"],
            nominal_rate_pps=15.0,
            description="1080p RTSP H.264 video stream to NVR storage",
            metadata={"fps": 30, "codec": "H.264", "resolution": "1920x1080"},
        ),
        IoTDevice(
            device_id="dev_cam_hallway_02",
            name="Access Hallway PTZ Camera",
            device_type=DeviceType.SMART_CAMERA,
            ip_address="192.168.1.111",
            mac_address="00:1a:2b:5a:6b:7d",
            typical_ports=[554, 443],
            typical_protocols=["tcp"],
            nominal_rate_pps=12.0,
            description="Motion-triggered optical stream with TLS control",
            metadata={"fps": 25, "night_vision": True},
        ),
        IoTDevice(
            device_id="dev_ctrl_hvac_01",
            name="Main Air Handler HVAC Controller",
            device_type=DeviceType.SMART_CONTROLLER,
            ip_address="192.168.1.120",
            mac_address="00:1a:2b:77:88:99",
            typical_ports=[502, 80],
            typical_protocols=["tcp"],
            nominal_rate_pps=4.0,
            description="Building automation controller via Modbus TCP",
            metadata={"bus": "Modbus TCP", "unit_id": 1, "registers": 64},
        ),
        IoTDevice(
            device_id="dev_ctrl_water_pump_02",
            name="Chilled Water Pump VFD Controller",
            device_type=DeviceType.SMART_CONTROLLER,
            ip_address="192.168.1.121",
            mac_address="00:1a:2b:77:88:9a",
            typical_ports=[502],
            typical_protocols=["tcp"],
            nominal_rate_pps=3.0,
            description="Variable Frequency Drive loop control",
            metadata={"bus": "Modbus TCP", "unit_id": 2, "max_rpm": 3600},
        ),
        IoTDevice(
            device_id="dev_gw_edge_master",
            name="Central Industrial Edge Gateway",
            device_type=DeviceType.INDUSTRIAL_GATEWAY,
            ip_address="192.168.1.1",
            mac_address="00:1a:2b:00:11:22",
            typical_ports=[53, 1883, 443, 8443],
            typical_protocols=["tcp", "udp"],
            nominal_rate_pps=25.0,
            description="NAT gateway, local MQTT broker, DNS resolver, and telemetry aggregator",
            metadata={"uplink": "Gigabit Ethernet", "broker": "Mosquitto 2.0"},
        ),
        IoTDevice(
            device_id="dev_gw_field_node_02",
            name="Field Bus Repeater Gateway",
            device_type=DeviceType.INDUSTRIAL_GATEWAY,
            ip_address="192.168.1.2",
            mac_address="00:1a:2b:00:11:23",
            typical_ports=[1883, 502],
            typical_protocols=["tcp"],
            nominal_rate_pps=8.0,
            description="Segment isolator and protocol bridge between RS-485 and Ethernet",
            metadata={"subnets": ["192.168.1.0/24", "10.0.4.0/24"]},
        ),
    ]
