---
title: Optional Brake Resistor Installation
drive_model: Optidrive E3
topic: braking
keywords: [brake resistor, brake chopper, dynamic braking, P-34, DC+, BR terminals, thermal overload protection]
source: "Optidrive E3 IP20 User Guide V1.05 (82-E3I20-IN), Section 4.10, p.15"
---

## Overview (Section 4.10, p.15)

Optidrive E3 Frame Size 2 and above units have a built in Brake Transistor. This allows an external resistor to be connected to the drive to provide improved braking torque in applications that require this. (Parameter P-34, "Brake Chopper Enable (Not Size 1)", enables the chopper — see parameters.json.)

The brake resistor should be connected to the "+" and "BR" terminals as shown in the source diagram.

## Safety warnings (verbatim)

- The voltage level at these terminals may exceed 800VDC.
- Stored charge may be present after disconnecting the mains power.
- Allow a minimum of 10 minutes discharge after power off before attempting any connection to these terminals. (The wiring diagram caption on the same page separately states "Allow a minimum of 5 minutes discharge" — both figures appear on p.15 as printed; see REVIEW_NOTES.md.)

Suitable resistors and guidance on selection can be obtained from your Invertek Sales Partner.

## Thermal overload protection of the resistor (Section 4.10, p.15)

It is highly recommended to equip the drive with a main contactor (source prints "contractor") and provide and use an additional thermal overload protection for braking resistor. The contactor should be wired so that it opens in case the resistor overheats, otherwise the drive will not be able to interrupt the main supply if the brake chopper remains closed (short-circuited) in a faulty situation. It is also recommended to wire the thermal overload protection to a digital input of the drive as an External Trip.

Related fault codes: OI-b (01, Brake channel over current) — "Check external brake resistor condition and connection wiring."; OL-br (02, Brake resistor overload) — "The drive has tripped to prevent damage to the brake resistor." Recommended brake resistance values per rating are in the Rating Tables (Section 9.2, p.36; see reference/rating-tables.md).
