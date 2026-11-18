"""Real driver for Arista EOS (works with free cEOS-lab in Containerlab).

EOS returns structured JSON with "| json", so no screen-scraping needed.
To support another vendor (SONiC, Cisco NX-OS), copy this file and
normalize that vendor's output into the same facts shape.
"""
import json

from netmiko import ConnectHandler

from .base import DeviceDriver


class EOSDriver(DeviceDriver):
    def connect(self) -> None:
        self.conn = ConnectHandler(
            device_type="arista_eos",
            host=self.host,
            username=self.username,
            password=self.password,
            conn_timeout=10,
        )
        self.conn.enable()

    def disconnect(self) -> None:
        self.conn.disconnect()

    def push_config(self, lines: list[str]) -> str:
        out = self.conn.send_config_set(lines)
        self.conn.save_config()
        return out

    def _json(self, cmd: str) -> dict:
        return json.loads(self.conn.send_command(f"{cmd} | json"))

    def get_facts(self) -> dict:
        ver = self._json("show version")
        intf = self._json("show interfaces status")["interfaceStatuses"]
        vlans = self._json("show vlan")["vlans"]
        lldp = self._json("show lldp neighbors")["lldpNeighbors"]
        return {
            "hostname": self._json("show hostname")["hostname"],
            "serial": ver.get("serialNumber", ""),
            "version": ver["version"],
            "interfaces": {
                name: {
                    "status": "up" if d["linkStatus"] == "connected" else "down",
                    "speed_gbps": int(d.get("bandwidth", 0)) // 1_000_000_000,
                }
                for name, d in intf.items()
            },
            "vlans": sorted(int(v) for v in vlans),
            "lldp_neighbors": [
                {"local": n["port"], "neighbor": n["neighborDevice"], "port": n["neighborPort"]}
                for n in lldp
            ],
        }
