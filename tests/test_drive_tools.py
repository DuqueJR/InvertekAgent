import json

import pytest

from agent.drive import SimulatedDriveClient
from agent.tools.drive_tools import (
    propose_parameter_changes,
    read_drive_status,
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


def test_read_trip_history_returns_four(drive):
    payload = json.loads(read_trip_history(drive=drive))
    assert len(payload["trips"]) == 4
    assert payload["trips"][0]["position"] == 0
    assert "O-I" in payload["trips"][0]["code"]


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
