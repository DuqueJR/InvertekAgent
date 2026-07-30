"""Drive client interface shared by the simulator and the serial client."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

FAULT_CODES_PATH = Path(__file__).parent.parent / "data" / "fault_codes.json"


class DriveError(Exception):
    """Base class for drive communication problems."""


class DriveNotConnected(DriveError):
    """An operation was attempted before connect() succeeded."""


class DriveSafetyError(DriveError):
    """A safety gate refused the operation (e.g. drive still running)."""


@lru_cache(maxsize=1)
def _fault_table() -> dict:
    payload = json.loads(FAULT_CODES_PATH.read_text(encoding="utf-8"))
    table = {}
    for fault in payload.get("faults", []):
        try:
            number = int(fault.get("display_number", ""))
        except (TypeError, ValueError):
            continue
        table[number] = fault
    return table


def fault_lookup(number: int) -> tuple[str, str]:
    """Numeric drive error code -> (printed code, name) from the KB."""
    fault = _fault_table().get(int(number))
    if fault is None:
        return f"{int(number):02d}", "Unknown fault code"
    return fault.get("code", f"{int(number):02d}"), fault.get("name", "Unknown")


def fault_source(number: int) -> str:
    """Citation for a fault code, so trip diagnoses are traceable too."""
    fault = _fault_table().get(int(number))
    source = (fault or {}).get("source")
    if not isinstance(source, dict):
        return ""
    parts = [source.get("document"), source.get("section")]
    page = source.get("page")
    if page not in (None, ""):
        parts.append(f"p.{page}")
    return ", ".join(str(p) for p in parts if p)


@dataclass
class DriveStatus:
    connected: bool = False
    running: bool = False
    tripped: bool = False
    standby: bool = False
    ready: bool = False
    state_label: str = "Disconnected"
    fault_number: int = 0
    fault_code: str = ""
    fault_name: str = ""
    output_freq_hz: float = 0.0
    output_current_a: float = 0.0
    # Register-backed measurements (Section 8.4 pp.32-35): DC bus voltage is
    # register 23 (P00-08) and drive temperature register 24 (P00-09). Unlike
    # frequency and current, these keep reading after a trip, which is what
    # makes a voltage or thermal fault diagnosable once the output is off.
    dc_bus_v: float = 0.0
    heatsink_temp_c: float = 0.0

    def to_dict(self) -> dict:
        return {
            "connected": self.connected,
            "state": self.state_label,
            "running": self.running,
            "tripped": self.tripped,
            "ready": self.ready,
            "active_fault": (
                {"number": self.fault_number, "code": self.fault_code,
                 "name": self.fault_name}
                if self.tripped else None
            ),
            "output_frequency_hz": self.output_freq_hz,
            "output_current_a": self.output_current_a,
            "dc_bus_voltage_v": self.dc_bus_v,
            "drive_temperature_c": self.heatsink_temp_c,
        }


@dataclass
class TripEntry:
    fault_number: int
    fault_code: str
    fault_name: str
    position: int  # 0 = most recent

    def to_dict(self) -> dict:
        return {
            "position": self.position,
            "number": self.fault_number,
            "code": self.fault_code,
            "name": self.fault_name,
            "source": fault_source(self.fault_number),
        }


def state_label(running: bool, tripped: bool, standby: bool) -> str:
    if tripped:
        return "Tripped"
    if running:
        return "Running"
    if standby:
        return "Standby"
    return "Stopped"


class DriveClient(ABC):
    """One drive, one client. Values in and out are raw register integers
    except read_status/read_trip_history, which return interpreted types."""

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @property
    @abstractmethod
    def is_connected(self) -> bool: ...

    @abstractmethod
    def read_status(self) -> DriveStatus: ...

    @abstractmethod
    def read_trip_history(self) -> list[TripEntry]: ...

    @abstractmethod
    def read_parameter(self, code: str) -> int: ...

    @abstractmethod
    def write_parameter(self, code: str, raw_value: int) -> None: ...

    def _require_connected(self):
        if not self.is_connected:
            raise DriveNotConnected("No drive connection is open.")
