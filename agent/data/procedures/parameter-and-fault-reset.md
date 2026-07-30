---
title: Resetting Parameters to Factory Defaults and Resetting a Fault
drive_model: Optidrive E3
topic: reset
keywords: [factory reset, P-dEF, fault reset, StoP, trip reset, LED display warnings, auto restart]
source: "Optidrive E3 IP20 User Guide V1.05 (82-E3I20-IN), Sections 5.5–5.7 p.17, Section 10.1 p.39, P-30 p.21"
---

## Resetting parameters to factory defaults (Section 5.5, p.17)

To reset parameter values to their factory default settings, press and hold Up, Down and Stop buttons for > 2 seconds. The display will show "P-dEF". Press the Stop key. The display will show "StoP".

## Resetting a fault (Section 5.6, p.17)

With a fault code shown (the source illustration shows "O-I"): Press the Stop key. The display will show "StoP".

Reset timing restriction (Section 10.1, p.39): "Following an over current or overload trip (3, 4, 15), the drive may not be reset until the reset time delay has elapsed to prevent damage to the drive." The O-I (03) and h O-I (15) table entries additionally state: "Following a trip, the drive cannot be immediately reset. A delay time is inbuilt, which allows the power components of the drive time to recover to avoid damage."

Automatic restart (P-30 Index 1, p.21): settings AUto-1 to AUto-5 — "Following a trip, the drive will make up to 5 attempts to restart at 20 second intervals. The numbers of restart attempts are counted, and if the drive fails to start on the final attempt, the drive will trip with a fault, and will require the user to manually reset the fault. The drive must be powered down to reset the counter."

Safety note (Section 1.1, p.4): "Do not activate the automatic fault reset function on any systems whereby this may cause a potentially dangerous situation."

## LED display warning indications (Section 5.7, p.17)

Optidrive E3 has a built-in 6 Digit 7 Segment LED Display. Certain warnings are shown by flashing the decimal-point segments (labelled a–f, left to right):

- Segments a, b, c, d, e, f flashing all together: Overload, motor output current exceeds P-08.
- Segments a and f flashing alternately: Mains Loss (Incoming AC power has been removed).
- Segment a flashing: Fire Mode Active.
