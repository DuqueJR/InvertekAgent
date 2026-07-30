---
title: Power Wiring — Earth, Supply, Motor Connection
drive_model: Optidrive E3
topic: power-wiring
keywords: [protective earth, PE, grounding, ELCB, fuses, MCB, input choke, motor cable, star delta, L1 L2 L3, U V W]
source: "Optidrive E3 IP20 User Guide V1.05 (82-E3I20-IN), Sections 4.2–4.5, pp.11–13"
---

## Protective Earth (PE) connection (Section 4.2, pp.11–12)

The ground terminal of each Optidrive should be individually connected DIRECTLY to the site ground bus bar (through the filter if installed). Optidrive ground connections should not loop from one drive to another, or to, or from any other equipment. The Cross sectional area of the PE Conductor must be at least equal to that of the incoming supply conductor. The motor ground must be connected to one of the ground terminals on the drive. To meet UL regulations, UL approved ring crimp terminals should be used for all ground wiring connections.

Ground fault monitoring: as with all inverters, a leakage current to earth can exist. If an ELCB (Earth Leakage Circuit Breaker) is to be used: a Type B Device must be used; the device must be suitable for protecting equipment with a DC component in the leakage current; individual ELCBs should be used for each Optidrive. (Section 1.1, p.4 adds: "The drive may have a leakage current of greater than 3.5mA".)

Shield termination: the motor cable shield connected to the safety ground terminal (drive end) should also be connected to the motor frame (motor end), using a shield terminating or EMI clamp.

## Incoming power connection (Section 4.3, p.12)

For 1 phase supply, connect to L1/L, L2/N. For 3 phase supplies, connect to L1, L2, and L3. Phase sequence is not important. A fixed installation is required according to IEC61800-5-1 with a suitable disconnecting device installed between the Optidrive and the AC Power Source. Suitable fuses: in general, type gG (IEC 60269) or UL type J; in some cases type aR may be required; operating time below 0.5 seconds. Type B MCBs of equivalent rating may be used where allowed. The maximum permissible short circuit current at the power terminals as defined in IEC60439-1 is 100kA. An optional input choke is recommended where supply impedance is low / fault level high, supply is prone to dips or brown outs, imbalance exists (3 phase drives), or supply is via busbar and brush gear (cranes); part numbers OPT-2-Lxxxx-20 per the table on p.12.

## Motor connection (Sections 4.4–4.5, pp.12–13)

Connect the motor to U, V, W using a suitable 3 or 4 core cable; earth conductor at least equal cross-section and same material as phase conductors. Maximum permitted motor cable length for all models: 100 metres shielded, 150 metres unshielded. Where multiple motors are connected to a single drive using parallel cables, an output choke must be installed. Never connect the mains power supply to the Output terminals U, V, W (Section 1.1, p.4). Do not install any type of automatic switchgear between the drive and the motor (Section 1.1, p.4).

Motor terminal box (Section 4.5, p.13): STAR always gives the higher of the two voltage ratings. Incoming 230V + motor 230/400 nameplate = Delta. Incoming 400V + motor 400/690 = Star. Incoming 400V + motor 230/400 = Star.
