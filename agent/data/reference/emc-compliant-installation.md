---
title: EMC Compliant Installation
drive_model: Optidrive E3
topic: emc
keywords: [EMC, category C1 C2 C3, shielded cable, screened cable, motor cable length, emissions]
source: "Optidrive E3 IP20 User Guide V1.05 (82-E3I20-IN), Section 4.9, p.15"
---

## EMC category cable requirements (Section 4.9, p.15)

| Category | Supply Cable Type | Motor Cable Type | Control Cables | Maximum Permissible Motor Cable Length |
|---|---|---|---|---|
| C1 (note 6) | Shielded (note 1) | Shielded (notes 1, 5) | Shielded (note 4) | 1M / 5M (note 7) |
| C2 | Shielded (note 2) | Shielded (notes 1, 5) | Shielded (note 4) | 5M / 25M (note 7) |
| C3 | Unshielded (note 3) | Shielded (note 2) | Shielded (note 4) | 25M / 100M (note 7) |

Notes (verbatim, abbreviated numbering as in source):

1. A screened (shielded) cable suitable for fixed installation with the relevant mains voltage in use. Braided or twisted type screened cable where the screen covers at least 85% of the cable surface area, designed with low impedance to HF signals. Installation of a standard cable within a suitable steel or copper tube is also acceptable.
2. A cable suitable for fixed installation with relevant mains voltage with a concentric protection wire. Installation of a standard cable within a suitable steel or copper tube is also acceptable.
3. A cable suitable for fixed installation with relevant mains voltage. A shielded type cable is not necessary.
4. A shielded cable with low impedance shield. Twisted pair cable is recommended for analog signals.
5. The cable screen should be terminated at the motor end using an EMC type gland allowing connection to the motor body through the largest possible surface area. Where drives are mounted in a steel control panel enclosure, the cable screen may be terminated directly to the control panel using a suitable EMC clamp or gland, as close to the drive as possible.
6. Compliance with category C1 conducted emissions only is achieved. For compliance with category C1 radiated emissions, additional measures may be required, contact your Sales Partner for further assistance.
7. Permissible cable length with additional external EMC filter.

## Related

An internal EMC filter is fitted on model numbers containing "F" (see reference/model-numbers.md). For IT or corner-grounded supplies the filter must be disconnected — see procedures/emc-filter-disconnect.md. Control cabling separation: "Wherever control cabling is close to power cabling, maintain a minimum separation of 100 mm and arrange crossings at 90 degrees" (Section 1.1, p.4).
