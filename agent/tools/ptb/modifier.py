"""modify_ptb_configuration: apply approved parameter changes to an Invertek .ptb.

A .ptb is gzip(UTF-8 XML) in the Invertek ParamProgram namespace. Every
parameter is either an <RParam> (numeric, carries <min>/<max>) or an <LParam>
(enumerated list), addressed by the unique key (groupNum, paramNum).

This tool does not reason about drives. The agent has already diagnosed the
problem and a human has approved the change list; the tool only reads the
file, applies exactly the requested parameters, validates them, writes a new
file and reports what happened. Everything it does not touch is preserved
byte for byte.
"""

import gzip
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree

from .registry import RegistryError, is_valid_code, load_registry

GZIP_MAGIC = b"\x1f\x8b"

TYPE_BY_TAG = {"RParam": "R", "LParam": "L"}

ERROR_TYPES = (
    "invalid_code_format",
    "unknown_parameter",
    "readonly_group",
    "multi_value_forbidden",
    "out_of_range",
    "type_mismatch",
    "parameter_not_in_file",
    "io_error",
)


class PtbIOError(Exception):
    """Reading, parsing or writing the .ptb failed."""


# ---------------------------------------------------------------------------
# File I/O — gzip envelope and XML prologue are preserved verbatim
# ---------------------------------------------------------------------------

def _read_ptb(path: Path) -> tuple[bytes, bool]:
    """Return (xml_bytes, was_gzipped). Plain-XML .ptb files are tolerated."""
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise PtbIOError(f"Input .ptb file not found: {path}") from exc
    except OSError as exc:
        raise PtbIOError(f"Could not read input .ptb file {path}: {exc}") from exc

    if raw[:2] == GZIP_MAGIC:
        try:
            return gzip.decompress(raw), True
        except (OSError, EOFError, gzip.BadGzipFile) as exc:
            raise PtbIOError(
                f"Input file {path} has a gzip header but could not be "
                f"decompressed: {exc}"
            ) from exc
    return raw, False


def _write_ptb(path: Path, xml_bytes: bytes, gzipped: bool) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if gzipped:
            # mtime=0 keeps the output reproducible for identical input.
            payload = gzip.compress(xml_bytes, compresslevel=9, mtime=0)
        else:
            payload = xml_bytes
        path.write_bytes(payload)
    except OSError as exc:
        raise PtbIOError(f"Could not write output .ptb file {path}: {exc}") from exc


def _split_envelope(xml_bytes: bytes) -> tuple[bytes, bytes]:
    """Return (prologue, epilogue) — the bytes lxml will not reproduce.

    The prologue is the BOM + <?xml ...?> declaration + the whitespace before
    the root element: lxml can re-emit a declaration, but not necessarily with
    the original quoting, casing or encoding label. The epilogue is the
    trailing whitespace after the root element, which the parser discards.
    Both are kept verbatim and wrapped back around the serialised tree.
    """
    stripped = xml_bytes.rstrip(b" \t\r\n")
    epilogue = xml_bytes[len(stripped):]

    idx = xml_bytes.find(b"?>")
    if idx == -1:
        return b"", epilogue

    end = idx + 2
    while end < len(xml_bytes) and xml_bytes[end] in b"\r\n\t ":
        end += 1
    return xml_bytes[:end], epilogue


def _empty_tag_style(xml_bytes: bytes) -> dict:
    """Map tag name -> its original empty-element spelling.

    lxml always serialises an empty element as <x/>, but .NET's XmlSerializer —
    which produces these files — writes <x /> or <x></x>. Rewriting those would
    touch parts of the file this tool is not supposed to change, so the original
    spelling is recorded here and restored after serialisation.
    """
    styles = {}
    for tag in re.findall(rb"<([A-Za-z_][\w.:-]*)\s*/>", xml_bytes):
        if b"<" + tag + b" />" in xml_bytes:
            styles[tag] = b"<" + tag + b" />"
    for tag in re.findall(rb"<([A-Za-z_][\w.:-]*)></\1>", xml_bytes):
        styles[tag] = b"<" + tag + b"></" + tag + b">"
    return styles


def _parse(xml_bytes: bytes, source: Path):
    parser = etree.XMLParser(remove_blank_text=False, strip_cdata=False)
    try:
        return etree.fromstring(xml_bytes, parser=parser)
    except etree.XMLSyntaxError as exc:
        raise PtbIOError(
            f"Input file {source} is not well-formed XML: {exc}"
        ) from exc


def _serialise(root, prologue: bytes, epilogue: bytes, empty_styles: dict) -> bytes:
    body = etree.tostring(
        root, encoding="utf-8", xml_declaration=False, with_tail=False
    )
    for tag, spelling in empty_styles.items():
        body = body.replace(b"<" + tag + b"/>", spelling)
    return prologue + body + epilogue


# ---------------------------------------------------------------------------
# XML navigation
# ---------------------------------------------------------------------------

def _ns_of(el) -> str:
    """Return the '{uri}' tag prefix used by an element, or '' if unqualified."""
    tag = el.tag
    if isinstance(tag, str) and tag.startswith("{"):
        return tag[: tag.index("}") + 1]
    return ""


def _text(root, ns: str, tag: str):
    el = root.find(f".//{ns}{tag}")
    return el.text.strip() if el is not None and el.text else None


def _int_or_none(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _index_parameters(root, ns: str) -> dict:
    """Map (groupNum, paramNum) -> {element, tag, values}.

    Later duplicates of the same address are ignored; the file is expected to
    hold each address once.
    """
    index = {}
    for tag in ("RParam", "LParam"):
        for el in root.iter(f"{ns}{tag}"):
            group = _int_or_none(_child_text(el, ns, "groupNum"))
            param = _int_or_none(_child_text(el, ns, "paramNum"))
            if group is None or param is None:
                continue
            key = (group, param)
            if key in index:
                continue
            index[key] = {
                "element": el,
                "tag": tag,
                "value_elements": el.findall(f"{ns}currentValue"),
            }
    return index


def _child_text(el, ns: str, tag: str):
    child = el.find(f"{ns}{tag}")
    return child.text if child is not None and child.text is not None else None


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------

def _rejection(code, requested_value, error_type, message: str) -> dict:
    # error_type is None only for changes that passed validation but were
    # dropped because strict mode aborted the batch.
    assert error_type is None or error_type in ERROR_TYPES, (
        f"unknown error_type {error_type!r}"
    )
    return {
        "code": code,
        "requested_value": requested_value,
        "error_type": error_type,
        "message": message,
    }


def _failure_report(rejected: list, warnings=None, **meta) -> str:
    report = {
        "success": False,
        "output_path": None,
        "drive_type": meta.get("drive_type"),
        "drive_version": meta.get("drive_version"),
        "drive_code": meta.get("drive_code"),
        "total_changes_requested": meta.get("total_changes_requested", len(rejected)),
        "applied_count": 0,
        "rejected_count": len(rejected),
        "applied": [],
        "rejected": rejected,
        "warnings": warnings or [],
    }
    return json.dumps(report, ensure_ascii=False, indent=2)


def _dump(report: dict) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Public tool
# ---------------------------------------------------------------------------

def read_ptb_parameters(ptb_input_path: str, codes=None) -> dict:
    """Read current parameter values out of a .ptb file.

    Returns {code: display_value} for the requested codes (all registry
    codes present in the file when `codes` is None). Codes absent from the
    file or the registry are simply omitted — callers report them as
    unknown rather than guessing.
    """
    registry = load_registry("E3")
    xml_bytes, _ = _read_ptb(Path(ptb_input_path))
    root = _parse(xml_bytes, Path(ptb_input_path))
    ns = _ns_of(root)
    index = _index_parameters(root, ns)

    wanted = list(codes) if codes else list(registry.parameters)
    values = {}
    for code in wanted:
        spec = registry.get(code)
        if spec is None:
            continue
        entry = index.get((spec.group_num, spec.param_num))
        if entry is None or not entry["value_elements"]:
            continue
        raw = _int_or_none(entry["value_elements"][0].text)
        if raw is None:
            continue
        values[spec.code] = spec.to_display(raw)
    return values


def modify_ptb_configuration(
    ptb_input_path: str,
    changes: list,
    output_path: str,
    strict: bool = True,
) -> str:
    """Apply approved parameter changes to a .ptb file.

    Args:
        ptb_input_path: path to the current .ptb on disk.
        changes: list of {"code", "new_value", "reason"} dicts. `new_value` is
            in display units (6.0 == 6.0 seconds), not the scaled integer.
        output_path: path for the modified .ptb.
        strict: when True (default) a single failed change aborts everything
            and no output file is produced.

    Returns:
        A JSON string reporting applied and rejected changes.
    """
    in_path = Path(ptb_input_path)
    out_path = Path(output_path)
    warnings: list = []

    if changes is None:
        changes = []
    if not isinstance(changes, list):
        return _failure_report(
            [_rejection(None, None, "type_mismatch",
                        "`changes` must be a list of change objects, got "
                        f"{type(changes).__name__}.")],
            total_changes_requested=0,
        )

    # --- load the descriptor table -----------------------------------------
    try:
        registry = load_registry("E3")
    except RegistryError as exc:
        return _failure_report(
            [_rejection(None, None, "io_error", str(exc))],
            total_changes_requested=len(changes),
        )

    # --- read + parse the input file ---------------------------------------
    try:
        xml_bytes, gzipped = _read_ptb(in_path)
        prologue, epilogue = _split_envelope(xml_bytes)
        empty_styles = _empty_tag_style(xml_bytes)
        root = _parse(xml_bytes, in_path)
    except PtbIOError as exc:
        return _failure_report(
            [_rejection(None, None, "io_error", str(exc))],
            total_changes_requested=len(changes),
        )

    ns = _ns_of(root)
    drive_type = _text(root, ns, "DriveType")
    drive_version = _text(root, ns, "DriveVersion")
    drive_code = _text(root, ns, "DriveCode")

    if drive_type and registry.drive_type and drive_type != registry.drive_type:
        warnings.append(
            f"The file declares DriveType '{drive_type}' but the loaded "
            f"parameter registry describes '{registry.drive_type}'. Parameter "
            f"addresses and scale factors may not apply to this drive."
        )

    param_index = _index_parameters(root, ns)
    if not param_index:
        return _failure_report(
            [_rejection(None, None, "io_error",
                        f"No RParam or LParam elements were found in "
                        f"{in_path}. The file does not look like an Invertek "
                        f"parameter program.")],
            warnings=warnings,
            drive_type=drive_type,
            drive_version=drive_version,
            drive_code=drive_code,
            total_changes_requested=len(changes),
        )

    # --- validate every change (no mutation yet) ---------------------------
    planned: list = []
    rejected: list = []

    for change in changes:
        if not isinstance(change, dict):
            rejected.append(_rejection(
                None, None, "type_mismatch",
                f"Each change must be an object with 'code' and 'new_value', "
                f"got {type(change).__name__}."))
            continue

        code = change.get("code")
        new_value = change.get("new_value")
        reason = change.get("reason") or ""

        outcome = _validate_change(code, new_value, registry, param_index)
        if isinstance(outcome, dict):  # rejection
            rejected.append(outcome)
            continue

        spec, entry, old_raw, new_raw, range_check = outcome
        planned.append({
            "spec": spec,
            "entry": entry,
            "old_raw": old_raw,
            "new_raw": new_raw,
            "reason": reason,
            "requested_value": new_value,
            "range_check": range_check,
        })

    # --- strict mode: one failure aborts the whole batch -------------------
    if strict and rejected:
        aborted = [
            _rejection(
                p["spec"].code, p["requested_value"], None,
                "Change passed validation but was not applied: strict mode "
                "aborted the batch because another change in the same request "
                "failed validation.",
            )
            for p in planned
        ]
        return _failure_report(
            rejected + aborted,
            warnings=warnings,
            drive_type=drive_type,
            drive_version=drive_version,
            drive_code=drive_code,
            total_changes_requested=len(changes),
        )

    # --- non-strict mode with nothing left to apply ------------------------
    if rejected and not planned:
        return _failure_report(
            rejected,
            warnings=warnings,
            drive_type=drive_type,
            drive_version=drive_version,
            drive_code=drive_code,
            total_changes_requested=len(changes),
        )

    # --- mutate: currentValue and userValue both get the new raw value -----
    applied = []
    for plan in planned:
        spec = plan["spec"]
        el = plan["entry"]["element"]
        raw_text = str(plan["new_raw"])

        plan["entry"]["value_elements"][0].text = raw_text
        user_el = el.find(f"{ns}userValue")
        if user_el is not None:
            user_el.text = raw_text
        else:
            warnings.append(
                f"{spec.code} has no <userValue> element; only <currentValue> "
                f"was updated."
            )

        applied.append({
            "code": spec.code,
            "name": spec.name,
            "old_display": spec.to_display(plan["old_raw"]),
            "new_display": spec.to_display(plan["new_raw"]),
            "old_raw": plan["old_raw"],
            "new_raw": plan["new_raw"],
            "units": spec.units,
            "reason": plan["reason"],
            "range_check": plan["range_check"],
        })

    # --- write ------------------------------------------------------------
    try:
        _write_ptb(
            out_path,
            _serialise(root, prologue, epilogue, empty_styles),
            gzipped,
        )
    except PtbIOError as exc:
        return _failure_report(
            rejected + [_rejection(None, None, "io_error", str(exc))],
            warnings=warnings,
            drive_type=drive_type,
            drive_version=drive_version,
            drive_code=drive_code,
            total_changes_requested=len(changes),
        )

    return _dump({
        "success": True,
        "output_path": str(out_path),
        "drive_type": drive_type,
        "drive_version": drive_version,
        "drive_code": drive_code,
        "written_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total_changes_requested": len(changes),
        "applied_count": len(applied),
        "rejected_count": len(rejected),
        "applied": applied,
        "rejected": rejected,
        "warnings": warnings,
    })


def _validate_change(code, new_value, registry, param_index):
    """Validate one change.

    Returns a rejection dict on failure, or
    (spec, index_entry, old_raw, new_raw, range_check) on success.
    """
    # 1. code format
    if not is_valid_code(code):
        return _rejection(
            code, new_value, "invalid_code_format",
            f"Parameter code {code!r} is not a valid Optidrive parameter "
            f"code. Expected a form such as 'P-03' or 'P00-13'.")

    code = code.strip()

    # 2. known to the registry
    spec = registry.get(code)
    if spec is None:
        return _rejection(
            code, new_value, "unknown_parameter",
            f"Parameter {code} is not defined in the Optidrive "
            f"{registry.drive_type} registry.")

    # 3. read-only group
    if spec.is_read_only:
        return _rejection(
            code, new_value, "readonly_group",
            f"Parameter {code} ({spec.name}) belongs to group "
            f"{spec.group_num}, the read-only status group. It reports drive "
            f"state and cannot be written.")

    # 4. present in the file
    address = (spec.group_num, spec.param_num)
    entry = param_index.get(address)
    if entry is None:
        return _rejection(
            code, new_value, "parameter_not_in_file",
            f"Parameter {code} maps to address groupNum={address[0]}, "
            f"paramNum={address[1]} (registry convention), but no RParam or "
            f"LParam with that address exists in the file. Either the drive "
            f"does not expose this parameter or the addressing convention "
            f"does not hold for this file.")

    # 5. multi-value / indexed parameters are refused
    if len(entry["value_elements"]) > 1:
        return _rejection(
            code, new_value, "multi_value_forbidden",
            f"Parameter {code} ({spec.name}) holds "
            f"{len(entry['value_elements'])} values in this file (an indexed "
            f"parameter). This tool only writes single-valued parameters.")
    if spec.indexed:
        return _rejection(
            code, new_value, "multi_value_forbidden",
            f"Parameter {code} ({spec.name}) is an indexed multi-value "
            f"parameter according to the registry; per-index writes are not "
            f"supported by this tool.")
    if not entry["value_elements"]:
        return _rejection(
            code, new_value, "parameter_not_in_file",
            f"Parameter {code} exists in the file but has no <currentValue> "
            f"element to write.")

    # 6. type consistency: registry vs file, and numeric input
    file_type = TYPE_BY_TAG.get(entry["tag"])
    if file_type != spec.type:
        return _rejection(
            code, new_value, "type_mismatch",
            f"Registry describes {code} as a {spec.type}Param "
            f"({'numeric' if spec.type == 'R' else 'enumerated'}) but the "
            f"file stores it as {entry['tag']}.")

    if isinstance(new_value, bool) or not isinstance(new_value, (int, float)):
        return _rejection(
            code, new_value, "type_mismatch",
            f"new_value for {code} must be a number in display units, got "
            f"{type(new_value).__name__}.")

    if spec.type == "L" and float(new_value) != int(new_value):
        return _rejection(
            code, new_value, "type_mismatch",
            f"{code} ({spec.name}) is an enumerated parameter and only "
            f"accepts whole-number settings, got {new_value}.")

    old_raw = _int_or_none(entry["value_elements"][0].text)
    if old_raw is None:
        return _rejection(
            code, new_value, "type_mismatch",
            f"The current value of {code} in the file "
            f"({entry['value_elements'][0].text!r}) is not an integer, so it "
            f"cannot be safely rewritten.")

    # 7. scale, then range-check against the file's own bounds
    new_raw = spec.to_raw(new_value)
    el = entry["element"]
    min_raw = _int_or_none(_child_text(el, _ns_of(el), "min"))
    max_raw = _int_or_none(_child_text(el, _ns_of(el), "max"))
    range_check = "file"

    if min_raw is None and max_raw is None:
        # LParam carries no bounds in the file; fall back to the registry.
        range_check = "registry"
        min_raw = (spec.to_raw(spec.min_display)
                   if spec.min_display is not None else None)
        max_raw = (spec.to_raw(spec.max_display)
                   if spec.max_display is not None else None)
        if min_raw is None and max_raw is None:
            range_check = "skipped"

    units = f" {spec.units}" if spec.units else ""
    bound_source = {
        "file": "the file's own <min>/<max>",
        "registry": f"the Optidrive {registry.drive_type} registry",
    }.get(range_check, range_check)

    if min_raw is not None and new_raw < min_raw:
        return _rejection(
            code, new_value, "out_of_range",
            f"{new_value}{units} for {code} ({spec.name}) scales to raw "
            f"{new_raw}, below the minimum raw {min_raw} "
            f"(= {spec.to_display(min_raw)}{units}) allowed by "
            f"{bound_source}.")
    if max_raw is not None and new_raw > max_raw:
        return _rejection(
            code, new_value, "out_of_range",
            f"{new_value}{units} for {code} ({spec.name}) scales to raw "
            f"{new_raw}, above the maximum raw {max_raw} "
            f"(= {spec.to_display(max_raw)}{units}) allowed by "
            f"{bound_source}.")

    return spec, entry, old_raw, new_raw, range_check


MODIFY_PTB_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "modify_ptb_configuration",
        "description": (
            "Modify specific parameters of an Invertek Optidrive .ptb "
            "configuration file. The tool applies the changes to the "
            "existing .ptb, validating ranges and types, and writes a new "
            ".ptb file to disk; the human operator reviews the resulting "
            "change report and decides whether to use the file. It never "
            "modifies read-only parameters (group P00) or the fault log. "
            "Returns a JSON report of applied and rejected changes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ptb_input_path": {
                    "type": "string",
                    "description": "Path to the current .ptb file on disk.",
                },
                "changes": {
                    "type": "array",
                    "description": "List of approved parameter changes to apply.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Parameter code, e.g. 'P-03'.",
                            },
                            "new_value": {
                                "type": "number",
                                "description": (
                                    "New value in display units "
                                    "(e.g. 6.0 for 6.0 seconds)."
                                ),
                            },
                            "reason": {
                                "type": "string",
                                "description": "Short justification for the change.",
                            },
                        },
                        "required": ["code", "new_value"],
                    },
                },
                "output_path": {
                    "type": "string",
                    "description": (
                        "Path where the modified .ptb file will be written."
                    ),
                },
                "strict": {
                    "type": "boolean",
                    "description": (
                        "If true (default), aborts and produces no output file "
                        "if any change fails validation."
                    ),
                    "default": True,
                },
            },
            "required": ["ptb_input_path", "changes", "output_path"],
        },
    },
}
