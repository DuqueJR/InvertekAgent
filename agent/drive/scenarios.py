"""Realistic fault scenarios for the Optidrive E3 simulator.

Each scenario pairs a fault code from the knowledge base with the drive
conditions and parameter state a real E3 would plausibly show when that
fault occurs, so a diagnosis has evidence to work from rather than just a
code.

Provenance discipline, following agent/tools/ptb/data/e3_registry.json:
every number below is marked either with the guide section it comes from or
`# chosen` where the guide gives no value. The knowledge base carries
`possible_causes` on only 2 of its 31 fault entries and `related_parameters`
on 4, so most telemetry values here are engineering-plausible choices, not
documented facts — correct them in this one file once a real drive is
available.

Deliberately NOT simulated, and why:
  - comms loss (12 SC-Ob5, 50 SC-F01, 51 SC-F02) — this app reads the drive
    over Modbus, so a dead link produces a confusing demo rather than a
    diagnosable fault;
  - autotune faults (40-44 AtF-01..05) — they occur only during an autotune,
    not during normal running;
  - internal memory and status codes (00 no-FLt, 10 P-dEF, 17 dAtA-F,
    19 dAtA-E) — the guide ties them to no measurable quantity;
  - IP66-only codes (05 PS-trP, 22 FAn-F, 40, 42-44) — this simulator is
    shaped after the IP20 drive.
"""

import random
from dataclasses import dataclass, field
from typing import Callable, Optional

# Healthy running values for a 230 V-class drive (P-07 defaults to 230 V).
NOMINAL_DC_BUS_V = 325        # chosen: ~230 V x sqrt(2)
NOMINAL_HEATSINK_C = 42       # chosen

# Section 10.1 p.39 (table footer): after an over-current or overload trip
# (3, 4, 15) "the drive may not be reset until the reset time delay has
# elapsed". The guide never states the duration.
RESET_INHIBIT_S = 10.0        # chosen — KB documents the lockout, not its length

# Heatsink concern threshold: P00-23 counts hours above 85 C (KB-backed).
HEATSINK_WARN_C = 85

# Register bounds from the Modbus register map, Section 8.4 pp.32-35:
# register 23 (DC bus) 0..1000 V, register 24 (temperature) 0..100 C.
DC_BUS_RANGE_V = (0, 1000)
TEMP_RANGE_C = (0, 100)


@dataclass
class Scenario:
    """One believable fault situation.

    `fixed_when` decides whether the fault still fires on a start attempt.
    It receives a getter returning the drive's current display value for a
    parameter code (or None), so scenarios stay decoupled from how the
    simulator stores its bank. `None` means the cause is physical — wiring,
    supply, motor, cooling — and no parameter change clears it.
    """

    fault_number: int
    label: str
    dc_bus_v: int
    heatsink_temp_c: int
    current_at_trip_a: float
    trip_log: tuple
    param_overrides: dict = field(default_factory=dict)
    fix_hint: str = ""
    fixed_when: Optional[Callable[[Callable[[str], Optional[float]]], bool]] = None
    reset_inhibited: bool = False

    @property
    def is_parameter_fixable(self) -> bool:
        return self.fixed_when is not None

    def is_fixed(self, get_display) -> bool:
        """True when the underlying cause no longer applies."""
        if self.fixed_when is None:
            return False
        try:
            return bool(self.fixed_when(get_display))
        except Exception:
            return False


def _at_least(code: str, threshold: float):
    def check(get):
        value = get(code)
        return value is not None and float(value) >= threshold
    return check


# --- the pool ---------------------------------------------------------------
# Two O-I entries on purpose: over-current is the most common E3 complaint and
# has genuinely different root causes, so one demo should not teach that O-I
# always means the same thing.

MOTOR_DATA_NOT_SET = Scenario(
    fault_number=3,                      # O-I, Output Over Current
    label="Overcurrent on start - motor data not set",
    dc_bus_v=NOMINAL_DC_BUS_V,
    heatsink_temp_c=48,                  # chosen
    current_at_trip_a=12.6,              # chosen: spike well above rating
    trip_log=(3, 3, 4, 11),              # recurring O-I after a thermal trip
    param_overrides={},                  # P-08 is 0.0 A from the KB default,
                                         # which is itself the root cause
    fix_hint="P-08 (motor rated current) is 0.0 A - set it to the nameplate value",
    fixed_when=_at_least("P-08", 1.0),
    reset_inhibited=True,                # Section 10.1 p.39 footer
)

ACCEL_RAMP_TOO_SHORT = Scenario(
    fault_number=3,                      # O-I
    label="Overcurrent on start - acceleration ramp too short",
    dc_bus_v=320,                        # chosen
    heatsink_temp_c=51,                  # chosen
    current_at_trip_a=14.2,              # chosen
    trip_log=(3, 3, 3, 4),
    param_overrides={"P-03": 0.5},       # 0.5 s accel into a loaded motor
    fix_hint="P-03 (acceleration ramp) is 0.5 s - lengthen it",
    fixed_when=_at_least("P-03", 5.0),
    reset_inhibited=True,
)

SHORT_CIRCUIT = Scenario(
    fault_number=15,                     # h O-I, "Fast Over-current Trip"
    label="Fast overcurrent - suspected short circuit",
    dc_bus_v=318,                        # chosen
    heatsink_temp_c=45,                  # chosen
    current_at_trip_a=24.0,              # chosen: near-instant fault current
    trip_log=(15, 15, 3),
    fix_hint="Check the motor and cable for short circuits - not a parameter fault",
    fixed_when=None,                     # physical
    reset_inhibited=True,                # Section 10.1 p.39 footer
)

REGEN_OVERVOLTAGE = Scenario(
    fault_number=6,                      # O-Volt, over voltage on DC bus
    label="Overvoltage on deceleration",
    dc_bus_v=448,                        # chosen: bus pushed up by regen
    heatsink_temp_c=44,                  # chosen
    current_at_trip_a=3.1,               # chosen
    trip_log=(6, 6, 6, 3),
    param_overrides={"P-04": 0.3, "P-34": 0},   # fast decel, braking disabled
    fix_hint="P-04 (decel ramp) is 0.3 s and P-34 (brake chopper) is off",
    # Section 10.1 p.39 names both remedies: lengthen P-04, or enable
    # dynamic braking via P-34. Either clears it.
    fixed_when=lambda get: (
        _at_least("P-04", 5.0)(get)
        or ((get("P-34") or 0) != 0)
    ),
)

SUPPLY_SAG = Scenario(
    fault_number=7,                      # U-Volt, under voltage on DC bus
    label="Undervoltage - incoming supply too low",
    dc_bus_v=196,                        # chosen: below the trip threshold
    heatsink_temp_c=38,                  # chosen
    current_at_trip_a=0.0,
    trip_log=(7, 14, 7, 7),
    fix_hint="Incoming supply voltage is too low - not a parameter fault",
    fixed_when=None,                     # physical
)

HEATSINK_OVERTEMP = Scenario(
    fault_number=8,                      # O-t, heatsink over temperature
    label="Heatsink over temperature",
    dc_bus_v=322,                        # chosen
    heatsink_temp_c=94,                  # chosen: above the 85 C P00-23 mark
    current_at_trip_a=6.8,               # chosen
    trip_log=(8, 8, 23, 8),
    param_overrides={"P-17": 32.0},      # max switching frequency - more heat
    fix_hint="P-17 (switching frequency) is at its 32 kHz maximum",
    fixed_when=lambda get: (
        (get("P-17") is not None) and float(get("P-17")) <= 8.0
    ),
)

MOTOR_OVERLOAD = Scenario(
    fault_number=4,                      # I_t-trP, motor thermal overload
    label="Motor thermal overload (I2t)",
    dc_bus_v=324,                        # chosen
    heatsink_temp_c=71,                  # chosen
    current_at_trip_a=5.9,               # chosen: sustained, not a spike
    trip_log=(4, 4, 3, 4),
    param_overrides={"P-08": 0.5},       # rated current set far too low
    # KB: the drive trips after delivering >100% of P-08 for a period.
    fix_hint="P-08 (motor rated current) is 0.5 A - far below the nameplate",
    fixed_when=_at_least("P-08", 3.0),
    reset_inhibited=True,                # Section 10.1 p.39 footer
)

INPUT_PHASE_LOSS = Scenario(
    fault_number=14,                     # P-LOSS, input phase loss
    label="Input phase loss",
    dc_bus_v=268,                        # chosen: mean bus sagging
    heatsink_temp_c=46,                  # chosen
    current_at_trip_a=4.2,               # chosen
    trip_log=(14, 14, 13, 7),
    fix_hint="Check all incoming supply phases are present and balanced",
    fixed_when=None,                     # physical
)

MOTOR_THERMISTOR = Scenario(
    fault_number=21,                     # F-Ptc, motor PTC thermistor trip
    label="Motor thermistor over temperature",
    # Deliberately clean drive telemetry: the motor is hot, the drive is not.
    dc_bus_v=326,                        # chosen: nominal
    heatsink_temp_c=41,                  # chosen: nominal
    current_at_trip_a=4.1,               # chosen: nominal
    trip_log=(21, 4, 21, 11),
    fix_hint="The motor's own thermistor is hot - check the motor and its cooling",
    fixed_when=None,                     # physical
)

SCENARIOS = (
    MOTOR_DATA_NOT_SET,
    ACCEL_RAMP_TOO_SHORT,
    SHORT_CIRCUIT,
    REGEN_OVERVOLTAGE,
    SUPPLY_SAG,
    HEATSINK_OVERTEMP,
    MOTOR_OVERLOAD,
    INPUT_PHASE_LOSS,
    MOTOR_THERMISTOR,
)

# The documented demo opener (docs/e2e-checklist.md step 1 and the simulator
# tests both expect a drive sitting tripped on O-I with this trip log).
DEFAULT_SCENARIO = MOTOR_DATA_NOT_SET


class ScenarioBag:
    """Draws scenarios without replacement, never twice in a row.

    A plain random choice would keep repeating the same fault, which is the
    behaviour this replaces: every scenario appears once per cycle before any
    repeats, and a reshuffle can never hand back the scenario just drawn.
    """

    def __init__(self, scenarios=SCENARIOS, seed=None):
        self._pool = list(scenarios)
        self._rng = random.Random(seed)
        self._bag: list = []
        self._last: Optional[Scenario] = None

    def next(self) -> Scenario:
        if not self._bag:
            self._bag = list(self._pool)
            self._rng.shuffle(self._bag)
            if len(self._bag) > 1 and self._bag[0] is self._last:
                self._bag[0], self._bag[-1] = self._bag[-1], self._bag[0]
        scenario = self._bag.pop(0)
        self._last = scenario
        return scenario
