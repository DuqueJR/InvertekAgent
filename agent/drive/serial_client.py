"""Modbus RTU client for a real Optidrive E3 over a USB-to-RS485 adapter.

Comms per Section 8.1-8.3 of the IP20 User Guide: RS485 on RJ45 pins 7/8,
8 data bits, no parity, 1 stop bit, drive address in P-36 (default 1).
Register semantics per Section 8.4; see registers.py.

Limitation, documented here on purpose: the guide exposes no Modbus register
for the last-4 trip log (P00-13 is keypad-only), so read_trip_history()
returns the currently active trip plus any trips this client has itself
observed during the session (it logs every error-code transition it sees).
"""

from . import registers as regs
from .base import (
    DriveClient,
    DriveError,
    DriveStatus,
    TripEntry,
    fault_lookup,
    state_label,
)

DEFAULT_BAUD = 115200
DEFAULT_ADDRESS = 1
TIMEOUT_S = 0.5


def list_serial_ports() -> list[str]:
    from serial.tools import list_ports

    return [port.device for port in list_ports.comports()]


class SerialDriveClient(DriveClient):
    def __init__(self, port: str, baud: int = DEFAULT_BAUD,
                 address: int = DEFAULT_ADDRESS):
        self.port = port
        self.baud = baud
        self.address = address
        self._instrument = None
        self._session_trips: list[int] = []
        self._last_fault_seen = 0

    # -- lifecycle -----------------------------------------------------
    def connect(self) -> None:
        import minimalmodbus

        try:
            instrument = minimalmodbus.Instrument(self.port, self.address)
            instrument.serial.baudrate = self.baud
            instrument.serial.bytesize = 8
            instrument.serial.parity = "N"  # serial.PARITY_NONE
            instrument.serial.stopbits = 1
            instrument.serial.timeout = TIMEOUT_S
            instrument.mode = minimalmodbus.MODE_RTU
            # Prove the link before claiming a connection.
            instrument.read_register(
                regs.REG_STATUS_ERROR - regs.ZERO_BASED_OFFSET
            )
        except Exception as exc:
            raise DriveError(
                f"Could not reach a drive on {self.port} at {self.baud} baud, "
                f"address {self.address}: {exc}"
            ) from exc
        self._instrument = instrument

    def disconnect(self) -> None:
        if self._instrument is not None:
            try:
                self._instrument.serial.close()
            except Exception:
                pass
        self._instrument = None

    @property
    def is_connected(self) -> bool:
        return self._instrument is not None

    # -- raw access ------------------------------------------------------
    def _read(self, register: int) -> int:
        self._require_connected()
        try:
            return self._instrument.read_register(
                register - regs.ZERO_BASED_OFFSET
            )
        except Exception as exc:
            raise DriveError(f"Read of register {register} failed: {exc}") from exc

    def _write(self, register: int, raw_value: int) -> None:
        self._require_connected()
        try:
            self._instrument.write_register(
                register - regs.ZERO_BASED_OFFSET, int(raw_value),
                functioncode=6,
            )
        except Exception as exc:
            raise DriveError(
                f"Write of register {register} failed: {exc}"
            ) from exc

    # -- DriveClient -----------------------------------------------------
    def read_status(self) -> DriveStatus:
        status_bits, error_code = regs.split_status_error(
            self._read(regs.REG_STATUS_ERROR)
        )
        running = bool(status_bits & regs.STATUS_BIT_RUNNING)
        tripped = bool(status_bits & regs.STATUS_BIT_TRIPPED)
        standby = bool(status_bits & regs.STATUS_BIT_STANDBY)
        ready = bool(status_bits & regs.STATUS_BIT_READY)

        if tripped and error_code and error_code != self._last_fault_seen:
            self._session_trips.insert(0, error_code)
            del self._session_trips[4:]
        self._last_fault_seen = error_code if tripped else 0

        code, name = fault_lookup(error_code)
        return DriveStatus(
            connected=True,
            running=running,
            tripped=tripped,
            standby=standby,
            ready=ready,
            state_label=state_label(running, tripped, standby),
            fault_number=error_code,
            fault_code=code if tripped else "",
            fault_name=name if tripped else "",
            output_freq_hz=self._read(regs.REG_OUTPUT_FREQ) / regs.FREQ_SCALE,
            output_current_a=(
                self._read(regs.REG_OUTPUT_CURRENT) / regs.CURRENT_SCALE
            ),
        )

    def read_trip_history(self) -> list[TripEntry]:
        # Refresh so the active trip is captured even on the first call.
        self.read_status()
        entries = []
        for position, number in enumerate(self._session_trips[:4]):
            code, name = fault_lookup(number)
            entries.append(TripEntry(number, code, name, position))
        return entries

    def read_parameter(self, code: str) -> int:
        return self._read(regs.param_register(code))

    def write_parameter(self, code: str, raw_value: int) -> None:
        self._write(regs.param_register(code), raw_value)
