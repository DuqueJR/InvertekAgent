import json

import pytest

from agent.drive import SimulatedDriveClient
from agent.tools.drive_tools import (
    propose_parameter_changes,
    read_drive_status,
    read_parameters,
    read_trip_history,
)


@pytest.fixture
def drive():
    client = SimulatedDriveClient()
    client.connect()
    return client


def test_read_drive_status_without_drive():
    payload = json.loads(read_drive_status(drive=None))
    assert "No drive is connected" in payload["error"]


def test_read_drive_status_reports_seeded_trip(drive):
    payload = json.loads(read_drive_status(drive=drive))
    assert payload["state"] == "Tripped"
    assert "O-I" in payload["active_fault"]["code"]
    # DC bus and temperature reach the agent so it can tell a thermal or
    # voltage fault from a load fault without asking the technician.
    assert payload["dc_bus_voltage_v"] > 0
    assert payload["drive_temperature_c"] > 0


def test_read_trip_history_returns_four(drive):
    payload = json.loads(read_trip_history(drive=drive))
    assert len(payload["trips"]) == 4
    assert payload["trips"][0]["position"] == 0
    assert "O-I" in payload["trips"][0]["code"]


def test_read_parameters_prefers_the_live_drive(drive):
    payload = json.loads(read_parameters(codes=["P-03", "P-08"], drive=drive))
    by_code = {p["code"]: p for p in payload["parameters"]}
    assert by_code["P-03"]["value"] == 5.0  # KB default, seeded
    assert by_code["P-03"]["source"].startswith("drive")
    assert by_code["P-03"]["units"] == "s"
    assert payload["unavailable"] == []


def test_read_parameters_reports_unknown_codes(drive):
    payload = json.loads(read_parameters(codes=["P-99"], drive=drive))
    assert payload["parameters"] == []
    assert "not in the E3 parameter registry" in payload["unavailable"][0]["reason"]


def test_read_parameters_falls_back_to_the_ptb_file(tmp_path):
    import gzip
    import sys

    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    from test_ptb_modifier import build_xml

    ptb = tmp_path / "drive.ptb"
    ptb.write_bytes(gzip.compress(build_xml().encode("utf-8")))

    payload = json.loads(read_parameters(
        codes=["P-03", "P-11"], drive=None, ptb_path=str(ptb),
    ))
    by_code = {p["code"]: p for p in payload["parameters"]}
    assert by_code["P-03"]["value"] == 5.0  # 500 raw / scale 100
    assert by_code["P-03"]["source"] == "uploaded .ptb file"
    # P-11 is absent from this file: reported, never guessed.
    assert payload["unavailable"][0]["code"] == "P-11"
    assert "keypad" in payload["unavailable"][0]["reason"]


def test_read_parameters_without_drive_or_file():
    payload = json.loads(read_parameters(codes=["P-03"], drive=None))
    assert payload["parameters"] == []
    assert payload["unavailable"][0]["code"] == "P-03"


def test_read_parameters_requires_codes(drive):
    payload = json.loads(read_parameters(codes=[], drive=drive))
    assert "error" in payload


def test_propose_validates_and_reads_current_value(drive):
    payload = json.loads(propose_parameter_changes(
        changes=[{"code": "P-03", "new_value": 8.0, "reason": "slower ramp"}],
        rationale="Reduce acceleration current.",
        drive=drive,
    ))
    assert payload["proposal_ok"]
    change = payload["proposal"]["changes"][0]
    assert change["code"] == "P-03"
    assert change["new_display"] == 8.0
    assert change["current_display"] == 5.0  # KB default seeded in simulator
    assert "never claim" in payload["message"]


def test_propose_works_without_drive():
    payload = json.loads(propose_parameter_changes(
        changes=[{"code": "P-04", "new_value": 10.0, "reason": "test"}],
        rationale="test",
        drive=None,
    ))
    assert payload["proposal_ok"]
    assert payload["proposal"]["changes"][0]["current_display"] is None


def test_propose_rejects_invalid_items(drive):
    payload = json.loads(propose_parameter_changes(
        changes=[
            {"code": "P00-08", "new_value": 400, "reason": "read-only"},
            {"code": "P-99", "new_value": 1, "reason": "unknown"},
            {"code": "P-30", "new_value": 1, "reason": "indexed"},
            {"code": "P-03", "new_value": 9999.0, "reason": "over max"},
            {"code": "P-03", "new_value": "fast", "reason": "not numeric"},
        ],
        rationale="all invalid",
        drive=drive,
    ))
    assert not payload["proposal_ok"]
    messages = " ".join(r["message"] for r in payload["rejected"])
    assert "read-only" in messages
    assert "not in the E3 parameter registry" in messages
    assert "indexed" in messages
    assert "above the documented maximum" in messages
    assert "not a numeric value" in messages


def test_propose_partial_validation_keeps_valid_changes(drive):
    payload = json.loads(propose_parameter_changes(
        changes=[
            {"code": "P-03", "new_value": 8.0, "reason": "ok"},
            {"code": "P-99", "new_value": 1, "reason": "unknown"},
        ],
        rationale="mixed",
        drive=drive,
    ))
    assert payload["proposal_ok"]
    assert len(payload["proposal"]["changes"]) == 1
    assert len(payload["proposal"]["rejected"]) == 1


def test_propose_requires_changes():
    payload = json.loads(propose_parameter_changes(
        changes=[], rationale="empty", drive=None,
    ))
    assert not payload["proposal_ok"]
