# REVIEW_NOTES — Optidrive E3 Knowledge Base

Built 2026-07-25 from the three PDFs in `../source-pdfs/`. Everything a human should double-check is listed here.

## 1. Sources and identity

- PRIMARY: **Optidrive ODE-3 (E3) IP20 User Guide, Revision 1.05** (82-E3I20-IN), 40 pages, "for use with version 3.11 Firmware" (p.3). NOTE: the uploaded **filename** says "User Guide V1.04 ENGLISH" but the document itself is Revision 1.05 on every footer; p.40 shows a superseded stamp `82-E3I20-IN_V1.04T` next to `82-E3I20-IN_V1.05`. All citations say V1.05.
- VARIANT: E3 IP66 Indoor User Guide V2.00 (82-E3MAN-IN), 40 pages; E3 IP66 Outdoor Rated User Guide V1.26, 58 pages. Used ONLY for fault-table cross-checking and IP66-only fault codes. Their parameter tables, switch/pot operation sections, and the Outdoor guide's CAN section (its §9) were NOT extracted.
- Expected doc #2 (standalone fault-code troubleshooting PDF) and #3 (separate parameter list / quick-start): **Invertek does not publish these as separate documents for the E3** — the official support-resources page offers only the User Guides above, an IP66 Quick Start Guide V1.10, a Fieldbus User Guide V1.02, brochures, CAD and certificates. Fault table and parameter list live inside the User Guide, which is what was extracted. The IP66 Quick Start Guide and Fieldbus User Guide were not provided and not used.

## 2. Extraction & verification method

- Text was extracted per page (pdfplumber, layout mode). Drive display mnemonics are typeset in a **7-segment style font** that garbles plain text extraction, so the fault-code column and all display strings were transcribed visually from 200–220 dpi page renders (pp.16, 17, 18–26, 31, 36, 39 of the IP20 guide; p.39 of the IP66 Indoor guide; plus a 2× zoom of the p.39 code column).
- Second pass: every min/max/default/units cell in parameters.json was verified against the rendered images of pp.18–26; the fault table against two renders of p.39; rating tables and model-number tables against renders of pp.36 and 7. JSON validity and entry counts were machine-checked.

## 3. Entries flagged `source_unclear: true`

- **Fault 12 `SC-Ob5`** — the final 7-segment glyph is inherently ambiguous between `5` and `S` ("SC-ObS" is a plausible alternative reading). Codes 50/51 (`SC-F01`/`SC-F02`) end in clear digits.
- **P-25** — printed Maximum is `12` but the settings list includes `13: Fieldbus Analog`. Recorded as printed.
- **P-28 / P-29** — both rows are printed with the identical name "V/F Characteristic Adjustment Voltage" and share the description "This parameter in conjunction with P-28 sets a frequency point at which the voltage set in P-29 is applied to the motor." Given the units (P-28 = V, P-29 = Hz), the names/description look swapped or mis-edited in the source. Recorded exactly as printed; a human should confirm against a newer manual revision before the agent relies on the P-28/P-29 role split.
- **P-44** — printed Maximum is `1` but the settings list includes `2: Fieldbus`. Recorded as printed.
- **P-47** — the printed row shows `-` in Minimum/Maximum/Default and `U0-10` in the **Units** column. Interpreted as default = U0-10 (matching P-16's layout, where U0-10 is in the Default column). This is the single interpretive step taken in Layer 1.
- **P-60** — the Units column prints `1` for both Index rows (suspected misprint for `-`). Index 2 setting 1 also contains the apparently truncated phrase "reaches 90% of,". Recorded as printed.

## 4. Other source errata / oddities (recorded verbatim, NOT corrected)

- Faults 17/19: "consult **you** supplier".
- Fault 10 (P-dEF) and 16 (th-FLt): the Suggested Remedy cells are blank in the IP20 table.
- P-12 setting 2: "in the forward and reverse directions **u** using the internal keypad".
- P-16 (r 4-20 / r 20-4 rows only): unclosed parenthesis "(P-20 if the signal level falls below 3mA."
- P-30 Index 2 setting 3: double full stop "closed. . Fire Mode Speed".
- P-43 setting 3 says "As setting 0" (setting 2 also says "As setting 0").
- Quick Start step 11: "Ensure wiring protection **is providing**".
- §1.3 (p.6): "a reduced mains voltage mains voltage" (duplicated words).
- §4.10 (p.15): main text says allow **10 minutes** discharge before touching brake terminals; the wiring-diagram caption on the same page says **5 minutes**. Both are in the source; the KB file quotes both.
- §4.10 prints "main **contractor**" (contactor).
- §9.4 prints "Integral Solid **Sate** short circuit protection" and "if the enclosure impacted".
- Model-number table (110–115V section, p.7): the kW column is blank; only HP values are printed.
- Fault-table footer: IP20 says "(3, 4, 15)"; both IP66 guides say "(3, 4, 5, 15)". The IP66 **Outdoor** guide includes '5' in the footer although its own table has **no** 05 row.

## 5. Cross-document fault-table differences (IP20 V1.05 vs IP66 Indoor V2.00 vs IP66 Outdoor V1.26)

- **05 `PS-trP` Power stage trip** — present only in IP66 Indoor V2.00 (p.39). Included in fault_codes.json with a variant_note; sourced to that document.
- **Autotune** — IP20 and IP66 Outdoor list only `AtF-02` (No. 41); IP66 Indoor lists `AtF-01`…`AtF-05` (Nos. 40–44) sharing one description/remedy block (remedy cells for 43/44 blank). Entries 40/42/43/44 are included with variant_notes, sourced to IP66 Indoor.
- **09 U-t remedy differs**: IP20/IP66 Outdoor: "The drive temperature is below the minimum limit and must be increased to operate the drive." IP66 Indoor: "Trip occurs when ambient temperature is less than -10°C. Temperature must be raised over -10°C in order to start the drive."
- **11 E-triP**: IP66 Outdoor shortens "has opened for some reason." to "has opened."
- Otherwise the three tables agree code-for-code (verified line by line).

## 6. Codes/strings referenced in the manual but NOT in the §10.1 fault table

`Ph-Ib` (Phase Imbalance) and `SC-trP` (Communications Loss Trip) — named in §7.8 Fire Mode, p.31. `rEd` (switching frequency reduced, P-17, p.20). Operating/status displays (not faults): `StoP`, `H xx.x`, `A x.x`, `P x.xx`, `FirE` (§5.2 p.16), `Stndby` (P-48, p.24), `P-dEF`/`StoP` after factory reset (§5.5 p.17). `It.trp` appears in P-60's settings text and "I.t-trP" in §4.8.1 — the fault table itself prints `I_t-trP` (04). The display renders "Volt" as 7-seg `uoLt`; the alphabetic forms O-Volt / U-Volt follow the manual's own plain-text usage "O-Volts"/"U-Volts" in P00-34/P00-35.

## 7. Deliberately left out (and why)

- IP66 Indoor/Outdoor variant content beyond the fault table (installation, switched-version pot/switches, Outdoor CAN section, IP66 ratings): out of scope — brief targets the standard three-phase E3; only fault-table variant info was captured and labelled.
- Macro tables for Keypad Mode, Fieldbus Mode and PI Mode (pp.30–31): not transcribed (complex grids; high mis-transcription risk). Terminal Mode (p.29) IS transcribed in reference/macro-configurations.md with an explicit caution note; the file directs wiring decisions back to the source pages. The example connection diagrams (§7.2, p.27) are graphics and were not reproduced.
- Modbus registers 2002–2016 are summarised as a range row in reference/modbus-register-map.md (full row-by-row list is on p.33); registers 1–24 and status words 2001/2005 are fully transcribed.
- Mechanical drawings/images (connection diagram p.11, EMC screw location p.38, keypad illustrations): graphics not reproducible as text; the KB describes them and cites pages.
- UL short-circuit-capacity table (p.37) is summarised in prose in reference/environmental-and-ul.md rather than fully tabulated.
- Inch dimensions in §3.3/3.4 tables were omitted from reference/mechanical-installation.md (mm and lb/kg kept; inches are in the source).

## 8. Coverage counts (sanity check against the manual)

- **Fault codes: 31 entries** = 26 rows in the IP20 §10.1 table (Nos. 00–51 with gaps exactly as printed: no 05, 20, 24, 25, 27–40, 42–49) + 5 IP66-documented codes (05, 40, 42, 43, 44). The IP20 table's 26 rows were counted twice (text layer + image).
- **Parameters: 64 entries** = Standard P-01…P-14 (14) + Extended P-15…P-50 (36) + Advanced P-51…P-63, P-66 (14). No P-64/P-65 exist in the source. Indexed parameters (P-30, P-32, P-36, P-40, P-60) carry 12 index sub-entries in total.
- **Read-only status parameters: 50** (P00-01…P00-50).
- **Layer 2: 10 procedure files + 11 reference files**, all with metadata blocks and per-section page citations.

## 9. Notes for the diagnostic agent's operators

- fault_codes.json splits each Suggested Remedy cell's sentences into description / possible_causes / diagnostic_steps **without rewording** (rule documented in the file's `_schema_notes`). If your retrieval prefers the raw cell text, it can be reconstructed by concatenating those fields in order.
- `category` (faults) is curator-assigned for retrieval only — not from Invertek.
- Schema extensions beyond the requested schema: `variant_note`, `general_notes` (faults); `settings`, `indices`, `group`, `related`, `read_only_status_parameters` (parameters); `_schema_notes` (both). All are documented in-file.
- The KB reflects manual revisions as of the July 2026 downloads from invertekdrives.com. If Invertek releases a newer User Guide revision, re-verify P-28/P-29 and the P-25/P-44 range inconsistencies first — they are the likeliest fixes.
