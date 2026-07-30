"""Apply an approved parameter change set to a connected drive.

This is the platform side of the approval flow: the model only proposes;
the technician approves in the UI; this module writes. Every write is
verified by reading the register back, and nothing is written unless the
drive is stopped. The report mirrors the .ptb modifier's shape so the UI
renders both with the same code.
"""

from .base import DriveError, DriveNotConnected


def _registry():
    try:
        from tools.ptb.registry import load_registry
    except ImportError:  # running as the agent.* package (tests)
        from agent.tools.ptb.registry import load_registry
    return load_registry("E3")


def _rejection(code, requested_value, error_type, message) -> dict:
    return {
        "code": code,
        "requested_value": requested_value,
        "error_type": error_type,
        "message": message,
    }


def _report(applied, rejected, warnings, total) -> dict:
    return {
        "success": bool(applied) and not rejected,
        "target": "drive",
        "total_changes_requested": total,
        "applied_count": len(applied),
        "rejected_count": len(rejected),
        "applied": applied,
        "rejected": rejected,
        "warnings": warnings,
    }


def _refuse_all(changes, error_type, message) -> dict:
    rejected = [
        _rejection(c.get("code"), c.get("new_value"), error_type, message)
        for c in changes
    ]
    return _report([], rejected, [], len(changes))


def _validate(change, registry):
    """Return (spec, new_raw) or raise ValueError with a rejection tuple."""
    code = (change.get("code") or "").strip()
    new_value = change.get("new_value")
    spec = registry.get(code) if code else None
    if spec is None:
        raise ValueError((code, new_value, "unknown_parameter",
                          f"{code or '?'} is not in the E3 parameter registry."))
    if spec.is_read_only:
        raise ValueError((code, new_value, "read_only",
                          f"{code} ({spec.name}) is a read-only status parameter."))
    if spec.indexed:
        raise ValueError((code, new_value, "indexed",
                          f"{code} ({spec.name}) is an indexed parameter; "
                          f"change it on the drive keypad."))
    try:
        new_raw = spec.to_raw(float(new_value))
    except (TypeError, ValueError, ArithmeticError):
        raise ValueError((code, new_value, "invalid_value",
                          f"{new_value!r} is not a numeric value for {code}."))
    if spec.min_display is not None and float(new_value) < spec.min_display:
        raise ValueError((code, new_value, "out_of_range",
                          f"{new_value} is below the documented minimum "
                          f"{spec.min_display} for {code}."))
    if spec.max_display is not None and float(new_value) > spec.max_display:
        raise ValueError((code, new_value, "out_of_range",
                          f"{new_value} is above the documented maximum "
                          f"{spec.max_display} for {code}."))
    return spec, new_raw


def apply_change_set(drive, changes: list) -> dict:
    """Write approved changes to the drive, read-back verifying each one."""
    registry = _registry()
    total = len(changes)

    if drive is None or not drive.is_connected:
        return _refuse_all(
            changes, "not_connected",
            "No drive is connected; changes were not applied.",
        )

    try:
        status = drive.read_status()
    except DriveError as exc:
        return _refuse_all(changes, "status_read_failed",
                           f"Could not read the drive status: {exc}")

    if status.running:
        return _refuse_all(
            changes, "safety_gate",
            "Drive must be stopped before parameters are written. "
            "Stop the drive and approve again.",
        )

    applied, rejected, warnings = [], [], []
    aborted = False
    for change in changes:
        if aborted:
            rejected.append(_rejection(
                change.get("code"), change.get("new_value"), "not_attempted",
                "Not attempted: an earlier write in this batch failed.",
            ))
            continue
        try:
            spec, new_raw = _validate(change, registry)
        except ValueError as exc:
            rejected.append(_rejection(*exc.args[0]))
            continue

        try:
            old_raw = drive.read_parameter(spec.code)
            drive.write_parameter(spec.code, new_raw)
            read_back = drive.read_parameter(spec.code)
        except (ValueError, KeyError) as exc:
            # The transport refused the code itself (e.g. P-01..P-03 have no
            # documented Modbus register): reject the item, keep the batch.
            rejected.append(_rejection(
                spec.code, change.get("new_value"),
                "not_writable_over_modbus", str(exc),
            ))
            continue
        except (DriveError, DriveNotConnected) as exc:
            rejected.append(_rejection(
                spec.code, change.get("new_value"), "write_failed", str(exc),
            ))
            aborted = True
            continue

        verified = read_back == new_raw
        if not verified:
            rejected.append(_rejection(
                spec.code, change.get("new_value"), "verify_failed",
                f"Read-back returned {spec.to_display(read_back)} instead of "
                f"{spec.to_display(new_raw)}; the drive did not accept the "
                f"write. Remaining changes were not attempted.",
            ))
            aborted = True
            continue

        applied.append({
            "code": spec.code,
            "name": spec.name,
            "old_display": spec.to_display(old_raw),
            "new_display": spec.to_display(new_raw),
            "old_raw": old_raw,
            "new_raw": new_raw,
            "units": spec.units,
            "reason": change.get("reason", ""),
            "verified": True,
        })

    return _report(applied, rejected, warnings, total)
