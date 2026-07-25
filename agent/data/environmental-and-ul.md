---
title: Control Terminal Connections and I/O
drive_model: Optidrive E3
topic: control-terminals
keywords: [control terminals, digital inputs, analog inputs, relay output, analog output, terminal 1-11, wiring]
source: "Optidrive E3 IP20 User Guide V1.05 (82-E3I20-IN), Sections 4.6–4.7, pp.13–14"
---

## Control terminal wiring rules (Section 4.6, p.13)

- All analog signal cables should be suitably shielded. Twisted pair cables are recommended.
- Power and Control Signal cables should be routed separately where possible, and must not be routed parallel to each other.
- Signal levels of different voltages e.g. 24 Volt DC and 110 Volt AC, should not be routed in the same cable.
- Maximum control terminal tightening torque is 0.5Nm.
- Control Cable entry conductor size: 0.05 – 2.5mm2 / 30 – 12 AWG.

## Control terminal connections (Section 4.7, p.13)

| Terminal | Signal | Description |
|---|---|---|
| 1 | +24Vdc User Output | +24Vdc user output, 100mA. Do not connect an external voltage source to this terminal. |
| 2 | Digital Input 1 | Positive logic. "Logic 1" input voltage range: 8V … 30V DC. "Logic 0" input voltage range: 0V … 4V DC |
| 3 | Digital Input 2 | (same logic levels as above) |
| 4 | Digital Input 3 / Analog Input 2 | Digital: 8 to 30V. Analog: 0 to 10V, 0 to 20mA or 4 to 20mA |
| 5 | +10V User Output | +10V, 10mA, 1kΩ minimum |
| 6 | Analog Input 1 / Digital Input 4 | Analog: 0 to 10V, 0 to 20mA or 4 to 20mA. Digital: 8 to 30V |
| 7 | 0V | 0 Volt Common, internally connected to terminal 9 |
| 8 | Analog Output / Digital Output | Analog: 0 to 10V. Digital: 0 to 24V. 20mA maximum |
| 9 | 0V | 0 Volt Common, internally connected to terminal 7 |
| 10 | Auxiliary Relay Common | Contact 250Vac, 6A / 30Vdc, 5A. Intended to drive resistive load. Over voltage category 2. |
| 11 | Auxiliary Relay NO Contact | (as above) |

## I/O configuration (Section 4.7.1–4.7.4, p.14)

- Analog Output: configured by P-25. Analog Mode: 0 – 10 volt DC signal, 20mA max load current. Digital Mode: 24 volt DC, 20mA max load current.
- Relay Output: configured by P-18.
- Analog Inputs: two available, also usable as Digital Inputs. Format selected by P-16 (Analog Input 1) and P-47 (Analog Input 2). Function defined by P-15.
- Digital Inputs: up to four available. Function defined by P-12 and P-15 (see section 7, p.27).
