from .drive_tools import (
    PROPOSE_CHANGES_TOOL_DEF,
    READ_DRIVE_STATUS_TOOL_DEF,
    READ_TRIP_HISTORY_TOOL_DEF,
    propose_parameter_changes,
    read_drive_status,
    read_trip_history,
)
from .ptb import modify_ptb_configuration
from .search_invertek_docs import SEARCH_TOOL_DEF, search_invertek_docs

# modify_ptb_configuration is deliberately NOT model-visible: the platform
# calls it itself when the technician presses Approve on a proposal card,
# so the model cannot bypass the approval step.
TOOL_DEFINITIONS = [
    SEARCH_TOOL_DEF,
    READ_DRIVE_STATUS_TOOL_DEF,
    READ_TRIP_HISTORY_TOOL_DEF,
    PROPOSE_CHANGES_TOOL_DEF,
]

TOOL_MAP = {
    "search_invertek_docs": search_invertek_docs,
    "read_drive_status": read_drive_status,
    "read_trip_history": read_trip_history,
    "propose_parameter_changes": propose_parameter_changes,
}

# Tools that receive the session's drive connection, injected by the
# platform — never taken from model arguments.
DRIVE_TOOLS = {
    "read_drive_status",
    "read_trip_history",
    "propose_parameter_changes",
}
