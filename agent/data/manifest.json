{
  "drive_model": "Optidrive E3",
  "kb_built": "2026-07-25",
  "built_from": [
    {
      "document": "Optidrive ODE-3 (E3) IP20 User Guide, Revision 1.05, document code 82-E3I20-IN, for firmware 3.11",
      "file": "82-E3I20-IN_V1.05 E3 IP20 User Guide V1.04 ENGLISH.pdf",
      "pages": 40,
      "role": "PRIMARY source — standard three-phase (and single-phase-input) IP20 Optidrive E3. All entries cite this document unless stated otherwise.",
      "note": "The uploaded filename says 'User Guide V1.04' but the document itself is Revision 1.05 (footer on every page; revision statement p.3)."
    },
    {
      "document": "Optidrive E3 IP66 Indoor User Guide, Version 2.00, document code 82-E3MAN-IN",
      "file": "(82-E3MAN-IN) E3 IP66 Indoor User Guide V2.00.pdf",
      "pages": 40,
      "role": "Variant document — used only to cross-check the fault-code table and to source IP66-only fault codes (labelled via variant_note)."
    },
    {
      "document": "Optidrive E3 IP66 Outdoor Rated User Guide, Version 1.26",
      "file": "E3 IP66 Outdoor User Guide V1.26.pdf",
      "pages": 58,
      "role": "Variant document — used only to cross-check the fault-code table (its section 11.1, p.56)."
    }
  ],
  "source_pdf_location": "../source-pdfs/ (copies of the three uploaded PDFs, kept alongside the KB for citation resolution)",
  "conventions": {
    "citation": "Every entry carries a source object: document + section + printed page number. Printed page numbers in the IP20 guide match PDF page indices.",
    "verbatim": "All codes, parameter IDs, numeric values and units are verbatim from the source. Suspected source errata are recorded as printed and flagged in REVIEW_NOTES.md, never corrected.",
    "schema_extensions": "fault_codes.json adds 'variant_note' and 'general_notes'; parameters.json adds 'settings', 'indices', 'group', 'related' and a separate 'read_only_status_parameters' array. 'category' values in fault_codes.json are curator-assigned groupings, not from the source. Both files carry a '_schema_notes' block documenting this.",
    "display_codes": "Drive display mnemonics are printed in a 7-segment style font in the PDFs and were transcribed from rendered page images; ambiguous glyphs are flagged source_unclear (see REVIEW_NOTES.md)."
  },
  "files": [
    { "path": "fault_codes.json", "type": "structured", "contents": "fault/trip codes (26 from IP20 guide table incl. No Fault, plus 5 IP66-documented codes labelled via variant_note) + 4 sourced general notes", "entry_count": 31 },
    { "path": "parameters.json", "type": "structured", "contents": "settable parameters P-01..P-63, P-66 (Standard 14, Extended 36, Advanced 14; indexed parameters carry per-index ranges/defaults)", "entry_count": 64 },
    { "path": "parameters.json#read_only_status_parameters", "type": "structured", "contents": "P00-01..P00-50 read-only status parameters (incl. Trip Log P00-13 and pre-trip data logs)", "entry_count": 50 },
    { "path": "procedures/commissioning-basic.md", "type": "prose", "topic": "commissioning" },
    { "path": "procedures/storage-capacitor-reforming.md", "type": "prose", "topic": "storage" },
    { "path": "procedures/keypad-operation.md", "type": "prose", "topic": "keypad" },
    { "path": "procedures/parameter-and-fault-reset.md", "type": "prose", "topic": "reset" },
    { "path": "procedures/motor-thermistor-connection.md", "type": "prose", "topic": "motor-protection" },
    { "path": "procedures/brake-resistor-installation.md", "type": "prose", "topic": "braking" },
    { "path": "procedures/fire-mode.md", "type": "prose", "topic": "fire-mode" },
    { "path": "procedures/single-phase-operation.md", "type": "prose", "topic": "single-phase-operation" },
    { "path": "procedures/modbus-rtu-setup.md", "type": "prose", "topic": "modbus" },
    { "path": "procedures/emc-filter-disconnect.md", "type": "prose", "topic": "emc-filter-disconnect" },
    { "path": "reference/product-overview.md", "type": "prose", "topic": "product-overview" },
    { "path": "reference/model-numbers.md", "type": "prose", "topic": "model-numbers" },
    { "path": "reference/control-terminals.md", "type": "prose", "topic": "control-terminals" },
    { "path": "reference/power-wiring.md", "type": "prose", "topic": "power-wiring" },
    { "path": "reference/mechanical-installation.md", "type": "prose", "topic": "mechanical-installation" },
    { "path": "reference/emc-compliant-installation.md", "type": "prose", "topic": "emc" },
    { "path": "reference/environmental-and-ul.md", "type": "prose", "topic": "environmental" },
    { "path": "reference/rating-tables.md", "type": "prose", "topic": "ratings" },
    { "path": "reference/macro-configurations.md", "type": "prose", "topic": "macros" },
    { "path": "reference/modbus-register-map.md", "type": "prose", "topic": "modbus-registers" },
    { "path": "reference/safety-information.md", "type": "prose", "topic": "safety" },
    { "path": "REVIEW_NOTES.md", "type": "meta", "contents": "verification notes, source errata, cross-document conflicts, omissions, coverage counts" }
  ]
}
