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
from drive import (
    DriveError,
    SerialDriveClient,
    SimulatedDriveClient,
    apply_change_set,
    list_serial_ports,
)
from tools import (
    DRIVE_TOOLS,
    PTB_PATH_TOOLS,
    TOOL_DEFINITIONS,
    TOOL_MAP,
    modify_ptb_configuration,
)
from ui import (
    PALETTE,
    inject_css,
    render_footer,
    render_header,
    render_source_chips,
    render_status_panel,
    render_trip_history,
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
    initial_sidebar_state="expanded",
)

# =============================================================================
# Brand look & feel (palette + CSS live in ui.py)
# =============================================================================
inject_css()

# =============================================================================
# Constants
# =============================================================================
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
    "4b. Judge the results, do not just cite them. If the documents "
    "returned do not actually answer the question - low relevance, or "
    "merely adjacent subject matter - say plainly that the E3 knowledge "
    "base does not cover it and refer the technician to Invertek "
    "technical support. A weak match is not an answer.\n"
    "4c. Every factual claim must carry its citation: quote the `source` "
    "field of the document you used, including the printed page, e.g. "
    "\"Source: Optidrive E3 IP20 User Guide V1.05, 10.1 Fault Code "
    "Messages, p.39\". Never cite a document you did not use.\n"
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
    "data would change your answer.\n"
    "8b. To learn a parameter's current setting, call `read_parameters` "
    "with the codes you need. It reads the drive live, or the uploaded "
    ".ptb when there is no connection. NEVER ask the technician to type "
    "out values you can read yourself — only ask when the tool reports "
    "them unavailable.\n\n"
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
render_header()

st.write(
    "Connect the drive to read its live status and trip history, then "
    "describe the problem. Parameter fixes appear as a preview you "
    "approve before anything is written to the drive."
)

# =============================================================================
# Chat history initialisation
# =============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

api_key = DEEPSEEK_API_KEY
selected_model = "Optidrive E3"

# =============================================================================
# Sidebar – drive connection, live status, trip history, .ptb upload
# =============================================================================
if "ptb_workdir" not in st.session_state:
    st.session_state.ptb_workdir = tempfile.mkdtemp(prefix="invertek_ptb_")

drive_client = st.session_state.get("drive_client")
drive_connected = drive_client is not None and drive_client.is_connected

with st.sidebar:
    st.markdown(
        '<div class="sidebar-title">Drive connection</div>',
        unsafe_allow_html=True,
    )
    connection_mode = st.radio(
        "Connection mode",
        ["Simulator", "Serial (USB-RS485)"],
        key="connection_mode",
        disabled=drive_connected,
        help=(
            "Simulator behaves like a real E3 for demos. Serial talks "
            "Modbus RTU through a USB-to-RS485 adapter."
        ),
    )

    if not drive_connected:
        if connection_mode == "Simulator":
            if st.button("Connect", key="connect_button"):
                client = SimulatedDriveClient()
                client.connect()
                st.session_state.drive_client = client
                st.session_state.drive_mode = "simulator"
                st.rerun()
        else:
            ports = list_serial_ports()
            port = st.selectbox(
                "Serial port",
                ports or ["No ports detected"],
                key="serial_port",
                disabled=not ports,
            )
            baud = st.number_input(
                "Baud rate", value=115200, step=9600, key="serial_baud",
                help="Drive default is 115200 (P-36 index 2).",
            )
            address = st.number_input(
                "Drive address", value=1, min_value=1, max_value=63,
                key="serial_address",
                help="Set in P-36 index 1; factory default 1.",
            )
            if st.button("Connect", key="connect_button", disabled=not ports):
                try:
                    client = SerialDriveClient(
                        port, baud=int(baud), address=int(address)
                    )
                    client.connect()
                    st.session_state.drive_client = client
                    st.session_state.drive_mode = f"serial {port}"
                    st.rerun()
                except DriveError as exc:
                    st.error(str(exc))
    else:
        if st.button("Disconnect", key="disconnect_button"):
            drive_client.disconnect()
            st.session_state.drive_client = None
            st.rerun()

        st.markdown(
            '<div class="sidebar-title">Drive status</div>',
            unsafe_allow_html=True,
        )
        try:
            live_status = drive_client.read_status()
            render_status_panel(live_status)
            render_trip_history(drive_client.read_trip_history())
        except DriveError as exc:
            st.error(f"Drive read failed: {exc}")

        if st.button("Refresh status", key="refresh_status"):
            st.rerun()

        if isinstance(drive_client, SimulatedDriveClient):
            st.markdown(
                '<div class="sidebar-title">Simulator controls</div>',
                unsafe_allow_html=True,
            )
            sim_run, sim_stop, sim_trip = st.columns(3)
            if sim_run.button("Run", key="sim_run"):
                drive_client.simulate_run()
                st.rerun()
            if sim_stop.button("Stop", key="sim_stop"):
                drive_client.simulate_stop()
                st.rerun()
            if sim_trip.button("Trip", key="sim_trip"):
                drive_client.simulate_trip(3)  # O-I, output over current
                st.rerun()

    st.markdown(
        '<div class="sidebar-title">Configuration file</div>',
        unsafe_allow_html=True,
    )
    uploaded_ptb = st.file_uploader(
        "Drive configuration file (.ptb) — optional",
        type=["ptb"],
        help=(
            "Upload the drive's parameter file so approved changes also "
            "produce a modified copy you can download."
        ),
    )

    ptb_input_path = None
    if uploaded_ptb is not None:
        workdir = Path(st.session_state.ptb_workdir)
        ptb_input_path = str(workdir / uploaded_ptb.name)
        with open(ptb_input_path, "wb") as fh:
            fh.write(uploaded_ptb.getbuffer())
        st.caption(
            f"{uploaded_ptb.name} loaded. Approved changes produce a "
            "modified copy to download from the proposal card."
        )

    with st.expander("Session details"):
        selected_category = st.selectbox("Category", CATEGORIES)
        firmware = st.text_input(
            "Firmware", value="", placeholder="e.g. v3.11"
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
            connection_line = (
                "Drive connection: connected "
                f"({st.session_state.get('drive_mode', 'simulator')})."
            )
            try:
                s = drive_client.read_status()
                connection_line += f" Current drive state: {s.state_label}"
                if s.tripped:
                    connection_line += (
                        f" ({s.fault_code} - {s.fault_name})"
                    )
                connection_line += "."
            except DriveError:
                pass
            context_lines.append(connection_line)
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
                        # connection and file, regardless of what the model sent.
                        if func_name in DRIVE_TOOLS:
                            func_args["drive"] = drive_client
                        if func_name in PTB_PATH_TOOLS:
                            func_args["ptb_path"] = ptb_input_path

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
    # The drive is the authority on whether a change took effect; the .ptb
    # copy is a convenience artefact, so a file shortfall is reported as a
    # warning and never downgrades a verified drive write to "failed".
    drive_outcome = None   # True/False once attempted, None if no drive
    ptb_outcome = None
    try:
        drive = st.session_state.get("drive_client")
        if drive is not None and drive.is_connected:
            report = apply_change_set(drive, changes)
            message["apply_report"] = report
            drive_outcome = bool(report["success"])
            if drive_outcome:
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
            # Non-strict: write the parameters this file actually contains
            # and report the rest, rather than abandoning the whole copy.
            ptb_report = json.loads(modify_ptb_configuration(
                ptb_input_path=ptb_input_path,
                changes=changes,
                output_path=out_path,
                strict=False,
            ))
            message["ptb_report"] = ptb_report
            ptb_outcome = bool(ptb_report.get("success"))
            if ptb_outcome:
                try:
                    message["ptb_bytes"] = Path(
                        ptb_report["output_path"]
                    ).read_bytes()
                except OSError:
                    message["ptb_bytes"] = None
                skipped = ptb_report.get("rejected", [])
                notice.append(
                    "A modified .ptb copy is ready to download under the "
                    "proposal card."
                    + (
                        f" {len(skipped)} change(s) were not present in the "
                        f"file and were left out of the copy."
                        if skipped else ""
                    )
                )
            else:
                reasons = "; ".join(
                    f"{r.get('code') or '?'}: {r['message']}"
                    for r in ptb_report.get("rejected", [])
                )
                notice.append(
                    "The .ptb copy could not be written, which does not "
                    f"affect the drive itself: {reasons}"
                )

        if drive_outcome is None and ptb_outcome is None:
            failed = True
            notice = [
                "Nothing to apply: connect a drive or upload a .ptb file, "
                "then approve again."
            ]
        elif drive_outcome is not None:
            # A drive was connected: its result decides the outcome.
            failed = not drive_outcome
        else:
            failed = not ptb_outcome
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
            render_source_chips(sources)
            # Several searches in one turn return the same documents, so
            # show each one once, at its best relevance.
            unique = {}
            for src in sources:
                key = src.get("id") or src.get("title")
                try:
                    score = int(str(src.get("relevance", "0")).rstrip("%"))
                except ValueError:
                    score = 0
                if key not in unique or score > unique[key][0]:
                    unique[key] = (score, src)
            with st.expander(f"Reference documents ({len(unique)})"):
                for score, src in sorted(
                    unique.values(), key=lambda pair: pair[0], reverse=True
                ):
                    st.markdown(
                        f"**{src['title']}**  "
                        f"_(relevance: {src.get('relevance', 'N/A')})_"
                    )
                    if src.get("source"):
                        st.caption(f"Source: {src['source']}")
                    st.caption(src["content"])

# =============================================================================
# Footer
# =============================================================================
render_footer()
