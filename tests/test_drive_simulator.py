import pytest

from agent.drive import (
    DriveNotConnected,
    SimulatedDriveClient,
    apply_change_set,
)
from agent.drive.registers import param_register
from agent.drive.base import fault_lookup


@pytest.fixture
def drive():
    client = SimulatedDriveClient()
    client.connect()
    return client


# --- register map -----------------------------------------------------------

def test_param_register_matches_guide_worked_example():
    # Section 8.4, p.33: "for parameter P-15, the register number is
    # 128 + 15 = 143".
    assert param_register("P-15") == 143


def test_param_register_rejects_undocumented_codes():
    with pytest.raises(ValueError):
        param_register("P-01")  # below the documented P-04..P-60 range
    with pytest.raises(ValueError):
        param_register("P00-13")  # read-only group has no register formula


def test_fault_lookup_resolves_kb_entries():
    code, name = fault_lookup(3)
    assert "O-I" in code
    assert name  # non-empty, from the KB
    code, name = fault_lookup(255)
    assert name == "Unknown fault code"


# --- simulator behaviour ----------------------------------------------------

def test_requires_connection():
    client = SimulatedDriveClient()
    with pytest.raises(DriveNotConnected):
        client.read_status()


def test_seeded_scenario_is_stopped_and_tripped(drive):
    status = drive.read_status()
    assert status.connected
    assert status.tripped and not status.running
    assert status.state_label == "Tripped"
    assert status.fault_number == 3
    assert "O-I" in status.fault_code
    assert status.output_freq_hz == 0.0


def test_trip_history_returns_four_newest_first(drive):
    trips = drive.read_trip_history()
    assert len(trips) == 4
    assert [t.position for t in trips] == [0, 1, 2, 3]
    assert trips[0].fault_number == 3
    assert "O-I" in trips[0].fault_code


def test_simulate_trip_pushes_the_log(drive):
    drive.simulate_trip(6)  # O-Volt
    trips = drive.read_trip_history()
    assert trips[0].fault_number == 6
    assert len(trips) == 4  # oldest entry fell off


def test_run_stop_flips_state(drive):
    drive.simulate_run()
    status = drive.read_status()
    assert status.running and not status.tripped
    assert status.output_freq_hz > 0
    drive.simulate_stop()
    assert drive.read_status().state_label == "Stopped"


def test_running_telemetry_is_plausible(drive):
    drive.simulate_run()
    status = drive.read_status()
    # A healthy 230 V-class drive: bus near 325 V, heatsink well under the
    # 85 degC threshold that P00-23 counts hours above.
    assert 300 <= status.dc_bus_v <= 350
    assert 30 <= status.heatsink_temp_c <= 85


def test_status_dict_exposes_the_new_telemetry(drive):
    payload = drive.read_status().to_dict()
    assert "dc_bus_voltage_v" in payload
    assert "drive_temperature_c" in payload


def test_parameter_write_read_back_round_trip(drive):
    raw = drive.read_parameter("P-03")
    drive.write_parameter("P-03", raw + 100)
    assert drive.read_parameter("P-03") == raw + 100


# --- apply_change_set -------------------------------------------------------

def change(code, value, reason="test"):
    return {"code": code, "new_value": value, "reason": reason}


def test_apply_writes_and_verifies(drive):
    report = apply_change_set(drive, [change("P-03", 8.0)])
    assert report["success"]
    item = report["applied"][0]
    assert item["verified"]
    assert item["new_display"] == 8.0
    assert drive.read_parameter("P-03") == 800  # ramp seconds are x100


def test_apply_refuses_while_running(drive):
    drive.simulate_run()
    report = apply_change_set(drive, [change("P-03", 8.0)])
    assert not report["success"]
    assert report["rejected"][0]["error_type"] == "safety_gate"
    assert "stopped" in report["rejected"][0]["message"]


def test_apply_refuses_without_connection():
    client = SimulatedDriveClient()  # never connected
    report = apply_change_set(client, [change("P-03", 8.0)])
    assert not report["success"]
    assert report["rejected"][0]["error_type"] == "not_connected"


def test_apply_rejects_invalid_items_individually(drive):
    report = apply_change_set(drive, [
        change("P00-08", 400),      # read-only
        change("P-99", 1),          # unknown
        change("P-03", 9999.0),     # above documented max 600.0
        change("P-04", 8.0),        # valid
    ])
    assert not report["success"]  # batch had rejections
    types = {r["code"]: r["error_type"] for r in report["rejected"]}
    assert types["P00-08"] == "read_only"
    assert types["P-99"] == "unknown_parameter"
    assert types["P-03"] == "out_of_range"
    assert report["applied"][0]["code"] == "P-04"
    assert report["applied"][0]["verified"]


def test_apply_aborts_batch_on_verify_failure(drive):
    drive.fail_next_write = True
    report = apply_change_set(drive, [
        change("P-03", 8.0),
        change("P-04", 8.0),
    ])
    assert not report["success"]
    assert report["rejected"][0]["error_type"] == "verify_failed"
    assert report["rejected"][1]["error_type"] == "not_attempted"
    assert report["applied"] == []
