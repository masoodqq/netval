"""Mock switch so the whole system runs with no hardware.

Fault injection: put a keyword in the host name to simulate failures,
e.g. "leaf3-linkdown", "leaf4-badfw", "leaf5-unreachable".
"""
import random
import time

from .base import DeviceDriver


class MockDriver(DeviceDriver):
    def connect(self) -> None:
        time.sleep(random.uniform(0.05, 0.2))  # simulate SSH latency
        if "unreachable" in self.host:
            raise ConnectionError(f"{self.host}: connection timed out")
        self.config: list[str] = []

    def disconnect(self) -> None:
        pass

    def push_config(self, lines: list[str]) -> str:
        self.config.extend(lines)
        return "\n".join(f"{self.host}(config)# {line}" for line in lines)

    def get_facts(self) -> dict:
        interfaces = {f"Ethernet{i}": {"status": "up", "speed_gbps": 100} for i in range(1, 5)}
        if "linkdown" in self.host:
            interfaces["Ethernet2"]["status"] = "down"
        vlans = sorted({int(l.split()[1]) for l in self.config if l.startswith("vlan ")} | {1})
        return {
            "hostname": self.host,
            "serial": f"SN{abs(hash(self.host)) % 10**8:08d}",
            "version": "4.30.1F" if "badfw" in self.host else "4.32.0F",
            "interfaces": interfaces,
            "vlans": vlans,
            "lldp_neighbors": [{"local": "Ethernet1", "neighbor": "spine1", "port": "Ethernet1"}],
        }
