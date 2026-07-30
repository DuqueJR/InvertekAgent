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

### Sprint scope -- Knowledge panel (implemented)

This sprint delivers the **Knowledge panel**: a Streamlit-based conversational agent that answers technical questions about the Optidrive E3 using **only** official documentation. Zero hallucinations by design -- every answer is sourced from real files on disk.

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
│   ├── client.py                     # Streamlit UI, agent loop, LLM orchestration
│   ├── tools/
│   │   ├── __init__.py               # Aggregates all tool defs and function maps
│   │   └── search_invertek_docs.py   # Keyword search across the data/ folder
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
├── .gitignore
└── README.md
```

**25 data files** (21 markdown documents + fault codes, parameters, manifest and review notes) covering the complete Optidrive E3 IP20 User Guide V1.05 plus IP66 variant supplements.

---

## How grounding works (anti-hallucination)

Every technical answer is guaranteed to be sourced from real documentation:

1. **LLM calls `search_invertek_docs` as a tool** -- the system prompt requires it before answering any technical question (`client.py:348-364`).

2. **The tool reads ONLY from `data/`** -- no external API, no vector DB, no model-generated content. Every result comes from files on disk (`tools/search_invertek_docs.py:4`).

3. **Keyword scoring** across frontmatter (title, topic, keywords) and body text ensures relevant documents surface even with partial queries.

4. **Structured JSON parsing** -- `fault_codes.json` (entries with `code`, `name`, `description`, `possible_causes`, `diagnostic_steps`, `reset_notes`) and `parameters.json` (entries with `id`, `name`, `function`, `range`, `default`, `source`) are searched field-by-field, returning precise entries instead of whole-file dumps.

5. **No-results guard** -- if no document matches, the tool returns an explicit `"found": 0` message telling the LLM to direct the user to Invertek support (`tools/search_invertek_docs.py:185-193`).

6. **System prompt explicitly forbids invention** -- rules 3-5 mandate answering exclusively from tool results and never inventing codes, values, or instructions.

### Verification

Tested 13 queries across fault codes, parameters, wiring, installation, and Modbus categories -- **all returned real documents** with 0 blank responses.

| Query | Category | Results |
|---|---|---|
| `O-I fault` | Fault code | 5 |
| `P-08 motor current` | Parameter | 5 |
| `2-wire start stop` | Wiring | 5 |
| `single phase derating` | Installation | 5 |
| `modbus register 2001` | Modbus | 4 |
| `brake resistor overload` | Fault | 5 |
| `EMC filter` | Installation | 5 |
| `U-Volt dc bus` | Fault | 5 |
| `O-temp over temperature` | Fault | 5 |
| `mechanical installation IP20` | Installation | 5 |
| `control terminals wiring` | Wiring | 5 |
| `P-Loss input phase` | Fault | 5 |
| `autotune P-03` | Parameter | 5 |

---

## Setup

### 1. Install dependencies

```bash
pip install streamlit openai python-dotenv
```

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

Top 5 results by relevance score. Score weights: 60% body text, 40% frontmatter metadata.

### `tools/__init__.py`
Package aggregator. Imports each tool module and exports `TOOL_DEFINITIONS` (list of OpenAI function schemas) and `TOOL_MAP` (name -> function). To add a new tool, create a `tools/my_tool.py`, import it here, done.

### `client.py`
Streamlit app with Invertek industrial branding (navy + orange palette). Agent loop:
1. User submits query
2. First LLM call with `TOOL_DEFINITIONS` -- LLM decides whether to invoke the search tool
3. If tool called: execute `search_invertek_docs`, feed results back as tool message
4. Second LLM call: formulates final answer grounded on tool results
5. Display answer with expandable reference documents showing source IDs and relevance

---

## Roadmap -- Issues & Analysis panels

### Issues panel (next sprint)
The core troubleshooting experience. Converts a technical fault report into a complete resolution pipeline:

- **Report intake**: fault codes, warnings, current parameters, motor nameplate data, scope recordings, logs, application context
- **AI Troubleshooting Agent**: interprets the problem, classifies as physical vs. parameter issue, analyzes configuration against motor/application data, produces a diagnosis with root cause and confidence level
- **Classification logic**:
  - **Physical/hardware issue**: recommends inspection steps, does NOT attempt to fix via parameters
  - **Parameter/configuration issue**: identifies exact parameters to change, with current value, proposed value, reason, and expected effect
- **Human-in-the-loop approval**: the agent never directly modifies the drive. It generates a proposed configuration table with `[APPROVE]` / `[REJECT]` controls
- **`.ptb` generation**: after approval, exports an OptiTools Studio-compatible parameter file containing only the approved changes, preserving original configuration for unmodified parameters
- **Post-solution feedback**: collects resolution status, new faults, actual parameters used, technician observations -- feeding the Analysis panel

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
