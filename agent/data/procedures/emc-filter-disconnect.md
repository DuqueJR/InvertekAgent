---
title: EMC Filter Disconnect (IT / Corner-Grounded Supplies, Leakage Trips, HiPot Testing)
drive_model: Optidrive E3
topic: emc-filter-disconnect
keywords: [EMC screw, VAR screw, IT supply, corner grounded, leakage current, HiPot, flash test, surge suppression]
source: "Optidrive E3 IP20 User Guide V1.05 (82-E3I20-IN), Section 9.5, p.38 and General Information, p.3"
---

## EMC filter disconnect (Section 9.5, p.38 — verbatim)

Drives with an EMC filter have an inherently higher leakage current to Ground (Earth). For applications where tripping occurs the EMC filter can be disconnected (on IP20 units only) by completely removing the EMC screw on the side of the product.

## Surge suppression / HiPot testing (Section 9.5, p.38)

The Optidrive product range has input supply voltage surge suppression components fitted to protect the drive from line voltage transients, typically originating from lightning strikes or switching of high power equipment on the same supply.

When carrying out a HiPot (Flash) test on an installation in which the drive is built, the voltage surge suppression components may cause the test to fail. To accommodate this type of system HiPot test, the voltage surge suppression components can be disconnected by removing the VAR screw. After completing the HiPot test, the screw should be replaced and the HiPot test repeated. The test should then fail, indicating that the voltage surge suppression components are once again in circuit.

## IT / corner-grounded network warning (p.3 — verbatim)

"When installing the drive on any power supply where the phase-ground voltage may exceed the phase-phase voltage (typically IT supply networks or Marine vessels) it is essential that the internal EMC filter ground and surge protection varistor ground (where fitted) are disconnected. If in doubt, refer to your Sales Partner for further information."

The Quick Start Process (step 6, p.5) likewise instructs: "If the supply type is IT or corner grounded, disconnect the EMC filter before connecting the supply."

Note: Section 1.1 (p.4) additionally states "Do not perform any flash test or voltage withstand test on the Optidrive. Any electrical measurements required should be carried out with the Optidrive disconnected." — the HiPot passage above concerns testing the installation the drive is built into.
