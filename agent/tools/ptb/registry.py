"""Parameter descriptor tables for Invertek drives.

The .ptb file format stores every parameter as a scaled integer in
<currentValue> and always leaves <decimal> at 0, so the display scaling is
not recoverable from the file itself. That knowledge lives here instead: one
JSON registry per drive model, keyed by the parameter code as printed in the
user guide ("P-03", "P00-01").

See data/e3_registry.json for the provenance of each entry and for the
code -> (groupNum, paramNum) convention.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

# "P-3", "P-03", "P00-13" ... Rejects "P-", "X-03", "P-123".
CODE_PATTERN = re.compile(r"^P\d{0,2}-\d{1,2}$")

REGISTRY_FILES = {
    "E3": "e3_registry.json",
}


class RegistryError(Exception):
    """The registry file is missing or internally inconsistent."""


def is_valid_code(code) -> bool:
    return isinstance(code, str) and bool(CODE_PATTERN.match(code.strip()))


def derive_address(code: str) -> tuple[int, int]:
    """Map a printed parameter code to its (groupNum, paramNum) address.

    Convention (documented in the registry, still to be confirmed against a
    real E3 .ptb): the digits before the dash are the group and the digits
    after it are the parameter number, so "P-03" -> (1, 3) and
    "P00-13" -> (0, 13). A bare "P-XX" has no printed group and means group 1.
    """
    if not is_valid_code(code):
        raise ValueError(f"Invalid parameter code format: {code!r}")

    group_str, param_str = code.strip().split("-", 1)
    group_digits = group_str[1:]
    group_num = int(group_digits) if group_digits else 1
    return group_num, int(param_str)


class ParamSpec:
    """One parameter descriptor."""

    __slots__ = (
        "code", "name", "type", "scale", "units", "min_display",
        "max_display", "group_num", "param_num", "indexed", "provenance",
        "provenance_note",
    )

    def __init__(self, code: str, entry: dict):
        self.code = code
        self.name = entry.get("name") or code
        self.type = entry.get("type")
        self.scale = entry.get("scale", 1)
        self.units = entry.get("units")
        self.min_display = entry.get("min_display")
        self.max_display = entry.get("max_display")
        self.group_num = entry.get("group_num")
        self.param_num = entry.get("param_num")
        self.indexed = bool(entry.get("indexed", False))
        self.provenance = entry.get("provenance")
        self.provenance_note = entry.get("provenance_note")

    @property
    def is_read_only(self) -> bool:
        """Group 0 holds the P00-xx status parameters, which are read-only."""
        return self.group_num == 0

    def to_raw(self, display_value) -> int:
        """Scale a display value to the integer stored in <currentValue>.

        Uses Decimal so that 6.0 s * 100 is exactly 600 and .5 always rounds
        away from zero (Python's round() would bank it to even).
        """
        from decimal import Decimal, ROUND_HALF_UP

        scaled = Decimal(str(display_value)) * Decimal(str(self.scale))
        return int(scaled.quantize(Decimal(1), rounding=ROUND_HALF_UP))

    def to_display(self, raw_value: int):
        """Inverse of to_raw. Returns an int when the scale is 1."""
        if self.scale in (1, None):
            return int(raw_value)
        return int(raw_value) / self.scale


class Registry:
    def __init__(self, payload: dict, path: Path):
        self.path = path
        self.drive_type = payload.get("drive_type")
        self.drive_version = payload.get("drive_version")
        self.source = payload.get("source")
        self.code_to_addr_convention = payload.get("code_to_addr_convention")
        self.parameters = {
            code: ParamSpec(code, entry)
            for code, entry in (payload.get("parameters") or {}).items()
        }
        self._validate()

    def _validate(self):
        """Fail fast if a registry entry contradicts the addressing convention."""
        for code, spec in self.parameters.items():
            if not is_valid_code(code):
                raise RegistryError(
                    f"{self.path.name}: parameter key {code!r} does not match "
                    f"the expected code format."
                )
            if spec.type not in ("R", "L"):
                raise RegistryError(
                    f"{self.path.name}: {code} has type {spec.type!r}, "
                    f"expected 'R' or 'L'."
                )
            expected = derive_address(code)
            if (spec.group_num, spec.param_num) != expected:
                raise RegistryError(
                    f"{self.path.name}: {code} declares address "
                    f"({spec.group_num}, {spec.param_num}) but the "
                    f"code_to_addr_convention derives {expected}."
                )

    def get(self, code: str):
        return self.parameters.get(code.strip()) if isinstance(code, str) else None


@lru_cache(maxsize=None)
def load_registry(drive_type: str = "E3") -> Registry:
    """Load (and cache) the descriptor table for a drive model."""
    filename = REGISTRY_FILES.get(drive_type)
    if filename is None:
        raise RegistryError(
            f"No parameter registry is available for drive type "
            f"{drive_type!r}. Known types: "
            f"{', '.join(sorted(REGISTRY_FILES))}."
        )

    path = DATA_DIR / filename
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistryError(f"Registry file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RegistryError(f"Registry file {path} is not valid JSON: {exc}") from exc

    return Registry(payload, path)
