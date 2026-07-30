---
title: Motor Thermal Overload Protection and Motor Thermistor Connection
drive_model: Optidrive E3
topic: motor-protection
keywords: [thermistor, PTC, motor overload, I.t-trP, P-54, P-08, P-47, E-Trip]
source: "Optidrive E3 IP20 User Guide V1.05 (82-E3I20-IN), Section 4.8, p.14"
---

## Internal thermal overload protection (Section 4.8.1, p.14)

Optidrive E3 has internal motor overload protection / current limit set at 150% of FLA. This may be adjusted in parameter P-54. The drive has an in-built motor thermal overload function; this is in the form of an "I.t-trP" trip after delivering >100% of the value set in P-08 for a sustained period of time (e.g. 150% for 60 seconds).

Note: the fault-code table (Section 10.1, p.39) prints this trip's display code as "I_t-trP" (No. 04, Motor Thermal Overload (I2t)); Section 4.8.1 prints it "I.t-trP". Related: P-60 (Motor Overload Management) configures thermal overload retention and the limit reaction (trip vs current limit reduction).

## Motor thermistor connection (Section 4.8.2, p.14)

Where a motor thermistor is to be used, it should be connected between control terminals 1 and 4 (per the Control Terminal Strip illustration in the source).

- Compatible Thermistor: PTC Type, 2.5kΩ trip level.
- Use a setting of P-15 that has Input 3 function as External Trip, e.g. P-15 = 3. Refer to section 7 (Analog and Digital Input Macro Configurations, p.27) for further details.
- Set P-47 = "Ptc-th" (per P-47 settings, p.24: "Use for motor thermistor measurement, valid with any setting of P-15 that has Input 3 as E-Trip. Trip level: 2.5kΩ, reset 2kΩ.").

When the motor thermistor over-temperature condition occurs the drive trips showing E-triP (External trip, No. 11) or F-Ptc (Motor PTC thermistor trip, No. 21) — see fault_codes.json. The E-triP fault table entry states: "If motor thermistor is connected check if the motor is too hot."
