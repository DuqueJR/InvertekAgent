from .ptb import MODIFY_PTB_TOOL_DEF, modify_ptb_configuration
from .search_invertek_docs import SEARCH_TOOL_DEF, search_invertek_docs

TOOL_DEFINITIONS = [SEARCH_TOOL_DEF, MODIFY_PTB_TOOL_DEF]

TOOL_MAP = {
    "search_invertek_docs": search_invertek_docs,
    "modify_ptb_configuration": modify_ptb_configuration,
}
