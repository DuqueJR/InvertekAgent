"""Agent-facing drive tools.

These are the only ways the model touches the drive, and none of them
writes anything: reads feed the diagnosis, and propose_parameter_changes
merely validates a change set and hands it to the platform, which renders
the preview card whose Approve button performs the actual write (see
drive/apply.py). The `drive` argument is injected by the platform from the
session's connection; the model cannot choose or fabricate it.
"""

import json


def _no_drive() -> str:
    return json.dumps({
        "error": (
            "No drive is connected. Ask the technician to connect the drive "
            "from the connection panel (simulator or USB-RS485), or continue "
            "with the uploaded .ptb file and the knowledge base."
        ),
    })


def _registry():
    try:
        from tools.ptb.registry import load_registry
    except ImportError:  # running as the agent.* package (tests)
        from agent.tools.ptb.registry import load_registry
    return load_registry("E3")


def read_drive_status(drive=None) -> str:
    """Live status of the connected drive as JSON."""
    if drive is None or not drive.is_connected:
        return _no_drive()
    try:
        status = drive.read_status()
    except Exception as exc:
        return json.dumps({"error": f"Status read failed: {exc}"})
    return json.dumps(status.to_dict(), ensure_ascii=False)


def read_trip_history(drive=None) -> str:
    """Last four trips of the connected drive as JSON, newest first."""
    if drive is None or not drive.is_connected:
        return _no_drive()
    try:
        trips = drive.read_trip_history()
    except Exception as exc:
        return json.dumps({"error": f"Trip history read failed: {exc}"})
    payload = {
        "trips": [t.to_dict() for t in trips],
        "note": (
            "Positions are newest first (0 = most recent). On real hardware "
            "only the active trip is register-backed; the full four-entry "
            "log is on the drive keypad under P00-13."
        ),
    }
    return json.dumps(payload, ensure_ascii=False)


def read_parameters(codes=None, drive=None, ptb_path=None) -> str:
    """Read current values of specific parameters, as JSON.

    Prefers the connected drive (live truth) and falls back to the uploaded
    .ptb file. Never guesses: a code that cannot be read is reported as
    unavailable with the reason.
    """
    registry = _registry()
    if not isinstance(codes, list) or not codes:
        return json.dumps({
            "error": "Provide a list of parameter codes, e.g. ['P-03','P-08'].",
        })

    live = drive is not None and drive.is_connected
    from_file = {}
    if not live and ptb_path:
        try:
            from .ptb import read_ptb_parameters
            from_file = read_ptb_parameters(ptb_path, codes)
        except Exception:
            from_file = {}

    values, unavailable = [], []
    for raw_code in codes:
        code = str(raw_code).strip()
        spec = registry.get(code)
        if spec is None:
            unavailable.append({
                "code": code,
                "reason": f"{code} is not in the E3 parameter registry.",
            })
            continue
        entry = {"code": spec.code, "name": spec.name, "units": spec.units}
        if live:
            try:
                entry["value"] = spec.to_display(drive.read_parameter(code))
                entry["source"] = "drive (live, over Modbus)"
                values.append(entry)
                continue
            except Exception as exc:
                unavailable.append({"code": spec.code, "reason": str(exc)})
                continue
        if code in from_file:
            entry["value"] = from_file[code]
            entry["source"] = "uploaded .ptb file"
            values.append(entry)
        else:
            unavailable.append({
                "code": spec.code,
                "reason": (
                    "No drive is connected and this parameter is not present "
                    "in the uploaded .ptb file. Ask the technician to read it "
                    "from the drive keypad."
                ),
            })

    return json.dumps({
        "parameters": values,
        "unavailable": unavailable,
    }, ensure_ascii=False)


def propose_parameter_changes(changes=None, rationale="", drive=None) -> str:
    """Validate a parameter change set. Never writes anything.

    Returns the validated proposal; the platform renders it as a preview
    card and only the technician's Approve button applies it.
    """
    registry = _registry()
    if not isinstance(changes, list) or not changes:
        return json.dumps({
            "proposal_ok": False,
            "error": "Provide a non-empty list of {code, new_value, reason} changes.",
        })

    validated, rejected = [], []
    for change in changes:
        if not isinstance(change, dict):
            rejected.append({"change": change,
                             "message": "Each change must be an object."})
            continue
        code = str(change.get("code") or "").strip()
        new_value = change.get("new_value")
        reason = str(change.get("reason") or "")
        spec = registry.get(code) if code else None
        if spec is None:
            rejected.append({
                "code": code or "?", "requested_value": new_value,
                "message": f"{code or '?'} is not in the E3 parameter registry.",
            })
            continue
        if spec.is_read_only:
            rejected.append({
                "code": code, "requested_value": new_value,
                "message": f"{code} ({spec.name}) is read-only.",
            })
            continue
        if spec.indexed:
            rejected.append({
                "code": code, "requested_value": new_value,
                "message": (
                    f"{code} ({spec.name}) is an indexed parameter and must "
                    f"be changed on the drive keypad."
                ),
            })
            continue
        try:
            new_raw = spec.to_raw(float(new_value))
        except (TypeError, ValueError, ArithmeticError):
            rejected.append({
                "code": code, "requested_value": new_value,
                "message": f"{new_value!r} is not a numeric value for {code}.",
            })
            continue
        value = float(new_value)
        if spec.min_display is not None and value < spec.min_display:
            rejected.append({
                "code": code, "requested_value": new_value,
                "message": (
                    f"{new_value} is below the documented minimum "
                    f"{spec.min_display} for {code}."
                ),
            })
            continue
        if spec.max_display is not None and value > spec.max_display:
            rejected.append({
                "code": code, "requested_value": new_value,
                "message": (
                    f"{new_value} is above the documented maximum "
                    f"{spec.max_display} for {code}."
                ),
            })
            continue

        current_display = None
        if drive is not None and drive.is_connected:
            try:
                current_display = spec.to_display(drive.read_parameter(code))
            except Exception:
                current_display = None

        validated.append({
            "code": code,
            "name": spec.name,
            "current_display": current_display,
            "new_display": spec.to_display(new_raw),
            "new_value": value,
            "units": spec.units,
            "reason": reason,
        })

    if not validated:
        return json.dumps({
            "proposal_ok": False,
            "rejected": rejected,
            "message": "No change passed validation; nothing was proposed.",
        }, ensure_ascii=False)

    return json.dumps({
        "proposal_ok": True,
        "proposal": {"changes": validated, "rejected": rejected,
                     "rationale": rationale},
        "message": (
            "Proposal validated. The platform now shows the technician a "
            "preview card with Approve and Reject buttons; tell them to "
            "review it below your answer. Nothing has been applied yet, "
            "and you must never claim otherwise."
        ),
    }, ensure_ascii=False)


READ_DRIVE_STATUS_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "read_drive_status",
        "description": (
            "Read the live status of the connected Optidrive E3 over Modbus "
            "RTU: state (running / stopped / tripped / standby), active "
            "fault code and name, output frequency (Hz) and output motor "
            "current (A). Call this first when a drive is connected and the "
            "question concerns its behaviour."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
}

READ_TRIP_HISTORY_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "read_trip_history",
        "description": (
            "Read the connected drive's last four trips (fault code, name, "
            "newest first). Use together with read_drive_status to ground a "
            "diagnosis in what the drive actually recorded."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
}

READ_PARAMETERS_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "read_parameters",
        "description": (
            "Read the CURRENT values of specific Optidrive E3 parameters. "
            "Reads live from the connected drive when there is one, "
            "otherwise from the uploaded .ptb file. Use this before "
            "proposing changes so your diagnosis rests on the drive's "
            "actual settings — never ask the technician to type values you "
            "could read yourself."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "codes": {
                    "type": "array",
                    "description": (
                        "Printed parameter codes to read, e.g. "
                        "['P-03','P-08','P-11']."
                    ),
                    "items": {"type": "string"},
                },
            },
            "required": ["codes"],
        },
    },
}

PROPOSE_CHANGES_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "propose_parameter_changes",
        "description": (
            "Propose a set of Optidrive E3 parameter changes for the "
            "technician to review. This tool only VALIDATES: nothing is "
            "written to the drive or to any file. The platform shows the "
            "technician a preview card (exact from/to values) with Approve "
            "and Reject buttons; only their approval applies the changes. "
            "Values are display values as printed in the user guide "
            "(e.g. seconds, Hz, A)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "changes": {
                    "type": "array",
                    "description": "Parameter changes to propose.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "Printed code, e.g. 'P-03'.",
                            },
                            "new_value": {
                                "type": "number",
                                "description": "New display value.",
                            },
                            "reason": {
                                "type": "string",
                                "description": "Why this change helps.",
                            },
                        },
                        "required": ["code", "new_value", "reason"],
                    },
                },
                "rationale": {
                    "type": "string",
                    "description": (
                        "One-paragraph summary of the diagnosis these "
                        "changes address."
                    ),
                },
            },
            "required": ["changes", "rationale"],
        },
    },
}
