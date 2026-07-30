"""In-memory Optidrive E3 stand-in for development and demos.

Behaves like the real drive as documented in Section 8.4 of the IP20 User
Guide: same register semantics, same scaling, plus the full last-4 trip log
that real hardware only exposes on the keypad (P00-13).
"""

import json
import random
from pathlib import Path

from . import registers as regs
from .base import (
    DriveClient,
    DriveStatus,
    TripEntry,
    fault_lookup,
    state_label,
)

KB_PARAMETERS_PATH = Path(__file__).parent.parent / "data" / "parameters.json"

# Demo scenario: the drive sits stopped and tripped on output over current
# (error 03, "h O-I"), with two earlier faults in the log.
DEFAULT_TRIP_LOG = [3, 3, 4, 11]
DEFAULT_FREQ_SETPOINT_HZ = 50.0


def _registry():
    try:
        from tools.ptb.registry import load_registry
    except ImportError:  # running as the agent.* package (tests)
        from agent.tools.ptb.registry import load_registry
    return load_registry("E3")


def _seed_parameters() -> dict:
    """Raw parameter bank seeded from the curated KB defaults."""
    registry = _registry()
    try:
        kb = json.loads(KB_PARAMETERS_PATH.read_text(encoding="utf-8"))
        defaults = {p["id"]: p.get("default") for p in kb.get("parameters", [])}
    except (OSError, json.JSONDecodeError):
        defaults = {}

    bank = {}
    for code, spec in registry.parameters.items():
        if spec.is_read_only:
            continue
        raw = 0
        default = defaults.get(code)
        if isinstance(default, str):
            token = default.split("(")[0].split("/")[0].strip()
            try:
                raw = spec.to_raw(float(token))
            except (ValueError, ArithmeticError):
                raw = 0
        bank[code] = raw
    return bank


class SimulatedDriveClient(DriveClient):
    def __init__(self):
        self._connected = False
        self._running = False
        self._tripped = True
        self._fault_number = DEFAULT_TRIP_LOG[0]
        self._trip_log = list(DEFAULT_TRIP_LOG)
        self._params = _seed_parameters()
        self.fail_next_write = False

    # -- lifecycle -----------------------------------------------------
    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    # -- reads ---------------------------------------------------------
    def read_status(self) -> DriveStatus:
        self._require_connected()
        freq = 0.0
        current = 0.0
        if self._running:
            setpoint = self._params.get("P-01") or int(
                DEFAULT_FREQ_SETPOINT_HZ * regs.FREQ_SCALE
            )
            freq = round(
                min(setpoint, DEFAULT_FREQ_SETPOINT_HZ * regs.FREQ_SCALE)
                / regs.FREQ_SCALE
                + random.uniform(-0.2, 0.2),
                1,
            )
            current = round(2.0 + random.uniform(-0.15, 0.15), 2)
        code, name = fault_lookup(self._fault_number)
        return DriveStatus(
            connected=True,
            running=self._running,
            tripped=self._tripped,
            standby=False,
            ready=not self._tripped,
            state_label=state_label(self._running, self._tripped, False),
            fault_number=self._fault_number,
            fault_code=code if self._tripped else "",
            fault_name=name if self._tripped else "",
            output_freq_hz=freq,
            output_current_a=current,
        )

    def read_trip_history(self) -> list[TripEntry]:
        self._require_connected()
        entries = []
        for position, number in enumerate(self._trip_log[:4]):
            code, name = fault_lookup(number)
            entries.append(TripEntry(number, code, name, position))
        return entries

    def read_parameter(self, code: str) -> int:
        self._require_connected()
        code = code.strip()
        if code not in self._params:
            raise KeyError(f"{code} is not present in the simulated drive.")
        return self._params[code]

    # -- writes ----------------------------------------------------------
    def write_parameter(self, code: str, raw_value: int) -> None:
        self._require_connected()
        code = code.strip()
        if code not in self._params:
            raise KeyError(f"{code} is not present in the simulated drive.")
        if self.fail_next_write:
            # Swallow the write so the caller's read-back verify fails,
            # exercising the same path a flaky RS485 link would.
            self.fail_next_write = False
            return
        self._params[code] = int(raw_value)

    # -- demo controls (UI only, never exposed to the model) -------------
    def simulate_run(self) -> None:
        self._tripped = False
        self._running = True

    def simulate_stop(self) -> None:
        self._running = False

    def simulate_trip(self, fault_number: int) -> None:
        self._running = False
        self._tripped = True
        self._fault_number = int(fault_number)
        self._trip_log.insert(0, int(fault_number))
        del self._trip_log[4:]

    def reset_fault(self) -> None:
        self._tripped = False
        self._fault_number = 0
