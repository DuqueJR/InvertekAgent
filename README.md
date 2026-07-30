# Agent Sprint Hackathon by **ReshapeX**
## InvertekAgent
Built by **aigents** (Medellin, July 25, 2026).

---

## AI Drive Troubleshooting Platform

An AI-powered platform for **commissioning, diagnostics, and troubleshooting of Invertek Optidrive E3** variable frequency drives. Designed to assist field technicians and engineers with fault diagnosis, configuration analysis, and technical knowledge retrieval.

### Platform panels (vision)

The complete platform has three panels:

| Panel | Purpose | Flow |
|---|---|---|
| **Issues** | Active problem resolution via an AI Troubleshooting Agent | Report → Diagnosis → Root Cause → Recommendation → Approval → `.ptb` generation → Physical test → Feedback |
| **Analysis** | Historical intelligence on resolved issues | Issues history → Metrics → Patterns → Trends → Success rates |
| **Knowledge** | Conversational technical assistant backed by official documentation | User question → Knowledge Base → LLM → Grounded technical answer |

### Sprint scope -- implemented

The build now covers the field-technician loop end to end: the technician
connects a laptop to the drive, the app reads live status and trip history
over **Modbus RTU**, the agent diagnoses from official documentation with a
citation on every claim, and parameter fixes are **proposed** for the
technician to **approve with a button** before anything is written. On
approval the platform writes each parameter over Modbus, verifies it by
reading it back, and produces a modified `.ptb` for download.

| Capability | Where |
|---|---|
| Live drive status, trip history, parameter reads | `agent/drive/`, sidebar panel |
| Software drive simulator (no hardware needed) | `agent/drive/simulator.py` |
| Grounded answers with document + section + page | `agent/tools/search_invertek_docs.py` |
| Propose → technician approves → write + read-back verify | `propose_parameter_changes`, `agent/drive/apply.py` |
| Safety gate (drive must be stopped) | `agent/drive/apply.py` |
| `.ptb` parameter profile generation | `agent/tools/ptb/` |

Scope is deliberately tight: Optidrive E3 only, one drive at a time, one
technician per session, cloud reasoning, simplicity above all.

Zero hallucinations by design -- every answer is sourced from real files on
disk, and questions the knowledge base does not cover are declined rather
than answered from an adjacent document. See
[`docs/e2e-checklist.md`](docs/e2e-checklist.md) to verify all of this in
about five minutes without a drive.

```
                           ┌──────────────────────┐
                           │  TECHNICIAN/ENGINEER  │
                           └──────────┬───────────┘
                                      │
           ┌──────────────────────────┼──────────────────────────┐
           │                          │                          │
           ▼                          ▼                          ▼
       ISSUES                    ANALYSIS                   KNOWLEDGE
   (next sprints)           (next sprints)              (this sprint)

   AI Troubleshooting       Metrics / Trends           LLM + Knowledge Base
        Agent                 / Patterns                   (RAG-like)
           │                                                │
    ┌──────┼──────┐                                  ┌──────┴──────┐
    ▼      ▼      ▼                                  ▼             ▼
  Report Params  Scope                         LLM (DeepSeek)    data/
    │      │      │                                  │        (23 files)
    └──────┼──────┘                                  ▼
           ▼                                    Grounded Answer
      Diagnosis                                 + Source Citations
           │
           ▼
   Physical or Parameter
        Issue
           │
    ┌──────┴──────┐
    ▼             ▼
  Physical    Parameter
  Solution     Solution
                 │
                 ▼
          Human Approval
                 │
                 ▼
           Generate .ptb
                 │
                 ▼
            OptiTools
                 │
                 ▼
               Drive
                 │
                 ▼
             Feedback
```

---

## Core philosophy

> The AI should not simply tell the engineer what a fault means. It should investigate the problem, reason about the available evidence, distinguish physical issues from configuration issues, recommend corrective actions, and produce an actionable configuration proposal that a human can review and approve.

The system behaves as an **AI Engineering Troubleshooting Agent** rather than a conventional chatbot:

```
Understand → Investigate → Interpret → Diagnose → Recommend
    → Ask for approval → Generate configuration
    → Human applies → Test → Collect feedback → Learn from history
```

The **Issues panel is the heart of the product**. Knowledge and Analysis provide technical intelligence and historical insight around it.

---

## Project structure

```
InvertekAgent/
├── .env                              # API key (DEEPSEEK_API_KEY)
├── agent/
│   ├── config.py                     # Env loading, API key + model constants
│   ├── client.py                     # Streamlit app: state, agent loop, approval flow
│   ├── ui.py                         # Palette, CSS and render helpers
│   ├── drive/                        # Live drive over Modbus RTU
│   │   ├── registers.py              # E3 register map (User Guide S8.4)
│   │   ├── base.py                   # DriveClient interface, status/trip types
│   │   ├── simulator.py              # In-memory E3 stand-in for demos
│   │   ├── serial_client.py          # Real drive via USB-RS485 (minimalmodbus)
│   │   └── apply.py                  # Approved writes: safety gate + read-back verify
│   ├── tools/
│   │   ├── __init__.py               # Aggregates all tool defs and function maps
│   │   ├── search_invertek_docs.py   # Keyword search across the data/ folder
│   │   ├── drive_tools.py            # Status, trips, parameter reads, proposals
│   │   └── ptb/                      # .ptb reading and modification + registry
│   └── data/                         # Official documentation (ground truth)
│       ├── fault_codes.json          # 31 fault codes (JSON structured)
│       ├── parameters.json           # 64 settable + 50 read-only parameters (JSON structured)
│       ├── manifest.json             # KB build manifest (excluded from search)
│       ├── REVIEW_NOTES.md           # Curator verification notes (excluded from search)
│       ├── procedures/               # Step-by-step procedures (10 documents)
│       │   ├── commissioning-basic.md
│       │   ├── keypad-operation.md
│       │   ├── parameter-and-fault-reset.md
│       │   ├── modbus-rtu-setup.md
│       │   ├── motor-thermistor-connection.md
│       │   ├── brake-resistor-installation.md
│       │   ├── emc-filter-disconnect.md
│       │   ├── fire-mode.md
│       │   ├── single-phase-operation.md
│       │   └── storage-capacitor-reforming.md
│       └── reference/                # Reference material (11 documents)
│           ├── product-overview.md
│           ├── model-numbers.md
│           ├── control-terminals.md
│           ├── power-wiring.md
│           ├── mechanical-installation.md
│           ├── modbus-register-map.md
│           ├── macro-configurations.md
│           ├── rating-tables.md
│           ├── environmental-and-ul.md
│           ├── emc-compliant-installation.md
│           └── safety-information.md
├── docs/e2e-checklist.md             # Pre-demo verification walkthrough
├── scripts/generate_e3_registry.py   # Rebuilds the .ptb registry from the KB
├── tests/                            # 69 tests, no hardware required
├── .gitignore
└── README.md
```

**25 data files** (21 markdown documents + fault codes, parameters, manifest and review notes) covering the complete Optidrive E3 IP20 User Guide V1.05 plus IP66 variant supplements.

---

## How grounding works (anti-hallucination)

Every technical answer is guaranteed to be sourced from real documentation:

1. **LLM calls `search_invertek_docs` as a tool** -- the system prompt requires it before answering any technical question (`client.py:348-364`).

2. **The tool reads ONLY from `data/`** -- no external API, no vector DB, no model-generated content. Every result comes from files on disk (`tools/search_invertek_docs.py:4`).

3. **Relevance you can trust** -- a document's score is the share of the query's *informative* terms it matches: stopwords are dropped, matching is whole-word (so "is" does not count inside "resistance"), and terms are weighted by inverse document frequency so a question sharing only "drive" or "invertek" with the corpus scores near zero. Frontmatter (title, topic, keywords) boosts; the body carries the signal.

3b. **Citations on every result** -- each hit returns a `source` naming the document, section and printed page, which the prompt requires the agent to quote. The UI renders them as chips so a weak citation is visible rather than implied.

4. **Structured JSON parsing** -- `fault_codes.json` (entries with `code`, `name`, `description`, `possible_causes`, `diagnostic_steps`, `reset_notes`) and `parameters.json` (entries with `id`, `name`, `function`, `range`, `default`, `source`) are searched field-by-field, returning precise entries instead of whole-file dumps.

5. **No-results guard** -- matches below `MIN_RELEVANCE` are discarded rather than dressed up as citations, so an uncovered question reaches the explicit `"found": 0` message that tells the agent to direct the technician to Invertek support. The prompt additionally requires the agent to decline when the documents returned do not actually answer the question: a weak match is not an answer.

6. **The model cannot apply anything** -- `modify_ptb_configuration` is deliberately not in the model-visible tool set. The agent can only *propose*; the platform performs the write after the technician presses Approve, then reports back what actually happened as a platform notice the agent must trust over its own expectations.

7. **System prompt explicitly forbids invention** -- rules 3-5 mandate answering exclusively from tool results and never inventing codes, values, or instructions.

### Verification

```bash
.venv/bin/python -m pytest tests/     # 69 tests, no drive hardware needed
```

`tests/test_search_docs.py` pins both grounding properties: every result
for a covered question carries a document/section/page citation, and
out-of-scope questions (fan bearings, pricing, EtherCAT, chocolate cake)
return `found: 0`. Eight representative covered questions -- O-I, U-Volt,
ramp times, factory reset, single-phase operation, thermistor wiring, EMC
installation, maximum frequency -- are asserted to keep retrieving.

`tests/test_drive_simulator.py` and `tests/test_drive_tools.py` cover the
drive layer: the safety gate, read-back verification, batch abort on a
failed write, proposal validation, and `P-15 -> register 143` from the
guide's own worked example.

For the manual walkthrough (simulator, approval, download, refusal) see
[`docs/e2e-checklist.md`](docs/e2e-checklist.md).

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

`openai`, `python-dotenv`, `streamlit`, `lxml`, `minimalmodbus` (Modbus RTU
over the USB-RS485 adapter, pulls in `pyserial`) and `pytest`.

### 2. Configure API key

Edit `.env` in the `InvertekAgent/` root:

```
DEEPSEEK_API_KEY="sk-your-key-here"
```

The key flows through `config.py` -> `client.py` automatically. No other file touches `.env` directly.

### 3. Run

```bash
cd InvertekAgent/agent
streamlit run client.py
```

Uses DeepSeek V4 Pro as the LLM backend (`config.py:12`). Swap `MODEL` in `config.py` to change providers.

---

## Components

### `config.py`
Loads `.env` via `python-dotenv`, exposes `DEEPSEEK_API_KEY`, `ANTHROPIC_BASE_URL`, and `MODEL`. Single source of truth for all credentials and model config.

### `tools/search_invertek_docs.py`
The search engine that grounds the Knowledge panel. Accepts `query` (required) and `category` (optional). Searches:
- **JSON files**: iterates `faults[]` and `parameters[]` arrays, scores each entry individually, returns structured snippets with code/name/causes/steps
- **Markdown files**: parses YAML frontmatter (`title`, `topic`, `keywords`), scores against frontmatter + body, returns the most relevant text section

Top 5 results above `MIN_RELEVANCE`. Relevance is the share of the query's
IDF-weighted terms a document matches (whole-word, stopwords removed);
frontmatter adds a boost rather than half the score. Every result carries a
`source` for citation.

### `tools/drive_tools.py`
The agent's only access to the drive, and none of it writes:
`read_drive_status`, `read_trip_history`, `read_parameters` (live over
Modbus, falling back to the uploaded `.ptb`) and
`propose_parameter_changes`, which validates a change set against the
registry and hands it to the platform for the technician to approve.

### `drive/`
`DriveClient` has two implementations behind one interface:
`SimulatedDriveClient` (in-memory E3, seeded to a tripped O-I scenario with
a four-entry trip log) and `SerialDriveClient` (real drive over USB-RS485,
8N1, 115200 baud, zero-based register addressing). `apply.py` performs
approved writes: it refuses unless the drive is connected *and stopped*,
writes each parameter, reads it back to confirm, and aborts the batch on the
first failure.

Documented limitations: the guide defines no Modbus register for the
last-four trip log (`P00-13` is keypad-only), so on real hardware the log
shows the active trip plus trips observed during the session; and the
parameter register formula `128 + n` covers `P-04..P-60` only, so P-01..P-03
are `.ptb`-only over Modbus.

### `tools/__init__.py`
Package aggregator. Imports each tool module and exports `TOOL_DEFINITIONS` (list of OpenAI function schemas) and `TOOL_MAP` (name -> function). To add a new tool, create a `tools/my_tool.py`, import it here, done.

### `client.py` and `ui.py`
Streamlit app in Invertek brand colours (periwinkle purple `#535483`, link
blue `#285FD1`, green accent `#63BF4F`, Mulish, 2px corners). `ui.py` owns
the palette, CSS and render helpers; `client.py` owns state and the agent
loop:

1. Technician submits a query; the sidebar's drive connection and uploaded
   `.ptb` are injected into the system prompt as session context.
2. Iterative tool loop (up to `MAX_TOOL_ROUNDS`): every round passes
   `TOOL_DEFINITIONS`, executes whatever the model calls -- status, trips,
   parameter reads, searches, a proposal -- and feeds results back, until
   the model answers in plain text.
3. A validated proposal is attached to the assistant message and rendered
   as a preview card with **Approve and apply** / **Reject**.
4. Approval runs platform-side: Modbus write with read-back verification,
   then the `.ptb` copy, then a platform notice appended to the
   conversation so the agent knows what actually happened.
5. The answer displays with citation chips and an expandable reference-
   documents list.

---

## Roadmap

### Issues panel -- largely delivered

What the original plan called the Issues panel now runs in this build:

- **Report intake** -- live fault code, drive state and trip history read
  from the drive; current parameter values read on demand; the technician
  describes the symptom in the chat.
- **AI Troubleshooting Agent** -- interprets the problem and separates
  physical from parameter causes, citing the document, section and page
  behind each claim.
- **Classification** -- physical faults get numbered inspection steps and no
  parameter changes; configuration faults get an exact change set with
  current value, proposed value and reason.
- **Human-in-the-loop approval** -- the agent cannot write. It proposes; the
  platform renders **Approve and apply** / **Reject** and only acts on the
  technician's click.
- **Application and verification** -- each approved parameter is written
  over Modbus and read back to confirm the drive took it, behind a safety
  gate that refuses while the drive is running.
- **`.ptb` generation** -- a modified copy of the uploaded configuration,
  containing only the approved changes, offered as a download.

Still outstanding: post-solution feedback capture (resolution status, new
faults, technician observations) to feed the Analysis panel, and
verification of the `.ptb` registry's addressing and scale factors against
a file saved from a real drive.

### Analysis panel (future)
Aggregates historical issue data for operational intelligence:
- Fault type frequency and distribution
- Physical vs. parameter issue ratio
- Most frequently modified parameters
- Resolution success rates
- Drives with recurring problems
- Recommendations with highest success rate
- Technician feedback aggregation

This data eventually feeds back into the AI agent to improve future recommendations.

---

## Adding a new tool

1. Create `agent/tools/my_tool.py`:

```python
def my_tool(param: str) -> str:
    ...

MY_TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "my_tool",
        "description": "...",
        "parameters": {
            "type": "object",
            "properties": {
                "param": {"type": "string", "description": "..."}
            },
            "required": ["param"],
        },
    },
}
```

2. Register in `agent/tools/__init__.py`:

```python
from .my_tool import MY_TOOL_DEF, my_tool

TOOL_DEFINITIONS = [SEARCH_TOOL_DEF, MY_TOOL_DEF]
TOOL_MAP = {
    "search_invertek_docs": search_invertek_docs,
    "my_tool": my_tool,
}
```

The LLM will automatically see the new tool in the next call -- no changes to `client.py` needed.

---

## Adding more documentation

Drop `.md` or `.json` files into `agent/data/`. They'll be indexed automatically on the next search.

**Markdown format** (recommended):

```markdown
---
title: Document Title
drive_model: Optidrive E3
topic: your-topic
keywords: [keyword1, keyword2, keyword3]
source: "User Guide Section X.Y, page Z"
---

## Content here...
```

**JSON format** for structured data (fault codes, parameters):

```json
{
  "faults": [
    {
      "code": "O-I",
      "display_number": "03",
      "name": "Output Over Current",
      "category": "overcurrent",
      "description": "...",
      "possible_causes": ["..."],
      "diagnostic_steps": ["..."],
      "reset_notes": "..."
    }
  ]
}
```

---

## Notes

- The old `rag_engine` dependency has been removed -- all search runs locally against files on disk with no external vector DB.
- `config.py` is the only module that reads `.env`. Every other module imports keys from `config.py`.
- `manifest.json` (KB build manifest) and `REVIEW_NOTES.md` (curator notes) in `data/` are metadata, not drive documentation, and are skipped by the search engine's `SKIP_FILES` set.
- The architecture is designed for the full three-panel platform: `tools/` package can grow with diagnostic, `.ptb` generation, and analytics tools without touching `client.py`.
