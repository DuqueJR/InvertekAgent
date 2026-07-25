import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

SKIP_FILES = {"manifest", "download"}


def _parse_frontmatter(text):
    frontmatter = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().split("\n"):
                line = line.strip()
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    frontmatter[key] = val
            body = parts[2].strip()
    return frontmatter, body


def _score_text(text, terms):
    text_lower = text.lower()
    score = 0.0
    for term in terms:
        count = text_lower.count(term)
        if count:
            score += count * 0.1
            if f" {term} " in f" {text_lower} ":
                score += 0.05
    return min(score, 0.99)


def _truncate(text, max_len=600):
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def _extract_snippet(text, terms, radius=200):
    text_lower = text.lower()
    for term in terms:
        idx = text_lower.find(term)
        if idx != -1:
            start = max(0, idx - radius)
            end = min(len(text), idx + len(term) + radius)
            snippet = text[start:end]
            if start > 0:
                snippet = "..." + snippet
            if end < len(text):
                snippet = snippet + "..."
            return snippet
    return _truncate(text)


def _search_json_faults(data, terms, file_id):
    results = []
    faults = data.get("faults", [])
    for fault in faults:
        searchable = json.dumps(fault).lower()
        score = _score_text(searchable, terms)
        if score > 0:
            parts = []
            if fault.get("code"):
                parts.append(f"Code: {fault['code']}")
            if fault.get("name"):
                parts.append(f"Name: {fault['name']}")
            if fault.get("display_number"):
                parts.append(f"Display: {fault['display_number']}")
            if fault.get("category"):
                parts.append(f"Category: {fault['category']}")
            if fault.get("description"):
                parts.append(f"Description: {fault['description']}")
            for cause in fault.get("possible_causes", []):
                parts.append(f"Cause: {cause}")
            for step in fault.get("diagnostic_steps", []):
                parts.append(f"Step: {step}")
            if fault.get("reset_notes"):
                parts.append(f"Reset: {fault['reset_notes']}")
            if fault.get("related_parameters"):
                parts.append(f"Related params: {', '.join(fault['related_parameters'])}")

            results.append({
                "id": f"{file_id}__{fault.get('code', fault.get('display_number', ''))}",
                "title": f"{fault.get('name', 'Unknown')} ({fault.get('code', 'N/A')})",
                "content": _truncate(" | ".join(parts)),
                "score": score,
            })
    return results


def _search_json_parameters(data, terms, file_id):
    results = []
    params = data.get("parameters", [])
    for param in params:
        searchable = json.dumps(param).lower()
        score = _score_text(searchable, terms)
        if score > 0:
            parts = []
            if param.get("number"):
                parts.append(f"P-{param['number']}")
            if param.get("name"):
                parts.append(f"Name: {param['name']}")
            if param.get("description"):
                parts.append(f"Desc: {param['description']}")
            results.append({
                "id": f"{file_id}__{param.get('number', '')}",
                "title": f"P-{param.get('number', '?')} {param.get('name', '')}",
                "content": _truncate(" | ".join(parts)),
                "score": score,
            })
    return results


def _search_json_structure(data, terms, file_id):
    results = []
    if "faults" in data:
        results.extend(_search_json_faults(data, terms, file_id))
    if "parameters" in data:
        results.extend(_search_json_parameters(data, terms, file_id))
    return results


def search_invertek_docs(query: str, category: str = "") -> str:
    query_lower = query.lower()
    terms = [t for t in query_lower.split() if len(t) > 1]
    if not terms:
        terms = [query_lower]

    results = []

    for filepath in sorted(DATA_DIR.iterdir()):
        if filepath.stem in SKIP_FILES:
            continue
        if filepath.suffix not in (".md", ".json"):
            continue

        try:
            raw = filepath.read_text(encoding="utf-8")
        except Exception:
            continue

        if filepath.suffix == ".json":
            try:
                data = json.loads(raw)
                snippets = _search_json_structure(data, terms, filepath.stem)
                results.extend(snippets)
                continue
            except json.JSONDecodeError:
                pass

        frontmatter, body = _parse_frontmatter(raw)

        if category:
            topic = frontmatter.get("topic", "").lower()
            keywords_str = frontmatter.get("keywords", "").lower()
            cat_lower = category.lower()
            if cat_lower not in topic and cat_lower not in keywords_str:
                continue

        fm_text = " ".join(f"{k} {v}" for k, v in frontmatter.items())
        score = _score_text(fm_text, terms) * 0.4 + _score_text(body, terms) * 0.6

        if score > 0:
            title = frontmatter.get("title", filepath.stem)
            snippet = _extract_snippet(body, terms)
            results.append({
                "id": filepath.stem,
                "title": title,
                "content": snippet,
                "score": score,
            })

    results.sort(key=lambda r: r["score"], reverse=True)
    results = results[:5]

    for r in results:
        r["relevance"] = f"{r['score']:.0%}"
        del r["score"]

    if not results:
        return json.dumps({
            "found": 0,
            "message": (
                "No matching documents in the E3 knowledge base. "
                "Advise the user to contact Invertek technical support "
                "or check the E3 installation manual directly."
            ),
        }, ensure_ascii=False)

    return json.dumps({
        "found": len(results),
        "documents": results,
    }, ensure_ascii=False, indent=2)


SEARCH_TOOL_DEF = {
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
}
