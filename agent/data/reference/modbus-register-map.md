---
title: Modbus RTU Register Map and Status Words
drive_model: Optidrive E3
topic: modbus-registers
keywords: [register map, control word, status word, register 2001, register 2005, holding registers]
source: "Optidrive E3 IP20 User Guide V1.05 (82-E3I20-IN), Section 8.4, pp.32–35"
---

## Addressing note (p.32 — verbatim)

"For Master devices which use zero based addressing and therefore treat the first Register address as Register 0, it may be necessary to convert the Register Numbers detailed below by subtracting 1 to obtain the correct Register address."

## Key registers (Section 8.4, p.33)

| Register | Par. | R/W | Function | Range / Explanation |
|---|---|---|---|---|
| 1 | - | R/W | PDO0 Control Word | 0..3. 16 Bit Word. Bit 0: Low = Stop, High = Run Enable. Bit 1: Low = Decel Ramp 1 (P-04), High = Decel Ramp 2 (P-24). Bit 2: Low = No Function, High = Fault Reset. Bit 3: Low – No Function, High = Coast Stop Request. Bit 8: Relay control, 0 = Open, 1 = Close. Bit 9: DO Control, 1 = Off, 0 = On |
| 2 | - | R/W | PDO1 Frequency Setpoint | 0..5000. Setpoint frequency x10, e.g. 100 = 10.0Hz |
| 3 | - | R/W | PI Setpoint / Analog Output Control | 0..4096. 0 - 4096 = 0 - 100.0% |
| 4 | - | R/W | PDO3 | 0..60000. Ramp time in seconds x 100, e.g. 250 = 2.5 seconds |
| 6 | - | R | Drive status / Error code | Low Byte = Drive Error Code; High Byte = Drive Status: Bit 0 Drive Running, Bit 1 Drive Tripped, Bit 5 Standby Mode, Bit 6 Drive Ready |
| 7 | - | R | Output Motor Frequency | 0..20000. Output frequency in Hz x10 |
| 8 | - | R | Output Motor Current | 0..480. Output Motor Current in Amps x10 |
| 11 | - | R | Digital input status | 0..15. Lowest Bit = 1 Input 1 |
| 20 | P00-01 | R | Analog Input 1 value | 0..1000, % of full scale x10 |
| 21 | P00-02 | R | Analog Input 2 value | 0..1000, % of full scale x10 |
| 22 | P00-03 | R | Speed Reference Value | 0..1000, setpoint frequency x10 |
| 23 | P00-08 | R | DC bus voltage | 0..1000 V |
| 24 | P00-09 | R | Drive temperature | 0..100 °C |
| 2001 | - | R | Status Word 2 | see below |
| 2002–2016 | various | R | Motor speed/current/power, torque (±200.0%), DC bus, heatsink temp, analog in 1/2 (0~4096), analog out, PI output, internal temp, output voltage (0–500V), IP66 Pot Input, Trip Code | as printed p.33 |

Parameter access (verbatim): "All user configurable parameters are accessible as Holding Registers... The Register number for each parameter P-04 to P-60 is defined as 128 + Parameter number, e.g. for parameter P-15, the register number is 128 + 15 = 143."

## Register 2001 – New Status Word (Section 8.4.2, p.34)

Bit 0 Ready; Bit 1 Running; Bit 2 Tripped; Bit 3 Standby; Bit 4 Fire Mode; Bit 5 Reserved; Bit 6 Speed Set-point Reached (At Speed); Bit 7 Below Minimum Speed; Bit 8 Overload (set if motor current > P-08); Bit 9 Mains Loss; Bit 10 Heatsink > 85°C; Bit 11 Control Board > 80°C; Bit 12 Switching Frequency Reduction; Bit 13 Reverse Rotation; Bit 14 Reserved; Bit 15 Live Toggle Bit.

## Register 2005 – IO Status Word (Section 8.4.3, p.35)

Bit 0–3: DI1–DI4 status; Bit 6 IP66 Switch FWD; Bit 7 IP66 Switch REV; Bit 8 Digital Output Status; Bit 9 Relay Output Status; Bit 12 Analog Input 1 Signal Lost (4-20mA); Bit 13 Analog Input 2 signal Lost (4-20mA); Bit 15 IP66 Pot Input > 50%; Bits 4, 5, 10, 11, 14 Reserved.

Drive Ready (Bit 6 of register 6 High Byte) is defined as: Not tripped; Hardware enable signal present (DI1 ON); No mains loss condition (Section 8.4.1, p.34).
