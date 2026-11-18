"""Driver interface: every device type implements these methods.

Checks never talk to devices directly; they only see the normalized
"facts" dict returned by get_facts(). That keeps checks vendor-neutral
and makes them easy to unit-test.
"""
from abc import ABC, abstractmethod


class DeviceDriver(ABC):
    def __init__(self, host: str, username: str = "admin", password: str = "admin"):
        self.host = host
        self.username = username
        self.password = password

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def push_config(self, lines: list[str]) -> str:
        """Apply configuration lines; return device output."""

    @abstractmethod
    def get_facts(self) -> dict:
        """Return normalized facts:
        {
          "hostname": str,
          "serial": str,
          "version": str,
          "interfaces": {"Ethernet1": {"status": "up", "speed_gbps": 100}},
          "vlans": [10, 20],
          "lldp_neighbors": [{"local": "Ethernet1", "neighbor": "leaf2", "port": "Ethernet1"}],
        }
        """

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.disconnect()
