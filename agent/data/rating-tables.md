---
title: Analog and Digital Input Macro Configurations
drive_model: Optidrive E3
topic: macros
keywords: [P-12, P-15, digital input functions, terminal mode, keypad mode, fieldbus mode, PI mode, macro key]
source: "Optidrive E3 IP20 User Guide V1.05 (82-E3I20-IN), Section 7, pp.27–31"
---

## Overview (Section 7.1, p.27)

Optidrive E3 uses a Macro approach to simplify the configuration of the Analog and Digital Inputs. Two key parameters determine the input functions and drive behaviour: P-12 selects the main drive control source; P-15 assigns the Macro function to the analog and digital inputs. Additional parameters adapt the settings: P-16 (analog input 1 format), P-30 (start mode after power on), P-31 (keypad-mode start behaviour), P-47 (analog input 2 format).

## Macro functions guide key (Section 7.3, p.28, selected verbatim entries)

STOP = Latched Input, Open the contact to STOP the drive. RUN = Latched input, Close the contact to Start, the drive will operate as long as the input is maintained. FWD / REV = Latched Input, selects the direction of motor rotation. ENABLE = Hardware Enable Input. START = Normally Open, Rising Edge, Close momentarily to START the drive (NC STOP Input must be maintained). FAST STOP (P-24) = Normally Closed, Falling Edge, Open momentarily to FAST STOP the drive using Fast Stop Ramp Time P-24. E-TRIP = Normally Closed, External Trip input; when the input opens momentarily, the drive trips showing E-triP or Ptc-th depending on P-47 setting. Fire Mode = Activates Fire Mode. AI1/AI2 REF = Analog Input 1/2 provides the speed reference. PR-REF = Preset speeds P-20 – P-23 used for speed reference, selected by other digital input status. PI-REF = PI Control Speed Reference. PI FB = Analog Input used as Feedback for the internal PI controller. KPD REF = Keypad Speed Reference. FB REF = Speed reference from Fieldbus. INC SPD / DEC SPD = Normally Open, Rising Edge, close momentarily to increase / decrease the motor speed by value in P-20.

## Terminal Mode (P-12 = 0) — DI functions by P-15 (Section 7.4, p.29)

| P-15 | DI1 (0/1) | DI2 (0/1) | DI3/AI2 (0/1) | DI4/AI1 |
|---|---|---|---|---|
| 0 | STOP / RUN | FWD / REV | AI1 REF / P-20 REF | Analog Input AI1 |
| 1 | STOP / RUN | AI1 REF / PR-REF | P-20 / P-21 | Analog Input AI1 |
| 2 | STOP / RUN | DI2 sel | DI3 sel (P-20…P-23 per DI2/DI3 combination) | P-01 sel |
| 3 | STOP / RUN | AI1 / P-20 REF | E-TRIP / OK | Analog Input AI1 |
| 4 | STOP / RUN | AI1 / AI2 | Analog Input AI2 | Analog Input AI1 |
| 5 | STOP RUN FWD / STOP RUN REV (both = FAST STOP P-24) | — | AI1 / P-20 REF | Analog Input AI1 |
| 6 | STOP / RUN | FWD / REV | E-TRIP / OK | Analog Input AI1 |
| 7 | STOP RUN FWD / STOP RUN REV (both = FAST STOP P-24) | — | E-TRIP / OK | Analog Input AI1 |
| 8 | STOP / RUN | FWD / REV | DI3 sel / DI4 sel (P-20…P-23) | — |
| 9 | STOP START FWD / STOP START REV (FAST STOP P-24) | — | DI3/DI4 preset select | — |
| 10 | (NO) START / STOP (NC) | — | AI1 REF / P-20 REF | Analog Input AI1 |
| 11 | (NO) START FWD / STOP (NC) / (NO) START REV (all = FAST STOP P-24) | — | — | Analog Input AI1 |
| 12 | STOP / RUN | FAST STOP (P-24) / OK | AI1 REF / P-20 REF | Analog Input AI1 |
| 13 | (NO) START FWD / STOP (NC) / (NO) START REV (FAST STOP P-24) | — | KPD REF / P-20 REF | — |
| 14 | STOP / RUN | DI2 sel | E-TRIP / OK | DI2/DI4 preset select |
| 15 | STOP / RUN | P-23 REF / AI1 | Fire Mode | Analog Input AI1 |
| 16 | STOP / RUN | P-23 REF / P-21 REF | Fire Mode | FWD / REV |
| 17 | STOP / RUN | DI2 sel | Fire Mode | DI2/DI4 preset select |
| 18 | STOP / RUN | FWD / REV | Fire Mode | Analog Input AI1 |
| 19 | STOP / RUN | AI1 REF / PR1 REF | No Function / Fire Mode | AI1 |

Preset selection by two digital inputs (settings 2, 8, 9, 14, 17): DI combinations 00→P-20, 10→P-21, 01→P-22, 11→P-23.

NOTE (verbatim, p.29): "When P-15 = 19, P-30 Index 2 and Index 3 have no effect. When the fire mode input is on, the drive will run regardless of whether the run input is present. Speed reference in Fire Mode is always Preset Speed 4, P-23."

CAUTION: this table is a condensed transcription of a complex printed grid. For wiring decisions, verify against the source table (p.29) or the example connection diagrams (Section 7.2, p.27). Keypad Mode (P-12 = 1 or 2), Fieldbus Control Mode (P-12 = 3, 4, 7, 8 or 9) and User PI Control Mode (P-12 = 5 or 6) have their own tables on pp.30–31, not transcribed here — see REVIEW_NOTES.md.
