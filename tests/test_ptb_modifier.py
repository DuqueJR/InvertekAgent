"""Tests for modify_ptb_configuration.

TODO: replace the synthetic fixture below with a real Optidrive E3 .ptb in
tests/fixtures/ as soon as one is available. The synthetic file follows the
documented ParamProgram structure, but only a real file can confirm the
code -> (groupNum, paramNum) convention and the per-parameter scale factors
(see agent/tools/ptb/data/e3_registry.json).
"""

import gzip
import json

import pytest

from agent.tools.ptb.modifier import modify_ptb_configuration

FIXTURES = __file__.rsplit("test_ptb_modifier.py", 1)[0] + "fixtures"

XML_HEADER = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<ParamProgram xmlns="http://www.invertek.co.uk/ParamProgram.xsd">\n'
    "  <driveParameterSet>\n"
    "    <DriveType>E3</DriveType>\n"
    "    <DriveVersion>3.11</DriveVersion>\n"
    "    <DriveFileVersion>2</DriveFileVersion>\n"
    "    <DriveCode>1234</DriveCode>\n"
    "    <DriveSubCode>0</DriveSubCode>\n"
    "    <DriveName>TEST-E3</DriveName>\n"
    "    <DriveCompanyName>IDL</DriveCompanyName>\n"
)

XML_FOOTER = "  </driveParameterSet>\n</ParamProgram>\n"


def _rparam(group, num, value, units, minimum, maximum, user=0):
    return (
        "    <RParam>\n"
        f"      <groupNum>{group}</groupNum>\n"
        f"      <paramNum>{num}</paramNum>\n"
        f"      <currentValue>{value}</currentValue>\n"
        f"      <units>{units}</units>\n"
        f"      <max>{maximum}</max>\n"
        f"      <min>{minimum}</min>\n"
        "      <boundary>AA==</boundary>\n"
        "      <symbol>AA==</symbol>\n"
        "      <visible>true</visible>\n"
        "      <signFlag>false</signFlag>\n"
        "      <showPlcParam>false</showPlcParam>\n"
        "      <decimal>0</decimal>\n"
        f"      <userValue>{user}</userValue>\n"
        "    </RParam>\n"
    )


def _lparam(group, num, value, user=0):
    return (
        "    <LParam>\n"
        f"      <groupNum>{group}</groupNum>\n"
        f"      <paramNum>{num}</paramNum>\n"
        f"      <currentValue>{value}</currentValue>\n"
        "      <visible>true</visible>\n"
        f"      <userValue>{user}</userValue>\n"
        "    </LParam>\n"
    )


def _multi_rparam(group, num, values):
    """An indexed parameter: several <currentValue> elements in one element."""
    body = (
        "    <RParam>\n"
        f"      <groupNum>{group}</groupNum>\n"
        f"      <paramNum>{num}</paramNum>\n"
    )
    for value in values:
        body += f"      <currentValue>{value}</currentValue>\n"
    body += (
        "      <units></units>\n"
        "      <max>5</max>\n"
        "      <min>0</min>\n"
        "      <visible>true</visible>\n"
        "      <userValue>0</userValue>\n"
        "    </RParam>\n"
    )
    return body


def build_xml(swap_p04_to_lparam=False):
    """A minimal but structurally faithful E3 parameter program."""
    params = [
        _rparam(1, 1, 500, "Hz", 0, 5000),          # P-01 max freq  50.0 Hz
        _rparam(1, 2, 0, "Hz", 0, 5000),            # P-02 min freq   0.0 Hz
        _rparam(1, 3, 500, "s", 0, 60000),          # P-03 accel      5.00 s
        _lparam(1, 4, 500) if swap_p04_to_lparam    # P-04 decel (wrong kind)
        else _rparam(1, 4, 500, "s", 0, 60000),     # P-04 decel      5.00 s
        _rparam(1, 8, 70, "A", 0, 480),             # P-08 motor I    7.0 A
        _lparam(1, 12, 0),                          # P-12 command source
        _lparam(1, 15, 0),                          # P-15 macro
        _multi_rparam(1, 30, [0, 0, 0]),            # P-30 indexed
        _rparam(1, 54, 1500, "%", 0, 1500),         # P-54 current limit 150.0%
    ]
    return XML_HEADER + "".join(params) + XML_FOOTER


@pytest.fixture
def ptb_file(tmp_path):
    """Writes the synthetic .ptb (gzipped, as real files are) and returns it."""
    path = tmp_path / "original.ptb"
    path.write_bytes(gzip.compress(build_xml().encode("utf-8")))
    return path


@pytest.fixture
def out_path(tmp_path):
    return tmp_path / "modified.ptb"


def run(ptb_file, changes, out_path, strict=True):
    return json.loads(modify_ptb_configuration(
        str(ptb_file), changes, str(out_path), strict=strict
    ))


def read_xml(path):
    return gzip.decompress(path.read_bytes()).decode("utf-8")


def find_param(xml, tag, group, num):
    """Return the raw text block of one parameter element."""
    needle = f"<groupNum>{group}</groupNum>\n      <paramNum>{num}</paramNum>"
    idx = xml.find(needle)
    assert idx != -1, f"{tag} ({group}, {num}) not found in output"
    start = xml.rfind(f"<{tag}>", 0, idx)
    end = xml.find(f"</{tag}>", idx)
    return xml[start:end]


# ---------------------------------------------------------------------------
# 1. Round trip with no changes
# ---------------------------------------------------------------------------

def test_roundtrip_without_changes_preserves_file(ptb_file, out_path):
    report = run(ptb_file, [], out_path)

    assert report["success"] is True
    assert report["applied_count"] == 0
    assert report["rejected"] == []
    assert report["drive_type"] == "E3"
    assert report["drive_version"] == "3.11"
    assert report["drive_code"] == "1234"
    assert out_path.exists()
    # Byte-for-byte identical XML payload, including the declaration.
    assert read_xml(out_path) == build_xml()


# ---------------------------------------------------------------------------
# 2. A valid RParam change
# ---------------------------------------------------------------------------

def test_valid_rparam_change_updates_current_and_user_value(ptb_file, out_path):
    report = run(ptb_file, [
        {"code": "P-03", "new_value": 6.0, "reason": "Reduce acceleration current"},
    ], out_path)

    assert report["success"] is True
    assert report["applied_count"] == 1
    assert report["rejected_count"] == 0

    applied = report["applied"][0]
    assert applied["code"] == "P-03"
    assert applied["name"] == "Acceleration Ramp Time"
    assert applied["old_raw"] == 500
    assert applied["new_raw"] == 600          # 6.0 s * scale 100
    assert applied["old_display"] == 5.0
    assert applied["new_display"] == 6.0
    assert applied["units"] == "s"
    assert applied["reason"] == "Reduce acceleration current"

    xml = read_xml(out_path)
    p03 = find_param(xml, "RParam", 1, 3)
    assert "<currentValue>600</currentValue>" in p03
    assert "<userValue>600</userValue>" in p03   # both fields, defensive rule

    # Everything else is untouched: the output differs from the input only in
    # the two fields of P-03.
    original = build_xml()
    assert xml.replace(
        "<currentValue>600</currentValue>", "<currentValue>500</currentValue>", 1
    ).replace("<userValue>600</userValue>", "<userValue>0</userValue>", 1) == original


def test_lparam_change_uses_registry_bounds(ptb_file, out_path):
    """LParam has no <min>/<max> in the file, so the registry supplies them."""
    report = run(ptb_file, [{"code": "P-12", "new_value": 3}], out_path)

    assert report["success"] is True
    applied = report["applied"][0]
    assert applied["new_raw"] == 3
    assert applied["range_check"] == "registry"
    assert "<currentValue>3</currentValue>" in find_param(
        read_xml(out_path), "LParam", 1, 12)


# ---------------------------------------------------------------------------
# 3. Unknown parameter code
# ---------------------------------------------------------------------------

def test_unknown_parameter_is_rejected(ptb_file, out_path):
    report = run(ptb_file, [{"code": "P-99", "new_value": 10.0}], out_path)

    assert report["success"] is False
    assert report["output_path"] is None
    assert not out_path.exists()

    rejection = report["rejected"][0]
    assert rejection["code"] == "P-99"
    assert rejection["error_type"] == "unknown_parameter"
    assert rejection["requested_value"] == 10.0
    assert "not defined" in rejection["message"]


def test_invalid_code_format_is_rejected(ptb_file, out_path):
    report = run(ptb_file, [{"code": "PP3", "new_value": 1.0}], out_path)

    assert report["rejected"][0]["error_type"] == "invalid_code_format"
    assert not out_path.exists()


# ---------------------------------------------------------------------------
# 4. Out of range
# ---------------------------------------------------------------------------

def test_out_of_range_is_rejected_against_file_bounds(ptb_file, out_path):
    # P-01 max is 5000 raw = 500.0 Hz; 600 Hz scales to 6000.
    report = run(ptb_file, [{"code": "P-01", "new_value": 600.0}], out_path)

    rejection = report["rejected"][0]
    assert rejection["error_type"] == "out_of_range"
    assert "6000" in rejection["message"]      # the computed raw value
    assert "5000" in rejection["message"]      # the file's own maximum
    assert not out_path.exists()


def test_below_minimum_is_rejected(ptb_file, out_path):
    report = run(ptb_file, [{"code": "P-08", "new_value": -1.0}], out_path)

    assert report["rejected"][0]["error_type"] == "out_of_range"


# ---------------------------------------------------------------------------
# 5. Read-only group P00
# ---------------------------------------------------------------------------

def test_readonly_group_is_rejected(ptb_file, out_path):
    report = run(ptb_file, [{"code": "P00-08", "new_value": 400}], out_path)

    rejection = report["rejected"][0]
    assert rejection["error_type"] == "readonly_group"
    assert "read-only" in rejection["message"]
    assert not out_path.exists()


# ---------------------------------------------------------------------------
# 6. Multi-value (indexed) parameter
# ---------------------------------------------------------------------------

def test_multi_value_parameter_is_rejected(ptb_file, out_path):
    report = run(ptb_file, [{"code": "P-30", "new_value": 1}], out_path)

    rejection = report["rejected"][0]
    assert rejection["error_type"] == "multi_value_forbidden"
    assert not out_path.exists()


def test_type_mismatch_between_registry_and_file(tmp_path, out_path):
    """Registry says P-04 is an RParam; this file stores it as an LParam."""
    ptb = tmp_path / "swapped.ptb"
    ptb.write_bytes(gzip.compress(
        build_xml(swap_p04_to_lparam=True).encode("utf-8")))

    report = run(ptb, [{"code": "P-04", "new_value": 6.0}], out_path)

    rejection = report["rejected"][0]
    assert rejection["error_type"] == "type_mismatch"
    assert "LParam" in rejection["message"]


def test_parameter_absent_from_file_is_rejected(ptb_file, out_path):
    # P-63 is in the registry but not in this synthetic file.
    report = run(ptb_file, [{"code": "P-63", "new_value": 1}], out_path)

    assert report["rejected"][0]["error_type"] == "parameter_not_in_file"


# ---------------------------------------------------------------------------
# 7. strict=True aborts the whole batch
# ---------------------------------------------------------------------------

def test_strict_mode_aborts_entire_batch(ptb_file, out_path):
    report = run(ptb_file, [
        {"code": "P-03", "new_value": 6.0, "reason": "good change"},
        {"code": "P-99", "new_value": 10.0, "reason": "bad change"},
    ], out_path, strict=True)

    assert report["success"] is False
    assert report["output_path"] is None
    assert report["applied"] == []
    assert report["applied_count"] == 0
    assert not out_path.exists()

    # Both changes are reported as rejected; the valid one carries no
    # error_type because it did not fail validation, only the batch did.
    assert report["rejected_count"] == 2
    by_code = {r["code"]: r for r in report["rejected"]}
    assert by_code["P-99"]["error_type"] == "unknown_parameter"
    assert by_code["P-03"]["error_type"] is None
    assert "strict mode" in by_code["P-03"]["message"]


# ---------------------------------------------------------------------------
# 8. strict=False applies what it can
# ---------------------------------------------------------------------------

def test_non_strict_mode_applies_valid_changes(ptb_file, out_path):
    report = run(ptb_file, [
        {"code": "P-03", "new_value": 6.0, "reason": "good change"},
        {"code": "P-99", "new_value": 10.0, "reason": "bad change"},
    ], out_path, strict=False)

    assert report["success"] is True
    assert report["output_path"] == str(out_path)
    assert report["applied_count"] == 1
    assert report["rejected_count"] == 1
    assert report["applied"][0]["code"] == "P-03"
    assert report["rejected"][0]["code"] == "P-99"
    assert report["rejected"][0]["error_type"] == "unknown_parameter"

    xml = read_xml(out_path)
    p03 = find_param(xml, "RParam", 1, 3)
    assert "<currentValue>600</currentValue>" in p03
    assert "<userValue>600</userValue>" in p03


def test_non_strict_mode_writes_nothing_when_all_changes_fail(ptb_file, out_path):
    report = run(ptb_file, [
        {"code": "P-99", "new_value": 1.0},
        {"code": "P00-08", "new_value": 400},
    ], out_path, strict=False)

    assert report["success"] is False
    assert report["output_path"] is None
    assert report["rejected_count"] == 2
    assert not out_path.exists()


# ---------------------------------------------------------------------------
# I/O failures
# ---------------------------------------------------------------------------

def test_missing_input_file_reports_io_error(tmp_path, out_path):
    report = run(tmp_path / "does-not-exist.ptb",
                 [{"code": "P-03", "new_value": 6.0}], out_path)

    assert report["success"] is False
    rejection = report["rejected"][0]
    assert rejection["error_type"] == "io_error"
    assert "not found" in rejection["message"]


def test_corrupt_gzip_reports_io_error(tmp_path, out_path):
    ptb = tmp_path / "corrupt.ptb"
    ptb.write_bytes(b"\x1f\x8b" + b"garbage")

    report = run(ptb, [{"code": "P-03", "new_value": 6.0}], out_path)

    assert report["rejected"][0]["error_type"] == "io_error"


def test_plain_xml_input_is_written_back_as_plain_xml(tmp_path, out_path):
    """Some .ptb files may not be gzipped; the envelope is preserved."""
    ptb = tmp_path / "plain.ptb"
    ptb.write_bytes(build_xml().encode("utf-8"))

    report = run(ptb, [{"code": "P-03", "new_value": 6.0}], out_path)

    assert report["success"] is True
    assert out_path.read_bytes()[:2] != gzip.compress(b"x")[:2]
    assert "<currentValue>600</currentValue>" in out_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Serialisation fidelity for .NET XmlSerializer output styles
# ---------------------------------------------------------------------------

def test_bom_and_spaced_empty_tags_are_preserved(tmp_path, out_path):
    """.NET writes a UTF-8 BOM and empty elements as <units />."""
    xml = build_xml().replace("<units></units>", "<units />")
    original = b"\xef\xbb\xbf" + xml.encode("utf-8")
    ptb = tmp_path / "dotnet-style.ptb"
    ptb.write_bytes(gzip.compress(original))

    report = run(ptb, [{"code": "P-03", "new_value": 6.0}], out_path)
    assert report["success"] is True

    written = gzip.decompress(out_path.read_bytes())
    assert written.startswith(b"\xef\xbb\xbf")
    assert b"<units />" in written
    assert b"<units/>" not in written
    # Only P-03's two fields differ from the input.
    assert written.replace(
        b"<currentValue>600</currentValue>", b"<currentValue>500</currentValue>", 1
    ).replace(b"<userValue>600</userValue>", b"<userValue>0</userValue>", 1) == original


def test_crlf_line_endings_are_preserved(tmp_path, out_path):
    original = build_xml().replace("\n", "\r\n").encode("utf-8")
    ptb = tmp_path / "crlf.ptb"
    ptb.write_bytes(gzip.compress(original))

    report = run(ptb, [{"code": "P-03", "new_value": 6.0}], out_path)
    assert report["success"] is True

    written = gzip.decompress(out_path.read_bytes())
    assert b"\r\n" in written
    assert written.endswith(b"</ParamProgram>\r\n")


# ---------------------------------------------------------------------------
# Tool registration stays in sync
# ---------------------------------------------------------------------------

def test_tool_is_registered_in_sync():
    from agent.tools import TOOL_DEFINITIONS, TOOL_MAP

    names = {d["function"]["name"] for d in TOOL_DEFINITIONS}
    assert names == set(TOOL_MAP)
    # The modify tool must NOT be model-visible: the platform calls it
    # itself when the technician approves a proposal card, so the model
    # cannot bypass the approval step.
    assert "modify_ptb_configuration" not in names
    assert "propose_parameter_changes" in names
