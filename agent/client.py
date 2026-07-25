import json

import streamlit as st
from openai import OpenAI
try:
    from anthropic import Anthropic
except Exception:
    Anthropic = None

from config import DEEPSEEK_API_KEY
from tools import TOOL_DEFINITIONS, TOOL_MAP

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

PAGE_TITLE = "INVERTEK DRIVES | OPTIDRIVE TECHNICAL ASSISTANT"

st.set_page_config(
    page_title=PAGE_TITLE,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =============================================================================
# Invertek Drives brand palette
# =============================================================================
PALETTE = {
    "navy": "#0A1E3D",
    "navy_light": "#0F2A52",
    "navy_dark": "#061228",
    "orange": "#E05500",
    "orange_hover": "#C44900",
    "white": "#FFFFFF",
    "off_white": "#F4F5F6",
    "light_gray": "#EAECEE",
    "mid_gray": "#9BA4B0",
    "dark_text": "#1A1D21",
    "body_text": "#2C3035",
    "muted": "#64748B",
    "border": "#D5DAE0",
    "success": "#1A7A3C",
    "error": "#C0392B",
}

# =============================================================================
# Global CSS – Invertek Drives industrial look & feel
# =============================================================================
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap');

    /* ---- RESET & BASE ---- */
    html, body, .stApp, [data-testid="stAppViewContainer"] {{
        background: {PALETTE['off_white']};
        color: {PALETTE['body_text']};
        font-family: 'Inter', Helvetica, Arial, sans-serif;
        font-size: 14px;
        -webkit-font-smoothing: antialiased;
    }}

    /* Remove default Streamlit padding */
    .block-container {{
        padding-top: 1rem;
    }}

    /* ---- HEADER / TOP BAR ---- */
    .invertek-header {{
        background: {PALETTE['navy']};
        padding: 16px 28px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 3px solid {PALETTE['orange']};
    }}
    .invertek-header .brand {{
        display: flex;
        align-items: center;
        gap: 14px;
    }}
    .invertek-header .brand-icon {{
        width: 40px;
        height: 40px;
        background: {PALETTE['orange']};
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 18px;
        color: #FFF;
        letter-spacing: -1px;
    }}
    .invertek-header .brand-text h1 {{
        margin: 0;
        font-size: 15px;
        font-weight: 700;
        letter-spacing: 1.2px;
        color: #FFFFFF;
        text-transform: uppercase;
        line-height: 1.2;
    }}
    .invertek-header .brand-text span {{
        font-size: 10px;
        font-weight: 500;
        letter-spacing: 2px;
        color: {PALETTE['mid_gray']};
        display: block;
    }}
    .invertek-header .header-badge {{
        background: {PALETTE['orange']};
        color: #FFF;
        padding: 5px 14px;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.8px;
        text-transform: uppercase;
    }}

    /* ---- BADGE / TRUST MARK ---- */
    .trust-badge {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: {PALETTE['navy']};
        color: #FFF;
        padding: 6px 16px 6px 12px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }}
    .trust-badge .dot {{
        width: 8px;
        height: 8px;
        background: {PALETTE['orange']};
        flex-shrink: 0;
    }}
    .trust-badge.outline {{
        background: transparent;
        border: 1px solid {PALETTE['navy']};
        color: {PALETTE['navy']};
    }}
    .trust-badge.outline .dot {{
        background: {PALETTE['orange']};
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
        background: {PALETTE['white']};
        border: 1px solid {PALETTE['border']};
        padding: 12px 16px;
        margin-bottom: 10px;
        color: {PALETTE['dark_text']};
        font-size: 13px;
        line-height: 1.5;
    }}
    .msg-user strong {{
        color: {PALETTE['navy']};
        font-size: 11px;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        display: block;
        margin-bottom: 4px;
    }}
    .msg-agent {{
        background: {PALETTE['white']};
        border-left: 4px solid {PALETTE['orange']};
        padding: 12px 16px;
        margin-bottom: 10px;
        color: {PALETTE['dark_text']};
        font-size: 13px;
        line-height: 1.5;
    }}
    .msg-agent strong {{
        color: {PALETTE['orange']};
        font-size: 11px;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        display: block;
        margin-bottom: 4px;
    }}

    /* ---- BUTTONS (industrial style) ---- */
    .stButton > button {{
        background: {PALETTE['orange']};
        color: #FFFFFF;
        border: none;
        padding: 8px 28px;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        cursor: pointer;
        transition: background 0.2s ease;
    }}
    .stButton > button:hover {{
        background: {PALETTE['navy']};
        color: #FFFFFF;
    }}
    .stButton > button:active {{
        background: {PALETTE['navy_dark']};
    }}

    /* ---- SECTION HEADERS ---- */
    .section-title {{
        font-family: 'Inter', Helvetica, Arial, sans-serif;
        font-size: 14px;
        font-weight: 800;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: {PALETTE['navy']};
        padding-bottom: 6px;
        border-bottom: 2px solid {PALETTE['orange']};
        display: inline-block;
        margin-bottom: 12px;
    }}

    /* ---- TABLES ---- */
    .stTable thead th {{
        background: {PALETTE['navy']};
        color: #FFFFFF;
        font-weight: 700;
        font-size: 11px;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        padding: 8px 12px;
    }}
    .stTable tbody td {{
        font-size: 13px;
        padding: 8px 12px;
    }}

    /* ---- SELECT BOX LABELS (inline controls) ---- */
    .stSelectbox label, .stTextInput label {{
        font-family: 'Inter', Helvetica, Arial, sans-serif;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        color: {PALETTE['navy']};
    }}

    /* ---- INPUTS ---- */
    .stTextInput > div > div > input {{
        border: 1px solid {PALETTE['border']};
        background: {PALETTE['white']};
        color: {PALETTE['dark_text']};
        font-size: 13px;
        padding: 8px 12px;
    }}
    .stTextInput > div > div > input:focus {{
        border-color: {PALETTE['orange']};
        box-shadow: 0 0 0 1px {PALETTE['orange']};
    }}

    /* ---- WARNINGS / ALERTS ---- */
    .stAlert {{
        font-size: 13px;
        font-weight: 500;
        border-radius: 0;
    }}

    /* ---- EXPANDER ---- */
    .streamlit-expanderHeader {{
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        color: {PALETTE['navy']};
        font-size: 12px;
    }}

    /* ---- FOOTER ---- */
    .invertek-footer {{
        background: {PALETTE['navy_dark']};
        color: {PALETTE['mid_gray']};
        padding: 20px 28px;
        font-size: 11px;
        letter-spacing: 0.4px;
        margin-top: 24px;
    }}
    .invertek-footer strong {{
        color: #FFFFFF;
        font-weight: 600;
    }}

    /* ---- LOADER / SPINNER ---- */
    .stSpinner > div {{
        border-top-color: {PALETTE['orange']} !important;
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
    "No emojis, no casual tone."
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
                <span>OPTIDRIVE &mdash; VARIABLE FREQUENCY DRIVES</span>
            </div>
        </div>
        <div class="header-badge">E3 DIAGNOSTICS</div>
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
            <span class="dot"></span> GLOBAL SUPPORT NETWORK
        </div>
        <div class="trust-badge">
            <span class="dot"></span> ISO 9001 CERTIFIED
        </div>
        <div class="trust-badge outline">
            <span class="dot"></span> OPTIDRIVE E3
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write(
    "Consult fault codes, parameter settings and wiring diagrams for "
    "Invertek Optidrive E3 variable frequency drives."
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
        "VFD MODEL",
        MODELS,
        label_visibility="visible",
    )
with col2:
    selected_category = st.selectbox(
        "CATEGORY",
        CATEGORIES,
        label_visibility="visible",
    )
with col3:
    firmware = st.text_input(
        "FIRMWARE",
        value="",
        placeholder="e.g. v2.10",
        label_visibility="visible",
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

        api_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        api_messages.extend(st.session_state.messages)

        try:
            with st.spinner("Analysing query..."):
                # --- First call: LLM may request a tool call ---
                response = client.chat.completions.create(
                    model="deepseek-v4-pro",
                    messages=api_messages,
                    max_tokens=500,
                    temperature=0.2,
                    tools=TOOL_DEFINITIONS,
                )

            assistant_msg = response.choices[0].message
            tool_calls = assistant_msg.tool_calls

            if tool_calls:
                # Execute tool calls and append results
                api_messages.append(assistant_msg)

                tool_sources = []
                for tc in tool_calls:
                    func_name = tc.function.name
                    func_args = json.loads(tc.function.arguments)
                    func = TOOL_MAP[func_name]
                    result = func(**func_args)

                    api_messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })

                    # Parse sources for display
                    parsed = json.loads(result)
                    tool_sources = parsed.get("documents", [])

                # --- Second call: LLM formulates final answer from tool results ---
                with st.spinner("Generating response..."):
                    response = client.chat.completions.create(
                        model="deepseek-v4-pro",
                        messages=api_messages,
                        max_tokens=500,
                        temperature=0.2,
                    )

                assistant_text = response.choices[0].message.content.strip()
            else:
                assistant_text = assistant_msg.content.strip()
                tool_sources = []

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": assistant_text,
                    "sources": tool_sources,
                }
            )

        except Exception as exc:
            st.error(f"API connection error: {exc}")

# =============================================================================
# Conversation history
# =============================================================================
st.markdown("---")
st.markdown(
    '<div class="section-title">CONVERSATION LOG</div>',
    unsafe_allow_html=True,
)

for message in st.session_state.messages[1:]:
    if message["role"] == "user":
        st.markdown(
            f"<div class='msg-user'>"
            f"<strong>ENGINEER QUERY</strong> {message['content']}"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='msg-agent'>"
            f"<strong>TECHNICAL RESPONSE</strong> {message['content']}"
            f"</div>",
            unsafe_allow_html=True,
        )
        sources = message.get("sources", [])
        if sources:
            with st.expander("REFERENCE DOCUMENTS"):
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
        <strong>INVERTEK DRIVES</strong> &mdash; A world leader in
        variable frequency drive technology.
        &nbsp;&middot;&nbsp;
        Optidrive E3 Technical Support Tool
        &nbsp;&middot;&nbsp;
        &copy; {__import__('datetime').datetime.now().year} Invertek Drives
    </div>
    """,
    unsafe_allow_html=True,
)
