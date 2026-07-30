"""Modbus RTU register map for the Optidrive E3.

Transcribed from the knowledge base document "Modbus RTU Register Map and
Status Words" (Optidrive E3 IP20 User Guide V1.05, 82-E3I20-IN, Section 8.4,
pp.32-35). Register numbers below are as printed in the guide; masters that
use zero-based addressing (minimalmodbus does) must subtract 1, per the
addressing note on p.32.
"""

REG_CONTROL_WORD = 1        # bit 0: 1 = run enable, 0 = stop; bit 2: fault reset
REG_FREQ_SETPOINT = 2       # 0..5000, Hz x10
REG_STATUS_ERROR = 6        # low byte = error code; high byte = status bits
REG_OUTPUT_FREQ = 7         # 0..20000, Hz x10
REG_OUTPUT_CURRENT = 8      # 0..480, A x10
REG_DC_BUS_V = 23           # P00-08, V x1
REG_TEMP_C = 24             # P00-09, degC x1
REG_STATUS_WORD_2 = 2001    # extended status word, Section 8.4.2 p.34

ZERO_BASED_OFFSET = 1

# Register 6 high byte (Section 8.4, p.33).
STATUS_BIT_RUNNING = 1 << 0
STATUS_BIT_TRIPPED = 1 << 1
STATUS_BIT_STANDBY = 1 << 5
STATUS_BIT_READY = 1 << 6

# Control word bits (Section 8.4, p.33).
CONTROL_BIT_RUN = 1 << 0
CONTROL_BIT_FAULT_RESET = 1 << 2

# "The Register number for each parameter P-04 to P-60 is defined as
# 128 + Parameter number" (Section 8.4, p.33). The formula is documented
# for that range only.
PARAM_REG_BASE = 128
PARAM_REG_MIN = 4
PARAM_REG_MAX = 60

FREQ_SCALE = 10
CURRENT_SCALE = 10


def split_status_error(raw: int) -> tuple[int, int]:
    """Split register 6 into (status_bits, error_code)."""
    return (raw >> 8) & 0xFF, raw & 0xFF


def param_register(code: str) -> int:
    """Printed parameter code -> Modbus register number (guide numbering).

    Only P-04..P-60 have a documented register; everything else (including
    the read-only P00-xx group) raises ValueError so callers fail loudly
    instead of writing to an undocumented address.
    """
    try:
        from tools.ptb.registry import derive_address
    except ImportError:  # running as the agent.* package (tests)
        from agent.tools.ptb.registry import derive_address

    group_num, param_num = derive_address(code)
    if group_num != 1:
        raise ValueError(
            f"{code} has no documented Modbus register (only P-04..P-60 do)."
        )
    if not PARAM_REG_MIN <= param_num <= PARAM_REG_MAX:
        raise ValueError(
            f"{code} is outside the documented Modbus range P-04..P-60; "
            f"change it via a .ptb file or the drive keypad instead."
        )
    return PARAM_REG_BASE + param_num
