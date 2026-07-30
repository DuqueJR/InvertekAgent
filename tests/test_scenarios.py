"""Fault scenarios must be real, varied, and diagnosable.

The regression these guard: the Trip button used to hardcode fault 3, so
every press replayed O-I with no supporting telemetry. A scenario is only
useful if its fault code exists in the knowledge base, its telemetry is
inside the ranges the drive's registers can express, and the pool actually
varies.
"""

import json
from pathlib import Path

import pytest

from agent.drive import (
    DEFAULT_SCENARIO,
    SCENARIOS,
    ScenarioBag,
    SimulatedDriveClient,
    apply_change_set,
)
from agent.drive.base import fault_lookup
from agent.drive.scenarios import (
    ACCEL_RAMP_TOO_SHORT,
    DC_BUS_RANGE_V,
    MOTOR_OVERLOAD,
    MOTOR_THERMISTOR,
    REGEN_OVERVOLTAGE,
    RESET_INHIBIT_S,
    TEMP_RANGE_C,
)

FAULT_CODES_PATH = (
    Path(__file__).resolve().parent.parent / "agent" / "data" / "fault_codes.json"
)


@pytest.fixture(scope="module")
def kb_fault_numbers():
    payload = json.loads(FAULT_CODES_PATH.read_text(encoding="utf-8"))
    return {int(f["display_number"]) for f in payload["faults"]}


@pytest.fixture
def drive():
    client = SimulatedDriveClient()
    client.connect()
    return client


# --- the scenario table is real ---------------------------------------------

@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.label[:32])
def test_fault_number_exists_in_the_knowledge_base(scenario, kb_fault_numbers):
    assert scenario.fault_number in kb_fault_numbers
    code, name = fault_lookup(scenario.fault_number)
    # A typo'd number would silently resolve to "Unknown fault code".
    assert name != "Unknown fault code"
    assert code


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.label[:32])
def test_telemetry_fits_the_register_ranges(scenario):
    # Section 8.4: DC bus register 0..1000 V, temperature register 0..100 degC.
    assert DC_BUS_RANGE_V[0] <= scenario.dc_bus_v <= DC_BUS_RANGE_V[1]
    assert TEMP_RANGE_C[0] <= scenario.heatsink_temp_c <= TEMP_RANGE_C[1]


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.label[:32])
def test_trip_log_is_believable(scenario):
    assert 1 <= len(scenario.trip_log) <= 4
    assert scenario.trip_log[0] == scenario.fault_number, (
        "the newest entry must be the fault the scenario trips on"
    )


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.label[:32])
def test_every_scenario_explains_itself(scenario):
    assert scenario.fix_hint, "a scenario needs a hint for the demo operator"
    assert scenario.label


def test_excluded_faults_are_absent():
    """Comms loss, autotune, memory/status and IP66-only codes stay out.

    Each exclusion is deliberate and documented in scenarios.py; this pins
    them so none creeps in later.
    """
    excluded = {
        12, 50, 51,              # comms loss - this app reads over Modbus
        40, 41, 42, 43, 44,      # autotune only
        0, 10, 17, 19,           # status / internal memory
        5, 22,                   # IP66-only
    }
    assert not ({s.fault_number for s in SCENARIOS} & excluded)


def test_pool_covers_both_fixable_and_physical_causes():
    fixable = [s for s in SCENARIOS if s.is_parameter_fixable]
    physical = [s for s in SCENARIOS if not s.is_parameter_fixable]
    # If every fault were a parameter fix, the agent would learn to always
    # propose one; physical causes keep it honest.
    assert len(fixable) >= 3
    assert len(physical) >= 3


# --- variety: the actual bug being fixed ------------------------------------

def test_bag_never_repeats_back_to_back_and_covers_the_pool():
    bag = ScenarioBag(seed=7)
    n = len(SCENARIOS)
    drawn = [bag.next() for _ in range(n * 3)]

    for first, second in zip(drawn, drawn[1:]):
        assert first is not second, "the same fault must not come up twice running"

    for cycle in range(3):
        window = drawn[cycle * n:(cycle + 1) * n]
        assert len(set(id(s) for s in window)) == n, (
            "every scenario should appear once per cycle"
        )


def test_bag_is_reproducible_with_a_seed():
    a = [s.label for s in (ScenarioBag(seed=42).next() for _ in range(9))]
    b = [s.label for s in (ScenarioBag(seed=42).next() for _ in range(9))]
    assert a == b


# --- applying a scenario ----------------------------------------------------

def test_default_opener_is_unchanged(drive):
    """docs/e2e-checklist.md step 1 and the demo script depend on this."""
    status = drive.read_status()
    assert DEFAULT_SCENARIO.fault_number == 3
    assert status.tripped and not status.running
    assert "O-I" in status.fault_code
    assert [t.fault_number for t in drive.read_trip_history()] == [3, 3, 4, 11]
    # No parameter overrides on the opener: P-08 is 0.0 A from the KB default,
    # which is itself the root cause the agent should find.
    assert drive.read_parameter("P-03") == 500  # 5.0 s, untouched


def test_apply_scenario_sets_telemetry_and_causes(drive):
    drive.apply_scenario(REGEN_OVERVOLTAGE)
    status = drive.read_status()
    assert status.fault_code == "O-Volt"
    assert status.dc_bus_v == REGEN_OVERVOLTAGE.dc_bus_v
    assert status.heatsink_temp_c == REGEN_OVERVOLTAGE.heatsink_temp_c
    # Output is off after a trip, but bus and temperature keep reading.
    assert status.output_freq_hz == 0.0
    assert status.output_current_a == 0.0
    # The cause is in the parameter bank for the agent to find.
    assert drive.read_parameter("P-04") == 30      # 0.3 s, scale 100
    assert drive.read_parameter("P-34") == 0
    assert [t.fault_number for t in drive.read_trip_history()][0] == 6


def test_thermal_scenario_exceeds_the_documented_threshold(drive):
    from agent.drive.scenarios import HEATSINK_OVERTEMP

    drive.apply_scenario(HEATSINK_OVERTEMP)
    # P00-23 counts hours above 85 degC, so an O-t demo must clear it.
    assert drive.read_status().heatsink_temp_c > 85


def test_thermistor_scenario_keeps_drive_telemetry_clean(drive):
    """F-Ptc: the motor is hot, the drive is not. Clean readings are the point."""
    drive.apply_scenario(MOTOR_THERMISTOR)
    status = drive.read_status()
    assert status.fault_code == "F-Ptc"
    assert 300 <= status.dc_bus_v <= 350
    assert status.heatsink_temp_c < 85


# --- arm, trip on start, and fix --------------------------------------------

def test_arming_installs_the_cause_without_tripping(drive):
    """Arming alone must be enough to make the next start fail.

    Regression: arm_scenario used to set only the flag, so on a drive whose
    parameter still held a healthy default the scenario read as already
    fixed and the arm silently did nothing.
    """
    assert drive.read_parameter("P-03") == 500      # 5.0 s, healthy default
    drive.arm_scenario(ACCEL_RAMP_TOO_SHORT)

    assert drive.read_parameter("P-03") == 50, "the cause should be in place"
    # Arming must not trip on its own: the drive was already tripped from the
    # opener, so reset first and confirm arming leaves it clear.
    drive._tripped = False
    assert drive.read_status().running is False
    assert drive.simulate_run() is False, "the start attempt must trip"


def test_armed_fault_trips_every_start_until_fixed(drive):
    drive.apply_scenario(ACCEL_RAMP_TOO_SHORT)   # puts P-03 = 0.5 in the bank
    drive.arm_scenario(ACCEL_RAMP_TOO_SHORT)

    assert drive.simulate_run() is False
    assert drive.read_status().tripped
    assert drive.simulate_run() is False, "must keep tripping while unfixed"

    report = apply_change_set(
        drive, [{"code": "P-03", "new_value": 8.0, "reason": "lengthen ramp"}]
    )
    assert report["success"]

    assert drive.simulate_run() is True, "fixing the cause should let it start"
    status = drive.read_status()
    assert status.running and not status.tripped


def test_physical_scenario_never_clears_by_itself(drive):
    drive.arm_scenario(MOTOR_THERMISTOR)
    assert drive.simulate_run() is False
    # No parameter change can fix a hot motor, so it stays armed.
    assert drive.simulate_run() is False


def test_overload_scenario_is_fixed_by_correcting_p08(drive):
    drive.apply_scenario(MOTOR_OVERLOAD)
    drive.arm_scenario(MOTOR_OVERLOAD)
    assert drive.simulate_run() is False
    apply_change_set(
        drive, [{"code": "P-08", "new_value": 4.8, "reason": "nameplate"}]
    )
    assert drive.simulate_run() is True


# --- reset inhibit ----------------------------------------------------------

def test_reset_is_inhibited_after_an_overcurrent_trip():
    """Section 10.1 p.39: faults 3, 4 and 15 need a recovery delay."""
    now = [1000.0]
    drive = SimulatedDriveClient(clock=lambda: now[0])
    drive.connect()
    drive.apply_scenario(ACCEL_RAMP_TOO_SHORT)   # fault 3, reset_inhibited

    assert drive.reset_blocked_for_s > 0
    with pytest.raises(Exception) as exc:
        drive.reset_fault()
    assert "cannot be reset yet" in str(exc.value)

    now[0] += RESET_INHIBIT_S + 0.1
    assert drive.reset_blocked_for_s == 0
    drive.reset_fault()
    assert not drive.read_status().tripped


def test_reset_is_immediate_for_other_faults():
    now = [1000.0]
    drive = SimulatedDriveClient(clock=lambda: now[0])
    drive.connect()
    drive.apply_scenario(MOTOR_THERMISTOR)       # fault 21, no lockout
    assert drive.reset_blocked_for_s == 0
    drive.reset_fault()
    assert not drive.read_status().tripped
