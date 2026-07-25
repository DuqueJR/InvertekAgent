import json
from pathlib import Path

from rag_engine import RAGEngine

KB_PATH = Path(__file__).parent / "knowledge_base.json"

_rag: RAGEngine | None = None


def _get_rag() -> RAGEngine:
    global _rag
    if _rag is None:
        _rag = RAGEngine(str(KB_PATH))
    return _rag


def search_invertek_docs(query: str, category: str = "") -> str:

    rag = _get_rag()
    results = rag.retrieve(query=query, model_filter="Optidrive E3", top_k=3)

    if not results:
        return json.dumps({
            "found": 0,
            "message": (
                "No matching documents in the E3 knowledge base. "
                "Advise the user to contact Invertek technical support "
                "or check the E3 installation manual directly."
            ),
        }, ensure_ascii=False)

    docs = []
    for r in results:
        docs.append({
            "id": r["id"],
            "title": r["title"],
            "content": r["content"],
            "relevance": f"{r['score']:.0%}",
        })

    return json.dumps({
        "found": len(docs),
        "documents": docs,
    }, ensure_ascii=False, indent=2)


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_invertek_docs",
            "description": (
                "Search the official Invertek Optidrive E3 technical "
                "knowledge base. Contains detailed specifications for "
                "fault codes (O-I, O-Volt, U-Volt, O-temp, P-Loss), "
                "motor parameters (P-03 to P-10, autotune), control "
                "wiring diagrams (2-wire and 3-wire start/stop), "
                "installation requirements, and EMC compliance. "
                "Use this tool BEFORE answering any technical question "
                "about Optidrive E3 to ensure accuracy."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Search query describing the technical issue, "
                            "fault code, parameter number, or wiring question. "
                            "Use English keywords. Examples: 'O-I fault', "
                            "'motor parameter P-08', '2-wire start stop wiring'."
                        ),
                    },
                    "category": {
                        "type": "string",
                        "enum": [
                            "Fault Codes & Diagnostics",
                            "Motor Parameters",
                            "Control Wiring Diagrams",
                            "General",
                        ],
                        "description": "Optional. Filter by document category.",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


TOOL_MAP = {
    "search_invertek_docs": search_invertek_docs,
}
