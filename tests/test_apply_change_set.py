"""The approved-write path: safety, verification and report shape.

client.py renders the drive report and the .ptb report with the same code,
so the two must agree on structure. It also decides the proposal's outcome
from the drive report alone, which is why `success` has to mean "every
approved change is on the drive and was read back".
"""

import gzip
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from agent.drive import SimulatedDriveClient, apply_change_set
from agent.tools.ptb import modify_ptb_configuration, read_ptb_parameters
from test_ptb_modifier import build_xml

REPORT_KEYS = {
    "success", "total_changes_requested", "applied_count", "rejected_count",
    "applied", "rejected", "warnings",
}
REJECTION_KEYS = {"code", "requested_value", "error_type", "message"}


@pytest.fixture
def drive():
    client = SimulatedDriveClient()
    client.connect()
    return client


@pytest.fixture
def ptb(tmp_path):
    path = tmp_path / "drive.ptb"
    path.write_bytes(gzip.compress(build_xml().encode("utf-8")))
    return path


def change(code, value, reason="test"):
    return {"code": code, "new_value": value, "reason": reason}


# --- report shape parity ----------------------------------------------------

def test_drive_and_ptb_reports_share_a_shape(drive, ptb, tmp_path):
    drive_report = apply_change_set(drive, [change("P-03", 8.0)])
    ptb_report = json.loads(modify_ptb_configuration(
        str(ptb), [change("P-03", 8.0)], str(tmp_path / "out.ptb"),
    ))
    assert REPORT_KEYS <= set(drive_report)
    assert REPORT_KEYS <= set(ptb_report)
    for report in (drive_report, ptb_report):
        for item in report["applied"]:
            assert {"code", "name", "old_display", "new_display",
                    "units", "reason"} <= set(item)


def test_rejections_share_a_shape(drive, ptb, tmp_path):
    bad = [change("P-99", 1)]
    drive_report = apply_change_set(drive, bad)
    ptb_report = json.loads(modify_ptb_configuration(
        str(ptb), bad, str(tmp_path / "out.ptb"),
    ))
    assert REJECTION_KEYS <= set(drive_report["rejected"][0])
    assert REJECTION_KEYS <= set(ptb_report["rejected"][0])


def test_counts_agree_with_the_lists(drive):
    report = apply_change_set(drive, [
        change("P-03", 8.0), change("P-99", 1),
    ])
    assert report["applied_count"] == len(report["applied"])
    assert report["rejected_count"] == len(report["rejected"])
    assert report["total_changes_requested"] == 2


# --- success means verified on the drive ------------------------------------

def test_success_requires_every_change_to_land(drive):
    mixed = apply_change_set(drive, [change("P-03", 8.0), change("P-99", 1)])
    assert mixed["applied"], "the valid change should still be written"
    assert not mixed["success"], "a rejected change must not report success"

    clean = apply_change_set(drive, [change("P-04", 9.0)])
    assert clean["success"]
    assert all(item["verified"] for item in clean["applied"])


def test_applied_values_are_actually_on_the_drive(drive):
    apply_change_set(drive, [change("P-03", 8.0), change("P-04", 12.5)])
    # Ramp times are stored x100, per the registry's documented scaling.
    assert drive.read_parameter("P-03") == 800
    assert drive.read_parameter("P-04") == 1250


def test_verify_failure_is_reported_not_swallowed(drive):
    before = drive.read_parameter("P-03")
    drive.fail_next_write = True
    report = apply_change_set(drive, [change("P-03", 8.0)])
    assert not report["success"]
    assert report["rejected"][0]["error_type"] == "verify_failed"
    assert drive.read_parameter("P-03") == before


# --- the .ptb reader --------------------------------------------------------

def test_read_ptb_parameters_applies_registry_scaling(ptb):
    values = read_ptb_parameters(str(ptb), ["P-03", "P-08", "P-54"])
    assert values["P-03"] == 5.0     # 500 raw, scale 100
    assert values["P-08"] == 7.0     # 70 raw, scale 10
    assert values["P-54"] == 150.0   # 1500 raw, scale 10


def test_read_ptb_parameters_omits_what_the_file_lacks(ptb):
    values = read_ptb_parameters(str(ptb), ["P-03", "P-11"])
    assert "P-03" in values
    assert "P-11" not in values, "absent parameters must not be invented"


def test_read_ptb_parameters_reads_the_whole_file_by_default(ptb):
    values = read_ptb_parameters(str(ptb))
    assert {"P-01", "P-02", "P-03", "P-04", "P-08", "P-54"} <= set(values)


def test_ptb_copy_survives_a_parameter_the_file_lacks(ptb, tmp_path):
    """Non-strict is what lets an approved change set still produce a file.

    A proposal may name a parameter this particular .ptb does not carry;
    the drive write is unaffected, so the copy must still be written with
    the changes that do apply, and the shortfall reported.
    """
    out = tmp_path / "out.ptb"
    report = json.loads(modify_ptb_configuration(
        str(ptb),
        [change("P-08", 4.8), change("P-11", 0.0)],
        str(out),
        strict=False,
    ))
    assert report["success"]
    assert [item["code"] for item in report["applied"]] == ["P-08"]
    assert report["rejected"][0]["code"] == "P-11"
    assert read_ptb_parameters(str(out), ["P-08"])["P-08"] == 4.8
