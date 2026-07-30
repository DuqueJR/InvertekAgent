import json
import tempfile
from pathlib import Path

import streamlit as st
from openai import OpenAI
try:
    from anthropic import Anthropic
except Exception:
    Anthropic = None

from config import DEEPSEEK_API_KEY, MODEL
from drive import apply_change_set
from tools import (
    DRIVE_TOOLS,
    TOOL_DEFINITIONS,
    TOOL_MAP,
    modify_ptb_configuration,
)

# Simple Anthropic example (optional). Fill .env with DEEPSEEK_API_KEY and ANTHROPIC_BASE_URL
# You can copy-paste this to run a quick test.
#
# from dotenv import load_dotenv
# load_dotenv()
# client = Anthropic(
#     api_key=os.getenv("DEEPSEEK_API_KEY"),
#     base_url=os.getenv("ANTHROPIC_BASE_URL"),
# )
# message = client.messages.create(
#     model="deepseek-v4-pro",
#     max_tokens=1024,
#     messages=[{"role": "user", "content": "Hola"}],
# )
# print(message.content[0].text)

# Minimal project layout to track small commits:
# my_agent_project/
# ├── .env
# ├── pyproject.toml
# ├── uv.lock
# ├── src/
# │   └── my_agent/
# │       ├── __init__.py
# │       ├── main.py      # the agent loop: call model, check for tool calls, execute, repeat
# │       ├── client.py    # OpenAI/Anthropic client setup
# │       ├── tools.py     # tool functions + their JSON schemas
# │       └── config.py
# └── tests/
#     └── test_tools.py

PAGE_TITLE = "Invertek Drives | Optidrive Technical Assistant"

st.set_page_config(
    page_title=PAGE_TITLE,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =============================================================================
# Invertek Drives brand palette — colours sampled from invertekdrives.com
# =============================================================================
PALETTE = {
    "purple": "#535483",
    "purple_300": "#7E7AAB",
    "purple_200": "#8782B4",
    "purple_hover": "#45466E",
    "link_blue": "#285FD1",
    "green": "#63BF4F",
    "green_alt": "#85B745",
    "ink": "#1A1A1A",
    "ink_muted": "#4B4B4B",
    "surface": "#FFFFFF",
    "surface_alt": "#F7F7F7",
    "surface_tile": "#F2F2F2",
    "panel_black": "#101010",
    "footer_black": "#000000",
    "line": "#E2E2EA",
    "on_purple": "#FFFFFF",
    "error": "#B42318",
}

# =============================================================================
# Global CSS – Invertek Drives look & feel (periwinkle purple, not navy/orange)
# =============================================================================
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Mulish:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400&display=swap');

    /* ---- RESET & BASE ---- */
    html, body, .stApp, [data-testid="stAppViewContainer"] {{
        background: {PALETTE['surface']};
        color: {PALETTE['ink']};
        font-family: 'Mulish', 'Museo Sans', 'Segoe UI', system-ui, Arial, sans-serif;
        font-size: 15px;
        line-height: 1.6;
        -webkit-font-smoothing: antialiased;
    }}

    /* Remove default Streamlit padding and chrome */
    .block-container {{
        padding-top: 1rem;
        max-width: 1280px;
    }}
    [data-testid="stHeader"] {{
        display: none !important;
    }}

    a {{
        color: {PALETTE['link_blue']};
        font-weight: 500;
        text-decoration: none;
    }}

    :focus-visible {{
        outline: 2px solid {PALETTE['purple_200']};
        outline-offset: 2px;
    }}

    /* ---- HEADER / TOP BAR ---- */
    .invertek-header {{
        background: linear-gradient(90deg, {PALETTE['purple']}, {PALETTE['purple_300']});
        color: {PALETTE['on_purple']};
        padding: 16px 28px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-radius: 2px;
    }}
    .invertek-header .brand {{
        display: flex;
        align-items: center;
        gap: 14px;
    }}
    .invertek-header .brand-icon {{
        width: 40px;
        height: 40px;
        background: {PALETTE['surface']};
        color: {PALETTE['purple']};
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 20px;
        border-radius: 2px;
    }}
    .invertek-header .brand-text h1 {{
        margin: 0 !important;
        padding: 0 !important;
        font-size: 18px;
        font-weight: 700;
        color: {PALETTE['on_purple']};
        line-height: 1.2;
    }}
    .invertek-header .brand-text span {{
        font-size: 12px;
        font-weight: 500;
        color: rgba(255, 255, 255, 0.78);
        display: block;
    }}
    .invertek-header .header-badge {{
        background: {PALETTE['surface']};
        color: {PALETTE['purple']};
        padding: 6px 16px;
        font-size: 12px;
        font-weight: 600;
        border-radius: 999px;
    }}

    /* ---- BADGE / TRUST MARK (pill chips) ---- */
    .trust-badge {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: {PALETTE['surface']};
        border: 1px solid {PALETTE['line']};
        color: {PALETTE['ink']};
        padding: 6px 16px 6px 12px;
        font-size: 12px;
        font-weight: 600;
        border-radius: 999px;
    }}
    .trust-badge .dot {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: {PALETTE['green']};
        flex-shrink: 0;
    }}
    .trust-badge.cta {{
        background: {PALETTE['purple']};
        border-color: {PALETTE['purple']};
        color: {PALETTE['on_purple']};
    }}
    .trust-badge.cta .dot {{
        background: {PALETTE['green']};
    }}

    /* ---- HIDE SIDEBAR ---- */
    [data-testid="stSidebar"] {{
        display: none !important;
    }}
    [data-testid="stSidebarCollapsedControl"] {{
        display: none !important;
    }}
    [data-testid="collapsedControl"] {{
        display: none !important;
    }}

    /* ---- CHAT BUBBLES ---- */
    .msg-user {{
        background: {PALETTE['surface_tile']};
        border: 1px solid {PALETTE['line']};
        border-radius: 2px;
        padding: 12px 16px;
        margin-bottom: 10px;
        color: {PALETTE['ink']};
        font-size: 14px;
        line-height: 1.6;
    }}
    .msg-user strong {{
        color: {PALETTE['ink_muted']};
        font-size: 12px;
        font-weight: 700;
        display: block;
        margin-bottom: 4px;
    }}
    .msg-agent {{
        background: {PALETTE['surface']};
        border: 1px solid {PALETTE['line']};
        border-left: 4px solid {PALETTE['purple']};
        border-radius: 2px;
        box-shadow: 0 1px 4px rgba(16, 16, 16, 0.10);
        padding: 12px 16px;
        margin-bottom: 10px;
        color: {PALETTE['ink']};
        font-size: 14px;
        line-height: 1.6;
    }}
    .msg-agent strong {{
        color: {PALETTE['purple']};
        font-size: 12px;
        font-weight: 700;
        display: block;
        margin-bottom: 4px;
    }}
    .msg-event {{
        background: {PALETTE['surface_alt']};
        border: 1px dashed {PALETTE['line']};
        border-radius: 2px;
        padding: 8px 16px;
        margin-bottom: 10px;
        color: {PALETTE['ink_muted']};
        font-size: 13px;
        line-height: 1.5;
    }}
    .proposal-status {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-size: 12px;
        font-weight: 700;
        padding: 4px 14px;
        border-radius: 999px;
        margin-bottom: 8px;
    }}
    .proposal-status.pending {{
        background: rgba(83, 84, 131, 0.10);
        color: {PALETTE['purple']};
    }}
    .proposal-status.applied {{
        background: rgba(99, 191, 79, 0.12);
        color: {PALETTE['green']};
    }}
    .proposal-status.rejected, .proposal-status.superseded {{
        background: {PALETTE['surface_tile']};
        color: {PALETTE['ink_muted']};
    }}
    .proposal-status.failed {{
        background: rgba(180, 35, 24, 0.08);
        color: {PALETTE['error']};
    }}

    /* ---- BUTTONS (rectangular, near-square corners) ---- */
    .stButton > button {{
        background: {PALETTE['purple']};
        color: {PALETTE['on_purple']};
        border: none;
        border-radius: 2px;
        padding: 10px 28px;
        font-family: 'Mulish', 'Museo Sans', 'Segoe UI', system-ui, Arial, sans-serif;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        transition: background 0.2s ease;
    }}
    .stButton > button:hover {{
        background: {PALETTE['purple_hover']};
        color: {PALETTE['on_purple']};
    }}
    .stButton > button:active {{
        background: {PALETTE['purple_hover']};
    }}

    /* ---- SECTION HEADERS (purple emphasis) ---- */
    .section-title {{
        font-family: 'Mulish', 'Museo Sans', 'Segoe UI', system-ui, Arial, sans-serif;
        font-size: 18px;
        font-weight: 700;
        color: {PALETTE['purple']};
        line-height: 1.2;
        padding-bottom: 6px;
        border-bottom: 2px solid {PALETTE['line']};
        display: inline-block;
        margin-bottom: 12px;
    }}

    /* ---- TABLES ---- */
    .stTable thead th {{
        background: {PALETTE['purple']};
        color: {PALETTE['on_purple']};
        font-weight: 700;
        font-size: 13px;
        padding: 8px 12px;
    }}
    .stTable tbody td {{
        font-size: 14px;
        padding: 8px 12px;
    }}

    /* ---- SELECT BOX LABELS (inline controls) ---- */
    .stSelectbox label, .stTextInput label {{
        font-family: 'Mulish', 'Museo Sans', 'Segoe UI', system-ui, Arial, sans-serif;
        font-size: 13px;
        font-weight: 600;
        color: {PALETTE['ink_muted']};
    }}

    /* ---- INPUTS ---- */
    .stTextInput > div > div > input {{
        border: 1px solid {PALETTE['line']};
        border-radius: 2px;
        background: {PALETTE['surface']};
        color: {PALETTE['ink']};
        font-size: 14px;
        padding: 8px 12px;
    }}
    .stTextInput > div > div > input:focus {{
        border-color: {PALETTE['purple']};
        box-shadow: 0 0 0 1px {PALETTE['purple']};
    }}

    /* ---- WARNINGS / ALERTS ---- */
    .stAlert {{
        font-size: 14px;
        font-weight: 500;
        border-radius: 2px;
    }}

    /* ---- EXPANDER ---- */
    .streamlit-expanderHeader {{
        font-weight: 600;
        color: {PALETTE['ink']};
        font-size: 13px;
    }}

    /* ---- FOOTER (black band) ---- */
    .invertek-footer {{
        background: {PALETTE['footer_black']};
        color: rgba(255, 255, 255, 0.72);
        border-radius: 2px;
        padding: 20px 28px;
        font-size: 12px;
        margin-top: 24px;
    }}
    .invertek-footer strong {{
        color: {PALETTE['on_purple']};
        font-weight: 600;
    }}

    /* ---- LOADER / SPINNER ---- */
    .stSpinner > div {{
        border-top-color: {PALETTE['purple']} !important;
    }}

    /* ---- FILE UPLOADER ---- */
    [data-testid="stFileUploaderDropzone"] {{
        background: {PALETTE['surface_alt']};
        border: 1px dashed {PALETTE['purple_200']};
        border-radius: 2px;
    }}
    [data-testid="stFileUploader"] label {{
        font-family: 'Mulish', 'Museo Sans', 'Segoe UI', system-ui, Arial, sans-serif;
        font-size: 13px;
        font-weight: 600;
        color: {PALETTE['ink_muted']};
    }}
    [data-testid="stFileUploaderDropzone"] button {{
        background: {PALETTE['surface']};
        color: {PALETTE['purple']};
        border: 1px solid {PALETTE['line']};
        border-radius: 999px;
        font-weight: 600;
    }}

    /* ---- DOWNLOAD BUTTON (matches primary button) ---- */
    .stDownloadButton > button {{
        background: {PALETTE['purple']};
        color: {PALETTE['on_purple']};
        border: none;
        border-radius: 2px;
        padding: 10px 28px;
        font-family: 'Mulish', 'Museo Sans', 'Segoe UI', system-ui, Arial, sans-serif;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        transition: background 0.2s ease;
    }}
    .stDownloadButton > button:hover {{
        background: {PALETTE['purple_hover']};
        color: {PALETTE['on_purple']};
    }}

    /* ---- PTB CHANGE REPORT ---- */
    .ptb-report {{
        background: {PALETTE['surface']};
        border: 1px solid {PALETTE['line']};
        border-radius: 2px;
        box-shadow: 0 1px 4px rgba(16, 16, 16, 0.10);
        padding: 12px 16px;
        margin-bottom: 10px;
        font-size: 14px;
    }}
    .ptb-report .ptb-status {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-size: 12px;
        font-weight: 700;
        padding: 4px 14px;
        border-radius: 999px;
        margin-bottom: 8px;
    }}
    .ptb-report .ptb-status.ok {{
        background: rgba(99, 191, 79, 0.12);
        color: {PALETTE['green']};
    }}
    .ptb-report .ptb-status.fail {{
        background: rgba(180, 35, 24, 0.08);
        color: {PALETTE['error']};
    }}
    .ptb-report table {{
        width: 100%;
        border-collapse: collapse;
        margin: 8px 0;
        font-size: 13px;
    }}
    .ptb-report th {{
        background: {PALETTE['purple']};
        color: {PALETTE['on_purple']};
        font-weight: 700;
        text-align: left;
        padding: 6px 10px;
    }}
    .ptb-report td {{
        border-bottom: 1px solid {PALETTE['line']};
        padding: 6px 10px;
        color: {PALETTE['ink']};
    }}
    .ptb-report .ptb-rejected-item {{
        border-left: 3px solid {PALETTE['error']};
        background: {PALETTE['surface_alt']};
        border-radius: 2px;
        padding: 8px 12px;
        margin: 6px 0;
        font-size: 13px;
    }}
    .ptb-report .ptb-warning {{
        color: {PALETTE['ink_muted']};
        font-size: 12px;
        margin-top: 6px;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# Constants
# =============================================================================
MODELS = [
    "Optidrive E3",
]

CATEGORIES = [
    "Fault Codes & Diagnostics",
    "Motor Parameters",
    "Control Wiring Diagrams",
    "General",
]

# Maximum model/tool round-trips per query before a plain-text
# answer is forced.
MAX_TOOL_ROUNDS = 6

SYSTEM_PROMPT = (
    "You are an expert technical support assistant for Invertek Drives "
    "Optidrive E3 variable frequency drives. You provide precise, "
    "technical answers backed by official documentation.\n\n"
    "CRITICAL RULES:\n"
    "1. You have access to a tool called `search_invertek_docs` that "
    "searches the official Invertek Optidrive E3 knowledge base.\n"
    "2. You MUST call this tool for EVERY technical question about "
    "fault codes, motor parameters, wiring, or installation.\n"
    "3. Base your answer EXCLUSIVELY on the tool's JSON response.\n"
    "4. If the tool returns no results (found: 0), state that the "
    "information is not available in the E3 knowledge base and "
    "recommend contacting Invertek support.\n"
    "5. Never invent fault codes, parameter values, or wiring "
    "instructions.\n"
    "6. Use professional, engineering-oriented language. "
    "No emojis, no casual tone.\n"
    "6b. Search with discipline: at most TWO searches per question, "
    "then act on the best information found. Never repeat a similar "
    "query hoping for better results.\n\n"
    "LIVE DRIVE (Modbus RTU):\n"
    "7. When the SESSION CONTEXT says a drive is connected, begin any "
    "diagnosis of drive behaviour by calling `read_drive_status` and "
    "`read_trip_history` — ground your reasoning in what the drive "
    "actually reports before searching the knowledge base.\n"
    "8. If no drive is connected, work from the knowledge base and any "
    "uploaded .ptb file; suggest connecting the drive only when live "
    "data would change your answer.\n\n"
    "PARAMETER CHANGES (propose, never apply):\n"
    "9. When your diagnosis calls for parameter changes, call "
    "`propose_parameter_changes` with the exact changes and a short "
    "rationale. The tool only validates: NOTHING is applied by it.\n"
    "10. The platform then shows the technician a preview card (exact "
    "current -> new values) with Approve and Reject buttons under your "
    "answer. Tell the technician to review and approve it there. NEVER "
    "claim a change was applied, a file was written, or a download is "
    "ready - approval has not happened yet when you answer.\n"
    "11. On approval the platform writes each parameter to the "
    "connected drive over Modbus, verifies each write by reading it "
    "back, and produces a modified .ptb download when a file is "
    "uploaded. The outcome arrives in the conversation as a platform "
    "notice; trust only that notice when later describing what was "
    "applied.\n"
    "12. If the tool rejects some changes, propose again in the same "
    "turn with only the valid ones and explain the rejected ones in "
    "your answer. Physical fixes (wiring, cooling, mechanical) are "
    "step-by-step instructions, not parameter proposals."
)

# =============================================================================
# Header – top bar
# =============================================================================
st.markdown(
    f"""
    <div class="invertek-header">
        <div class="brand">
            <div class="brand-icon">I</div>
            <div class="brand-text">
                <h1>Invertek Drives</h1>
                <span>Optidrive &mdash; variable frequency drives</span>
            </div>
        </div>
        <div class="header-badge">E3 diagnostics</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# Trust badges row
# =============================================================================
st.markdown(
    f"""
    <div style="padding:12px 28px; display:flex; gap:12px; flex-wrap:wrap;">
        <div class="trust-badge">
            <span class="dot"></span> Global support network
        </div>
        <div class="trust-badge">
            <span class="dot"></span> ISO 9001 certified
        </div>
        <div class="trust-badge cta">
            <span class="dot"></span> Optidrive E3
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write(
    "Consult fault codes, parameter settings and wiring diagrams for "
    "Invertek Optidrive E3 variable frequency drives. Upload a .ptb "
    "configuration file to propose and apply approved parameter changes."
)

# =============================================================================
# Chat history initialisation
# =============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

api_key = DEEPSEEK_API_KEY

# =============================================================================
# Control panel – inline model / category / firmware selectors
# =============================================================================
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    selected_model = st.selectbox(
        "VFD model",
        MODELS,
        label_visibility="visible",
    )
with col2:
    selected_category = st.selectbox(
        "Category",
        CATEGORIES,
        label_visibility="visible",
    )
with col3:
    firmware = st.text_input(
        "Firmware",
        value="",
        placeholder="e.g. v2.10",
        label_visibility="visible",
    )

# =============================================================================
# Drive configuration file (.ptb) upload
# =============================================================================
if "ptb_workdir" not in st.session_state:
    st.session_state.ptb_workdir = tempfile.mkdtemp(prefix="invertek_ptb_")

uploaded_ptb = st.file_uploader(
    "Drive configuration file (.ptb) — optional",
    type=["ptb"],
    help=(
        "Upload the drive's parameter file to let the assistant propose "
        "and, once you approve, apply parameter changes."
    ),
)

ptb_input_path = None
if uploaded_ptb is not None:
    workdir = Path(st.session_state.ptb_workdir)
    ptb_input_path = str(workdir / uploaded_ptb.name)
    with open(ptb_input_path, "wb") as fh:
        fh.write(uploaded_ptb.getbuffer())
    st.caption(
        f"{uploaded_ptb.name} loaded. Recommended changes are applied to a "
        "modified copy - review the change report and download it under "
        "the response."
    )

st.markdown("---")

# =============================================================================
# Main input area
# =============================================================================
user_input = st.text_input(
    "Enter your technical query",
    value="",
    key="user_input",
    placeholder="Describe the fault code, parameter, or wiring question...",
)

if not api_key:
    st.warning(
        "API key not configured. "
        "Set the DEEPSEEK_API_KEY environment variable."
    )

if st.button("Submit Query", key="send_button"):
    if not api_key:
        st.error(
            "API key not configured. "
            "Set the DEEPSEEK_API_KEY environment variable."
        )
    elif not user_input.strip():
        st.error("Enter a message before submitting.")
    else:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )

        st.session_state.messages.append(
            {"role": "user", "content": user_input}
        )

        context_lines = [
            f"Drive model: {selected_model}",
            f"Question category: {selected_category}",
        ]
        if firmware.strip():
            context_lines.append(f"Firmware: {firmware.strip()}")
        drive_client = st.session_state.get("drive_client")
        if drive_client is not None and drive_client.is_connected:
            context_lines.append(
                "Drive connection: connected "
                f"({st.session_state.get('drive_mode', 'simulator')})."
            )
        else:
            context_lines.append("Drive connection: no drive is connected.")
        if ptb_input_path:
            context_lines.append(
                "A .ptb configuration file is uploaded; approved parameter "
                "changes also produce a modified copy for download."
            )
        else:
            context_lines.append("No .ptb configuration file has been uploaded.")

        api_messages = [
            {
                "role": "system",
                "content": (
                    SYSTEM_PROMPT
                    + "\n\nSESSION CONTEXT:\n"
                    + "\n".join(context_lines)
                ),
            },
        ]
        # Platform events (approval outcomes) replay as user-side notices
        # so the model knows what was actually applied.
        api_messages.extend(
            {
                "role": "user" if m["role"] == "event" else m["role"],
                "content": (
                    f"[Platform notice] {m['content']}"
                    if m["role"] == "event" else m["content"]
                ),
            }
            for m in st.session_state.messages
        )

        try:
            tool_sources = []
            pending_proposal = None
            assistant_text = None

            # Iterative tool loop: the model may search, read the results,
            # search again and finally modify the .ptb — each round passes
            # the tools again until the model answers in plain text.
            with st.spinner("Analysing query..."):
                for _ in range(MAX_TOOL_ROUNDS):
                    response = client.chat.completions.create(
                        model=MODEL,
                        messages=api_messages,
                        max_tokens=3000,
                        temperature=0.2,
                        tools=TOOL_DEFINITIONS,
                    )
                    assistant_msg = response.choices[0].message
                    tool_calls = assistant_msg.tool_calls

                    if not tool_calls:
                        # An empty answer here means the token budget died
                        # mid-reasoning (finish_reason "length"); fall
                        # through to the forced final call instead.
                        assistant_text = (
                            (assistant_msg.content or "").strip() or None
                        )
                        break

                    api_messages.append(assistant_msg)
                    for tc in tool_calls:
                        func_name = tc.function.name
                        func_args = json.loads(tc.function.arguments)

                        # Drive tools always act on this session's own
                        # connection, regardless of what the model sent.
                        if func_name in DRIVE_TOOLS:
                            func_args["drive"] = drive_client

                        func = TOOL_MAP.get(func_name)
                        if func is None:
                            result = json.dumps(
                                {"error": f"Unknown tool: {func_name}"}
                            )
                        else:
                            result = func(**func_args)

                        api_messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result,
                        })

                        # Parse results for display
                        parsed = json.loads(result)
                        if func_name == "search_invertek_docs":
                            tool_sources.extend(parsed.get("documents", []))
                        elif func_name == "propose_parameter_changes":
                            if parsed.get("proposal_ok"):
                                pending_proposal = parsed["proposal"]

                if assistant_text is None:
                    # Tool budget exhausted: force a final plain-text answer.
                    response = client.chat.completions.create(
                        model=MODEL,
                        messages=api_messages,
                        max_tokens=3000,
                        temperature=0.2,
                    )
                    assistant_text = (
                        response.choices[0].message.content or ""
                    ).strip()

            if not assistant_text:
                assistant_text = (
                    "No response was generated. Please resubmit the query."
                )

            message = {
                "role": "assistant",
                "content": assistant_text,
                "sources": tool_sources,
            }
            if pending_proposal is not None:
                # Only one proposal can be pending at a time.
                for m in st.session_state.messages:
                    p = m.get("proposal")
                    if p and p["status"] == "pending":
                        p["status"] = "superseded"
                st.session_state.proposal_seq = (
                    st.session_state.get("proposal_seq", 0) + 1
                )
                message["proposal"] = {
                    "id": st.session_state.proposal_seq,
                    "status": "pending",
                    "changes": pending_proposal["changes"],
                    "rationale": pending_proposal.get("rationale", ""),
                }
            st.session_state.messages.append(message)

        except Exception as exc:
            st.error(f"API connection error: {exc}")

# =============================================================================
# Conversation history
# =============================================================================
def render_ptb_report(
    report: dict,
    key: str,
    file_bytes=None,
    ok_label="Configuration file updated",
    fail_label="No configuration file written",
) -> None:
    """Render a change report (drive or .ptb) as a branded card."""
    ok = bool(report.get("success"))
    status = (
        f'<span class="ptb-status ok">{ok_label}</span>'
        if ok
        else f'<span class="ptb-status fail">{fail_label}</span>'
    )
    drive_bits = " &middot; ".join(
        str(report[k])
        for k in ("drive_type", "drive_version")
        if report.get(k)
    )
    parts = [f'<div class="ptb-report">{status}']
    if drive_bits:
        parts.append(
            f'<span class="ptb-warning">Drive: {drive_bits}</span>'
        )

    applied = report.get("applied", [])
    if applied:
        rows = "".join(
            f"<tr><td>{ch.get('code', '')}</td>"
            f"<td>{ch.get('name', '')}</td>"
            f"<td>{ch.get('old_display', '')} &rarr; "
            f"<strong>{ch.get('new_display', '')}</strong>"
            f" {ch.get('units') or ''}</td>"
            f"<td>{ch.get('reason', '')}</td></tr>"
            for ch in applied
        )
        parts.append(
            "<table><thead><tr><th>Code</th><th>Parameter</th>"
            "<th>Change</th><th>Reason</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )

    for rej in report.get("rejected", []):
        code = rej.get("code") or "—"
        parts.append(
            f'<div class="ptb-rejected-item"><strong>{code}</strong> '
            f"{rej.get('message', '')}</div>"
        )

    for warning in report.get("warnings", []):
        parts.append(f'<div class="ptb-warning">{warning}</div>')

    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)

    out_path = report.get("output_path")
    data = file_bytes
    if data is None and out_path and Path(out_path).exists():
        data = Path(out_path).read_bytes()
    if ok and data:
        st.download_button(
            "Download modified .ptb",
            data=data,
            file_name=Path(out_path).name if out_path else "modified.ptb",
            mime="application/octet-stream",
            key=f"ptb_download_{key}",
        )


PROPOSAL_STATUS_LABELS = {
    "pending": "Awaiting your approval",
    "applied": "Applied and verified",
    "rejected": "Rejected - nothing was changed",
    "failed": "Apply failed - see details",
    "superseded": "Superseded by a newer proposal",
}


def _approve_proposal(message) -> None:
    """Platform-side apply: Modbus write + verify, then the .ptb copy.

    Runs inside the button-click rerun. Any exception marks the proposal
    failed so a re-render can never double-apply.
    """
    proposal = message["proposal"]
    changes = [
        {
            "code": c["code"],
            "new_value": c["new_value"],
            "reason": c.get("reason", ""),
        }
        for c in proposal["changes"]
    ]
    notice = []
    failed = False
    try:
        drive = st.session_state.get("drive_client")
        if drive is not None and drive.is_connected:
            report = apply_change_set(drive, changes)
            message["apply_report"] = report
            if report["success"]:
                applied = ", ".join(
                    f"{c['code']} {c['old_display']} -> {c['new_display']}"
                    f" {c['units'] or ''}".rstrip()
                    for c in report["applied"]
                )
                notice.append(
                    f"Written to the drive and verified by read-back: "
                    f"{applied}."
                )
            else:
                failed = True
                reasons = "; ".join(
                    f"{r.get('code') or '?'}: {r['message']}"
                    for r in report["rejected"]
                )
                notice.append(f"Drive write failed: {reasons}")
        else:
            notice.append(
                "No drive connected, so nothing was written over Modbus."
            )

        if ptb_input_path:
            st.session_state.ptb_seq = st.session_state.get("ptb_seq", 0) + 1
            out_path = str(
                Path(st.session_state.ptb_workdir)
                / (
                    f"{Path(ptb_input_path).stem}_modified_"
                    f"v{st.session_state.ptb_seq}.ptb"
                )
            )
            ptb_report = json.loads(modify_ptb_configuration(
                ptb_input_path=ptb_input_path,
                changes=changes,
                output_path=out_path,
            ))
            message["ptb_report"] = ptb_report
            if ptb_report.get("success"):
                try:
                    message["ptb_bytes"] = Path(
                        ptb_report["output_path"]
                    ).read_bytes()
                except OSError:
                    message["ptb_bytes"] = None
                notice.append(
                    "A modified .ptb copy is ready to download under the "
                    "proposal card."
                )
            else:
                failed = True
                reasons = "; ".join(
                    f"{r.get('code') or '?'}: {r['message']}"
                    for r in ptb_report.get("rejected", [])
                )
                notice.append(f".ptb modification failed: {reasons}")

        if len(notice) == 0 or (
            not failed
            and message.get("apply_report") is None
            and message.get("ptb_report") is None
        ):
            failed = True
            notice = [
                "Nothing to apply: connect a drive or upload a .ptb file, "
                "then approve again."
            ]
    except Exception as exc:
        failed = True
        notice.append(f"Apply aborted by an unexpected error: {exc}")

    proposal["status"] = "failed" if failed else "applied"
    st.session_state.messages.append({
        "role": "event",
        "content": (
            f"Proposal {'could not be applied' if failed else 'approved'}. "
            + " ".join(notice)
        ),
    })


def render_proposal_card(message, key: str) -> None:
    proposal = message["proposal"]
    status = proposal["status"]
    label = PROPOSAL_STATUS_LABELS.get(status, status)
    parts = [
        '<div class="ptb-report">',
        f'<span class="proposal-status {status}">Proposed parameter '
        f"changes &middot; {label}</span>",
    ]
    if proposal.get("rationale"):
        parts.append(
            f'<div class="ptb-warning">{proposal["rationale"]}</div>'
        )
    rows = "".join(
        f"<tr><td>{c['code']}</td>"
        f"<td>{c['name']}</td>"
        f"<td>{'&mdash;' if c.get('current_display') is None else c['current_display']}"
        f" &rarr; <strong>{c['new_display']}</strong>"
        f" {c.get('units') or ''}</td>"
        f"<td>{c.get('reason', '')}</td></tr>"
        for c in proposal["changes"]
    )
    parts.append(
        "<table><thead><tr><th>Code</th><th>Parameter</th>"
        "<th>Current &rarr; new</th><th>Reason</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)

    if status == "pending":
        pid = proposal["id"]
        col_approve, col_reject, _ = st.columns([1, 1, 3])
        if col_approve.button("Approve and apply", key=f"approve_{pid}"):
            _approve_proposal(message)
            st.rerun()
        if col_reject.button("Reject", key=f"reject_{pid}"):
            proposal["status"] = "rejected"
            st.session_state.messages.append({
                "role": "event",
                "content": (
                    "Proposal rejected by the technician. Nothing was "
                    "changed."
                ),
            })
            st.rerun()

    apply_report = message.get("apply_report")
    if apply_report is not None:
        render_ptb_report(
            apply_report,
            key=f"drive_{key}",
            ok_label="Drive updated - every write verified by read-back",
            fail_label="Drive not updated",
        )


st.markdown("---")
st.markdown(
    '<div class="section-title">Conversation log</div>',
    unsafe_allow_html=True,
)

for idx, message in enumerate(st.session_state.messages):
    if message["role"] == "user":
        st.markdown(
            f"<div class='msg-user'>"
            f"<strong>Engineer query</strong> {message['content']}"
            f"</div>",
            unsafe_allow_html=True,
        )
    elif message["role"] == "event":
        st.markdown(
            f"<div class='msg-event'>{message['content']}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='msg-agent'>"
            f"<strong>Technical response</strong> {message['content']}"
            f"</div>",
            unsafe_allow_html=True,
        )
        if message.get("proposal"):
            render_proposal_card(message, key=str(idx))
        report = message.get("ptb_report")
        if report:
            render_ptb_report(
                report, key=str(idx), file_bytes=message.get("ptb_bytes")
            )
        sources = message.get("sources", [])
        if sources:
            with st.expander("Reference documents"):
                for src in sources:
                    st.markdown(
                        f"**{src['id']} &mdash; {src['title']}**  "
                        f"_(relevance: {src.get('relevance', src.get('score', 'N/A'))})_"
                    )
                    st.caption(src["content"])

# =============================================================================
# Footer
# =============================================================================
st.markdown(
    f"""
    <div class="invertek-footer">
        <strong>Invertek Drives</strong> &mdash; A world leader in
        variable frequency drive technology.
        &nbsp;&middot;&nbsp;
        Optidrive E3 Technical Support Tool
        &nbsp;&middot;&nbsp;
        &copy; {__import__('datetime').datetime.now().year} Invertek Drives
    </div>
    """,
    unsafe_allow_html=True,
)
