"""Branded UI components for the Invertek assistant.

Everything visual that does not touch the agent loop lives here: the
palette, the global CSS, the header/footer and the drive-panel widgets.
client.py owns state (session, messages, proposals) and calls in.
"""

import streamlit as st

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


def inject_css() -> None:
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
    /* Keep the header strip and its toolbar: the sidebar expand chevron
       lives inside stToolbar, so hiding the toolbar would strand the
       technician with no way to reopen the drive panel. Hide only the
       Streamlit-specific controls. */
    [data-testid="stHeader"] {{
        background: transparent;
    }}
    [data-testid="stDecoration"],
    [data-testid="stBaseButton-header"],
    [data-testid="stMainMenuButton"],
    [data-testid="stStatusWidget"],
    #MainMenu {{
        display: none !important;
    }}
    /* Sidebar toggle chevrons, in brand purple so they read as ours. */
    [data-testid="stToolbar"] button[kind="header"],
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="stExpandSidebarButton"] {{
        color: {PALETTE['purple']} !important;
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

    /* ---- SIDEBAR (drive panel) ---- */
    [data-testid="stSidebar"] {{
        background: {PALETTE['surface_alt']};
        border-right: 1px solid {PALETTE['line']};
    }}
    [data-testid="stSidebar"] .block-container {{
        padding-top: 1rem;
    }}
    .sidebar-title {{
        font-family: 'Mulish', 'Museo Sans', 'Segoe UI', system-ui, Arial, sans-serif;
        font-size: 14px;
        font-weight: 700;
        color: {PALETTE['purple']};
        border-bottom: 2px solid {PALETTE['line']};
        padding-bottom: 4px;
        margin: 10px 0 8px 0;
    }}
    .status-panel {{
        background: {PALETTE['surface']};
        border: 1px solid {PALETTE['line']};
        border-radius: 2px;
        padding: 10px 12px;
        font-size: 13px;
        margin-bottom: 8px;
    }}
    .status-panel .state-chip {{
        display: inline-flex;
        align-items: center;
        gap: 7px;
        font-size: 12px;
        font-weight: 700;
        padding: 3px 12px;
        border-radius: 999px;
        margin-bottom: 6px;
    }}
    .status-panel .state-chip .dot {{
        width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
    }}
    .state-chip.running {{ background: rgba(99,191,79,0.12); color: {PALETTE['green']}; }}
    .state-chip.running .dot {{ background: {PALETTE['green']}; }}
    .state-chip.tripped {{ background: rgba(180,35,24,0.08); color: {PALETTE['error']}; }}
    .state-chip.tripped .dot {{ background: {PALETTE['error']}; }}
    .state-chip.stopped {{ background: {PALETTE['surface_tile']}; color: {PALETTE['ink_muted']}; }}
    .state-chip.stopped .dot {{ background: {PALETTE['ink_muted']}; }}
    .state-chip.standby {{ background: rgba(83,84,131,0.10); color: {PALETTE['purple']}; }}
    .state-chip.standby .dot {{ background: {PALETTE['purple']}; }}
    .status-panel .metric-row {{
        display: flex;
        justify-content: space-between;
        border-bottom: 1px solid {PALETTE['line']};
        padding: 4px 0;
    }}
    .status-panel .metric-row:last-child {{ border-bottom: none; }}
    .status-panel .metric-row .value {{ font-weight: 700; color: {PALETTE['ink']}; }}
    .trip-item {{
        background: {PALETTE['surface']};
        border: 1px solid {PALETTE['line']};
        border-left: 3px solid {PALETTE['error']};
        border-radius: 2px;
        padding: 6px 10px;
        margin-bottom: 6px;
        font-size: 12px;
    }}
    .trip-item strong {{ color: {PALETTE['ink']}; font-size: 13px; }}
    .trip-item span {{ color: {PALETTE['ink_muted']}; }}
    [data-testid="stSidebar"] .stButton > button {{
        padding: 8px 12px;
        width: 100%;
        white-space: nowrap;
        font-size: 13px;
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
    /* ---- CITATION CHIPS ---- */
    .source-chips {{
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin: -4px 0 12px 0;
    }}
    .source-chip {{
        display: inline-flex;
        align-items: center;
        background: {PALETTE['surface_alt']};
        border: 1px solid {PALETTE['line']};
        color: {PALETTE['ink_muted']};
        padding: 3px 12px;
        font-size: 11px;
        font-weight: 600;
        border-radius: 999px;
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


def render_header() -> None:
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
            <div class="header-badge">E3 field assistant</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_panel(status) -> None:
    """Live drive status block for the sidebar."""
    chip_class = status.state_label.lower()
    fault_row = ""
    if status.tripped:
        fault_row = (
            f'<div class="metric-row"><span>Active fault</span>'
            f'<span class="value">{status.fault_code} &middot; '
            f'{status.fault_name}</span></div>'
        )
    st.markdown(
        f"""
        <div class="status-panel">
            <span class="state-chip {chip_class}"><span class="dot"></span>
            {status.state_label}</span>
            <div class="metric-row"><span>Output frequency</span>
            <span class="value">{status.output_freq_hz:.1f} Hz</span></div>
            <div class="metric-row"><span>Output current</span>
            <span class="value">{status.output_current_a:.2f} A</span></div>
            {fault_row}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_trip_history(trips) -> None:
    """Last-four trip log for the sidebar, newest first."""
    st.markdown(
        '<div class="sidebar-title">Trip history (last 4)</div>',
        unsafe_allow_html=True,
    )
    if not trips:
        st.caption("No trips recorded in this session.")
        return
    for trip in trips:
        st.markdown(
            f'<div class="trip-item"><strong>{trip.fault_code}</strong> '
            f'<span>&middot; {trip.fault_name}</span></div>',
            unsafe_allow_html=True,
        )


MAX_SOURCE_CHIPS = 6


def _chip_label(citation: str) -> str:
    """Section and page only: every KB entry cites the same user guide, so
    repeating its title on each chip crowds out the part that differs."""
    parts = [p.strip() for p in citation.split(",")]
    if len(parts) > 1 and "User Guide" in parts[0]:
        parts = parts[1:]
    return ", ".join(parts) or citation


def render_source_chips(sources) -> None:
    """Citation chips under an answer: section and printed page, best first.

    Gives the technician the same provenance the agent was told to quote,
    so a weak or irrelevant citation is visible rather than implied. One
    chip per distinct citation, since several searches in a turn return
    the same document repeatedly.
    """
    best = {}
    for src in sources:
        citation = src.get("source") or src.get("title") or src.get("id", "")
        if not citation:
            continue
        try:
            relevance = int(str(src.get("relevance", "0")).rstrip("%"))
        except ValueError:
            relevance = 0
        if citation not in best or relevance > best[citation]:
            best[citation] = relevance

    if not best:
        return

    ranked = sorted(best.items(), key=lambda kv: kv[1], reverse=True)
    chips = [
        f'<span class="source-chip" title="{citation}">'
        f"{_chip_label(citation)} &middot; {relevance}%</span>"
        for citation, relevance in ranked[:MAX_SOURCE_CHIPS]
    ]
    hidden = len(ranked) - len(chips)
    if hidden > 0:
        chips.append(
            f'<span class="source-chip">+{hidden} more in reference '
            f"documents</span>"
        )
    st.markdown(
        '<div class="source-chips">' + "".join(chips) + "</div>",
        unsafe_allow_html=True,
    )


def render_footer() -> None:
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
