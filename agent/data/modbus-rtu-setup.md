---
title: Fire Mode
drive_model: Optidrive E3
topic: fire-mode
keywords: [fire mode, emergency operation, smoke extraction, P-30, P-15, P-23, protection disabled]
source: "Optidrive E3 IP20 User Guide V1.05 (82-E3I20-IN), Section 7.8, p.31"
---

## Overview (Section 7.8, p.31)

The Fire Mode function is designed to ensure continuous operation of the drive in emergency conditions until the drive is no longer capable of sustaining operation. The Fire Mode input may be a normally open (Close to Activate Fire Mode) or Normally Closed (Open to Activate Fire Mode) according to the setting of P-30 Index 2. In addition, the input may be momentary or maintained type, selected by P-30 Index 3.

This input may be linked to a fire control system to allow maintained operation in emergency conditions, e.g. to clear smoke or maintain air quality within that building.

The fire mode function is enabled when P-15 = 15, 16 or 17, with Digital Input 3 assigned to activate fire mode.

## Protection features disabled in Fire Mode (verbatim)

O-t (Heat-sink Over-Temperature), U-t (Drive Under Temperature), th-FLt (Faulty Thermistor on Heat-sink), E-triP (External Trip), 4-20 F (4-20mA fault), Ph-Ib (Phase Imbalance), P-LoSS (Input Phase Loss Trip), SC-trP (Communications Loss Trip), I_t-trP (Accumulated overload Trip).

## Faults that trip, auto reset and restart in Fire Mode (verbatim)

O-Volt (Over Voltage on DC Bus), U-Volt (Under Voltage on DC Bus), h O-I (Fast Over-current Trip), O-I (Instantaneous over current on drive output), OUt-F (Drive output fault, Output stage trip).

## Related behaviour stated elsewhere in the guide

- Display shows "FirE" while in fire mode; the drive "can't be reset until fire mode is deactivated" (Section 5.2, p.16).
- P-30 Index 2 settings 2 and 3 (fixed speed): Fire Mode Speed is Preset Speed 4 (P-23) (p.21).
- Macro tables note (pp.29–30): "When P-15 = 19, P-30 Index 2 and Index 3 have no effect. When the fire mode input is on, the drive will run regardless of whether the run input is present. Speed reference in Fire Mode is always Preset Speed 4, P-23."
- P-18 setting 10 / P-25 relay-digital settings provide a "Fire Mode Active" output signal (p.20–21).
- P00-47: Index 1 Fire mode total active time; Index 2 Fire Mode Activation Count (p.26).

Note: 'Ph-Ib' and 'SC-trP' are named here in the source but do not appear in the Section 10.1 fault-code table; see REVIEW_NOTES.md.
