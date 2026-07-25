---
title: Single Phase Operation of Three Phase Drives
drive_model: Optidrive E3
topic: single-phase-operation
keywords: [single phase supply, derating, 50%, L1 L2, three phase drive]
source: "Optidrive E3 IP20 User Guide V1.05 (82-E3I20-IN), Section 9.3, p.37"
---

## Overview (Section 9.3, p.37 — verbatim)

All drive models intended for operation from three phase mains power supply (e.g. model codes ODE-3-xxxxxx-3xxx) may be operated from a single phase supply at up to 50% of maximum rated output current capacity.

In this case, the AC power supply should be connected to L1 (L) and L2 (N) power connection terminals only.

## Related information

- Incoming power connection rules (Section 4.3.1, p.12): "For 1 phase supply, the mains power cables should be connected to L1/L, L2/N. For 3 phase supplies, the mains power cables should be connected to L1, L2, and L3. Phase sequence is not important."
- Input phase monitoring faults that may be relevant when supply phases are missing or imbalanced on three-phase-supplied drives: P-LOSS (14, Input phase loss trip) and FLt-dc (13, DC bus ripple too high) — see fault_codes.json.
- UL supply requirements (Section 9.4, p.37): "All Optidrive E3 units have phase imbalance monitoring. A phase imbalance of > 3% will result in the drive tripping. For input supplies which have supply imbalance greater than 3% (typically the Indian sub-continent & parts of Asia Pacific including China) Invertek Drives recommends the installation of input line reactors."
