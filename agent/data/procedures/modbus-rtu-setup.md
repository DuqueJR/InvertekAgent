---
title: Modbus RTU Communications Setup
drive_model: Optidrive E3
topic: modbus
keywords: [Modbus RTU, RS485, RJ45, baud rate, P-36, P-63, SC-F01, comms loss]
source: "Optidrive E3 IP20 User Guide V1.05 (82-E3I20-IN), Sections 8.1–8.3, p.32"
---

## Overview (Section 8.1, p.32)

The Optidrive E3 can be connected to a Modbus RTU network via the RJ45 connector on the front of the drive.

## Modbus RTU specification (Section 8.2, p.32 — verbatim)

Protocol: Modbus RTU. Error check: CRC. Baud rate: 9600bps, 19200bps, 38400bps, 57600bps, 115200bps (default). Data format: 1 start bit, 8 data bits, 1 stop bits, no parity. Physical signal: RS 485 (2-wire). User interface: RJ45. Supported Function Codes: 03 Read Multiple Holding Registers; 06 Write Single Holding Register; 16 Write Multiple Holding Registers (Supported for registers 1 – 4 only).

## RJ45 connector pinout (Section 8.3, p.32)

Pin 1: CAN −; Pin 2: CAN +; Pin 3: 0 Volts; Pin 4: −RS485 (PC); Pin 5: +RS485 (PC); Pin 6: +24 Volt; Pin 7: −RS485 (Modbus RTU); Pin 8: +RS485 (Modbus RTU).

Warning (verbatim): "This is not an Ethernet connection. Do not connect directly to an Ethernet port."

## Wiring notes (Section 8.3, p.32 — verbatim list)

- Use 3 or 4 Conductor Twisted Pair Cable.
- RS485+ and RS485− must be twisted pair.
- Ensure the network taps for the drive are kept as short as possible.
- Using Option OPT-2-BNTSP-IN is preferred.
- Terminate the network cable shield at the controller only. Do not terminate at the drive!
- 0 Volt common must be connected across all devices and to reference 0 Volt terminal at the controller.
- Do not connect the 0V Common of the network to power ground.

## Configuration parameters

P-36 configures address (Index 1: 0–63, default 1), baud rate (Index 2: default 115.2 kbps) and communication loss protection / watchdog timeout (Index 3: default "t 3000" ms; 't' suffix = trip on comms loss, 'r' suffix = coast stop without trip). P-63 selects Standard or Advanced Modbus mode. P-12 = 3 or 4 selects Modbus network control. See parameters.json.

Comms loss trip: SC-F01 (No. 50) — "Check the incoming Modbus RTU connection cable. Check that at least one register is being polled cyclically within the timeout limit set in P-36 Index 3." (Section 10.1, p.39.)
