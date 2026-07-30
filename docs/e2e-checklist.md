# End-to-end verification checklist

Run this before a demo. It needs no drive hardware: the simulator behaves
like a real E3 over the same interface. Roughly five minutes.

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests/          # 69 tests, all green
cd agent && ../.venv/bin/streamlit run client.py
```

`client.py` uses flat imports, so it **must** be launched from inside
`agent/`. `.env` must hold `DEEPSEEK_API_KEY`.

## 1. Connect the drive

- [ ] Sidebar shows **Drive connection** with Simulator selected.
- [ ] Press **Connect**. The status card appears: red **Tripped** chip,
      output frequency `0.0 Hz`, output current `0.00 A`, active fault
      `O-I · Output Over Current`.
- [ ] **Trip history (last 4)** lists `O-I`, `O-I`, `I_t-trP`, `E-triP`.
- [ ] **Simulator controls** appear. Press **Run**: the chip turns green
      (**Running**), frequency reads ~50 Hz and current ~2 A. Press
      **Stop**: back to **Stopped**. Press **Trip**: back to
      **Tripped / O-I**.
- [ ] If the sidebar is collapsed, the `»` chevron at the top left
      reopens it. (It lives in the Streamlit toolbar; do not hide the
      toolbar or the panel becomes unreachable.)

## 2. Diagnose with citations

Leave the drive connected and tripped.

- [ ] Ask: *"The drive keeps tripping on overcurrent every time the
      motor starts. What should I do?"*
- [ ] The agent reads live status and trip history before answering — the
      diagnosis refers to the actual `O-I` trip and the preceding
      `I_t-trP` thermal trip, not to generic advice.
- [ ] It calls `read_parameters` rather than asking you to type values in
      from the keypad. With the default simulator bank it finds
      `P-08 = 0.0 A` and identifies that as the cause of the instant trip.
- [ ] Every factual claim ends with a citation naming the document,
      section and printed page, e.g. *"Source: Optidrive E3 IP20 User
      Guide V1.05 (82-E3I20-IN), 10.1 Fault Code Messages, p.39"*.
- [ ] Citation chips appear under the answer (section, page, relevance),
      with a **Reference documents (n)** expander below.
- [ ] Physical checks are given as numbered steps, separately from the
      parameter proposal.

## 3. Approve a parameter change

- [ ] A **Proposed parameter changes · Awaiting your approval** card is
      shown: code, parameter name, `current → new`, and a reason per row.
      Current values are the ones read from the drive.
- [ ] The answer states plainly that nothing has been written yet.
- [ ] Press **Approve and apply**.
- [ ] The card turns green: **Applied and verified**.
- [ ] A **Drive updated - every write verified by read-back** report
      lists each parameter that was written.
- [ ] Re-ask *"what is P-08 now?"* — the agent reads the new value back
      from the drive, proving the write landed.

## 4. Safety gate and retry

- [ ] Press **Run** in the simulator controls, then ask directly for a
      change — *"Set the deceleration ramp time to 12 seconds"* — and press
      **Approve and apply**.
- [ ] The apply is refused. The card reads **Not applied - see details**
      and the report says *"Drive must be stopped before parameters are
      written. Stop the drive and approve again."* Nothing is written.
- [ ] The buttons remain, now labelled **Retry apply** — the instruction to
      approve again has to be followable.
- [ ] Press **Stop**, then **Retry apply**. The card turns green
      (**Applied and verified**), the drive report shows the write, and the
      stale failure report is gone.
- [ ] A partial batch — some parameters written, others rejected — reports
      **Partly applied** and **Drive partly updated**, never "not
      updated": the technician must not be told nothing changed when
      something did.

## 5. Reject

- [ ] Trigger another proposal and press **Reject**.
- [ ] The card reads **Rejected - nothing was changed**, no report
      appears, and a platform notice records the rejection so the agent
      knows on its next turn.

## 6. `.ptb` download

- [ ] Upload a `.ptb` in the sidebar (generate one with
      `build_xml()` from `tests/test_ptb_modifier.py` if you have no real
      file).
- [ ] Approve a proposal. A **Configuration file updated** report appears
      alongside the drive report, plus a **Download modified .ptb**
      button.
- [ ] Parameters present in the file are applied; any that are absent are
      listed honestly and do **not** fail the drive write — the drive is
      the authority on the outcome.
- [ ] Download and confirm the value changed, e.g.:
      ```bash
      python -c "import gzip,re;x=gzip.decompress(open('DOWNLOAD.ptb','rb').read()).decode();i=x.find('<paramNum>8</paramNum>');print(re.search(r'<currentValue>(\d+)</currentValue>',x[i:i+400]).group(1))"
      ```
      `48` means P-08 = 4.8 A (scale 10).

## 7. Honesty

- [ ] Ask something the knowledge base does not cover, e.g. *"How do I
      service the cooling fan bearings on this drive?"*
- [ ] The agent says plainly that the E3 knowledge base does not contain
      the procedure and refers you to Invertek technical support. It does
      not dress up an adjacent document as an answer.
- [ ] Ask something wholly unrelated (*"recipe for chocolate cake"*):
      search returns `found: 0` and the agent declines.

## 8. Real hardware (when a drive is available)

Not covered by the simulator; verify manually once:

- [ ] Sidebar → **Serial (USB-RS485)**, pick the adapter's port, baud
      115200, address 1 (P-36 index 1), **Connect**.
- [ ] Status and the active trip code match the drive keypad.
- [ ] A parameter write lands and reads back: check the keypad shows the
      new value. `P-15` must map to register 143 (`128 + 15`, guide
      §8.4 p.33) — an off-by-one here is the classic zero-based
      addressing mistake.
- [ ] Trip history shows the active trip plus trips observed during the
      session; the full last-four log is keypad-only (`P00-13`), as the
      guide documents no register for it.
- [ ] Confirm the `.ptb` registry's addressing and scale factors against
      a file saved from the real drive — these are still unconfirmed
      against real hardware.
