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
    '<div class="section-title">Conversation log</div>',
    unsafe_allow_html=True,
)

for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(
            f"<div class='msg-user'>"
            f"<strong>Engineer query</strong> {message['content']}"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='msg-agent'>"
            f"<strong>Technical response</strong> {message['content']}"
            f"</div>",
            unsafe_allow_html=True,
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