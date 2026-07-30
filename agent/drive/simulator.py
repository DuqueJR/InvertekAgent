"""In-memory Optidrive E3 stand-in for development and demos.

Behaves like the real drive as documented in Section 8.4 of the IP20 User
Guide: same register semantics, same scaling, plus the full last-4 trip log
that real hardware only exposes on the keypad (P00-13).
"""

import json
import random
import time
from pathlib import Path

from . import registers as regs
from .base import (
    DriveClient,
    DriveSafetyError,
    DriveStatus,
    TripEntry,
    fault_lookup,
    state_label,
)
from .scenarios import (
    DEFAULT_SCENARIO,
    NOMINAL_DC_BUS_V,
    NOMINAL_HEATSINK_C,
    RESET_INHIBIT_S,
    Scenario,
)

KB_PARAMETERS_PATH = Path(__file__).parent.parent / "data" / "parameters.json"

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
    def __init__(self, scenario: Scenario = None, seed=None, clock=time.monotonic):
        self._connected = False
        self._running = False
        self._params = _seed_parameters()
        self.fail_next_write = False
        self._rng = random.Random(seed)
        self._clock = clock
        self._armed: Scenario = None
        self._tripped_at = None
        # A fresh client reproduces the documented demo opener; other
        # scenarios arrive via apply_scenario/arm_scenario.
        self._scenario = scenario or DEFAULT_SCENARIO
        self._apply_scenario_state(self._scenario, set_params=scenario is not None)

    # -- scenarios -----------------------------------------------------
    def _apply_param_overrides(self, scenario: Scenario) -> None:
        """Put the scenario's misconfiguration into the parameter bank."""
        for code, display in (scenario.param_overrides or {}).items():
            spec = _registry().get(code)
            if spec is None:
                continue
            try:
                self._params[code] = spec.to_raw(display)
            except (ValueError, ArithmeticError):
                continue

    def _apply_scenario_state(self, scenario: Scenario, set_params=True) -> None:
        self._scenario = scenario
        self._tripped = True
        self._running = False
        self._fault_number = scenario.fault_number
        self._trip_log = list(scenario.trip_log)[:4]
        self._tripped_at = self._clock()
        if set_params:
            self._apply_param_overrides(scenario)

    def apply_scenario(self, scenario: Scenario) -> None:
        """Trip the drive now, with this scenario's conditions and causes."""
        self._apply_scenario_state(scenario)

    def arm_scenario(self, scenario: Scenario) -> None:
        """Make the fault occur on the next start attempt, not now.

        The cause is installed immediately — a misconfigured drive is already
        misconfigured before anyone presses Run — while the trip itself waits
        for the start attempt. Without this the arm would silently do nothing
        whenever the parameter still held a healthy default, because the
        scenario would read as already fixed.

        The arm persists so the drive trips on *every* start until the cause
        is corrected, which is what "it trips every time the motor starts"
        actually looks like.
        """
        self._armed = scenario
        self._apply_param_overrides(scenario)

    @property
    def armed_scenario(self):
        return self._armed

    @property
    def scenario(self):
        return self._scenario

    def _display_of(self, code: str):
        """Current display value of a parameter, for a scenario's fix check."""
        spec = _registry().get(code)
        raw = self._params.get(code)
        if spec is None or raw is None:
            return None
        return spec.to_display(raw)

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
        # DC bus and temperature keep reading after a trip on a real drive, so
        # a voltage or thermal fault stays diagnosable with the output off.
        dc_bus = float(NOMINAL_DC_BUS_V)
        temp = float(NOMINAL_HEATSINK_C)
        if self._tripped and self._scenario is not None:
            dc_bus = float(self._scenario.dc_bus_v)
            temp = float(self._scenario.heatsink_temp_c)
        if self._running:
            setpoint = self._params.get("P-01") or int(
                DEFAULT_FREQ_SETPOINT_HZ * regs.FREQ_SCALE
            )
            freq = round(
                min(setpoint, DEFAULT_FREQ_SETPOINT_HZ * regs.FREQ_SCALE)
                / regs.FREQ_SCALE
                + self._rng.uniform(-0.2, 0.2),
                1,
            )
            current = round(2.0 + self._rng.uniform(-0.15, 0.15), 2)
            dc_bus = round(NOMINAL_DC_BUS_V + self._rng.uniform(-4, 4), 1)
            temp = round(NOMINAL_HEATSINK_C + self._rng.uniform(-1.5, 1.5), 1)
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
            dc_bus_v=dc_bus,
            heatsink_temp_c=temp,
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
    def simulate_run(self) -> bool:
        """Attempt to start. Returns False if an armed fault tripped it.

        An armed scenario keeps tripping the drive on every start attempt
        until its cause is corrected, so approving the right parameter change
        is what finally gets the motor turning.
        """
        armed = self._armed
        if armed is not None and not armed.is_fixed(self._display_of):
            self._apply_scenario_state(armed, set_params=False)
            self._trip_log.insert(0, armed.fault_number)
            del self._trip_log[4:]
            return False
        self._armed = None
        self._tripped = False
        self._fault_number = 0
        self._running = True
        return True

    def simulate_stop(self) -> None:
        self._running = False

    def simulate_trip(self, fault_number: int) -> None:
        self._running = False
        self._tripped = True
        self._fault_number = int(fault_number)
        self._trip_log.insert(0, int(fault_number))
        del self._trip_log[4:]
        self._tripped_at = self._clock()

    @property
    def reset_blocked_for_s(self) -> float:
        """Seconds still to wait before this trip can be reset."""
        scenario = self._scenario
        if (
            not self._tripped
            or scenario is None
            or not scenario.reset_inhibited
            or self._tripped_at is None
        ):
            return 0.0
        remaining = RESET_INHIBIT_S - (self._clock() - self._tripped_at)
        return max(0.0, remaining)

    def reset_fault(self) -> None:
        remaining = self.reset_blocked_for_s
        if remaining > 0:
            # Section 10.1 p.39: after an over-current or overload trip
            # (3, 4, 15) the drive cannot be reset until the inbuilt delay
            # has elapsed, to let the power components recover.
            raise DriveSafetyError(
                f"This trip cannot be reset yet: a delay time is inbuilt to "
                f"let the drive's power components recover. Wait "
                f"{remaining:.0f} more second(s) and reset again."
            )
        self._tripped = False
        self._fault_number = 0
