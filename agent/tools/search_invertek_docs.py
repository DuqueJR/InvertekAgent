import json
import math
import re
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

# manifest.json is KB metadata; REVIEW_NOTES.md is curator meta — neither is
# drive documentation, so both stay out of search results.
SKIP_FILES = {"manifest", "REVIEW_NOTES"}


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


# Words that carry no retrieval signal. Without this list a question like
# "how do I service the fan bearings" scored 99% on every document (each
# "the"/"do" occurrence added to the score), so the found:0 honesty path
# never fired and the agent always had something to cite.
STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "what", "when",
    "how", "why", "does", "did", "are", "was", "you", "your", "can",
    "should", "would", "will", "have", "has", "any", "all", "but", "not",
    "its", "it's", "there", "then", "than", "them", "they", "get", "got",
    "out", "off", "into", "onto", "about", "after", "before", "every",
    "some", "such", "which", "while", "just", "only", "also", "been",
    "being", "here", "very", "much", "more", "most", "need", "needs",
    "want", "wants", "know", "please", "help", "tell", "give", "show",
    "make", "made", "take", "keeps", "keep", "time", "times", "still",
    "now", "one", "two", "use", "used", "using", "see", "look", "like",
    "may", "might", "must", "could", "shall", "who", "whom", "whose",
    "where", "because", "since", "each", "both", "over", "under",
    # Short function words. Left in, they matched almost every document
    # and inflated coverage to the point that found:0 never fired.
    "is", "of", "do", "in", "to", "on", "at", "by", "or", "if", "as",
    "be", "an", "my", "we", "so", "no", "up", "it", "am", "me", "us",
    "our", "his", "her", "was", "were", "had", "doing", "done", "goes",
}

# A result must cover a meaningful share of the query's real terms to be
# offered as a citation. Below this the tool reports found:0 so the agent
# says plainly that the knowledge base does not cover the question.
MIN_RELEVANCE = 0.34


def _terms_of(query: str) -> list:
    """Meaningful search terms: punctuation stripped, stopwords removed."""
    raw = [t.strip(".,;:!?()[]{}'\"") for t in query.lower().split()]
    raw = [t for t in raw if t]
    terms = [t for t in raw if len(t) > 1 and t not in STOPWORDS]
    # A query made entirely of stopwords still deserves a literal attempt.
    return terms or raw


@lru_cache(maxsize=512)
def _term_pattern(term: str):
    """Whole-word matcher for a term, tolerating a plural 's'.

    Substring matching used to count "is" inside "resistance" and similar,
    which is how unrelated questions scored full marks.
    """
    stem = term[:-1] if len(term) > 3 and term.endswith("s") else term
    return re.compile(rf"(?<!\w){re.escape(stem)}s?(?!\w)")


def _count_term(text_lower: str, term: str) -> int:
    return len(_term_pattern(term).findall(text_lower))


@lru_cache(maxsize=1)
def _corpus() -> tuple:
    """Every searchable unit as one lowercased blob, for term statistics."""
    blobs = []
    for filepath in sorted(DATA_DIR.rglob("*")):
        if (not filepath.is_file() or filepath.stem in SKIP_FILES
                or filepath.suffix not in (".md", ".json")):
            continue
        try:
            raw = filepath.read_text(encoding="utf-8")
        except Exception:
            continue
        if filepath.suffix == ".json":
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            for key in ("faults", "parameters", "read_only_status_parameters"):
                for entry in data.get(key, []):
                    blobs.append(json.dumps(entry).lower())
        else:
            blobs.append(raw.lower())
    return tuple(blobs)


@lru_cache(maxsize=1024)
def _idf(term: str) -> float:
    """Inverse document frequency: how much signal this term carries.

    Words present in nearly every document ("drive", "motor", "invertek")
    approach zero, so a question that only shares those words with the
    knowledge base scores near zero and reaches the found:0 path instead
    of being answered from an irrelevant citation.
    """
    corpus = _corpus()
    if not corpus:
        return 1.0
    df = sum(1 for blob in corpus if _term_pattern(term).search(blob))
    return math.log(len(corpus) / (1 + df))


def _score_text(text, terms):
    """Relevance as the share of the query's *informative* weight matched.

    Each term counts in proportion to its IDF, so covering the rare,
    meaningful terms of a question matters and covering only its filler
    does not. Repetition adds a small bonus. Scores stay comparable
    across documents so MIN_RELEVANCE can separate "covered by the
    knowledge base" from "not covered".
    """
    if not terms:
        return 0.0
    text_lower = text.lower()
    total_weight = 0.0
    matched_weight = 0.0
    bonus = 0.0
    for term in terms:
        weight = max(_idf(term), 0.01)
        total_weight += weight
        count = _count_term(text_lower, term)
        if count:
            matched_weight += weight
            bonus += min(count, 5) * 0.01
    if not matched_weight or not total_weight:
        return 0.0
    return min(matched_weight / total_weight + bonus, 0.99)


def _format_source(source):
    """Render a KB source object as a citable one-liner.

    Every KB entry carries {document, section, page}; the agent is required
    to quote this verbatim, so keep the printed page number intact.
    """
    if isinstance(source, str):
        return source
    if not isinstance(source, dict):
        return ""
    parts = [source.get("document"), source.get("section")]
    page = source.get("page")
    if page not in (None, ""):
        parts.append(f"p.{page}")
    return ", ".join(str(p) for p in parts if p)


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
                "source": _format_source(fault.get("source")),
                "score": score,
            })
    return results


def _search_json_parameters(data, terms, file_id):
    results = []
    settable = data.get("parameters", [])
    read_only = data.get("read_only_status_parameters", [])
    for param in settable + read_only:
        searchable = json.dumps(param).lower()
        score = _score_text(searchable, terms)
        code = param.get("id", "?")
        # An exact code in the query (e.g. "P-08") must outrank entries that
        # merely repeat common words like "motor" or "current".
        if code.lower() in terms:
            score += 1.0
        if score > 0:
            parts = []
            if param.get("group"):
                parts.append(f"Group: {param['group']}")
            if param.get("function"):
                parts.append(f"Function: {param['function']}")
            if param.get("explanation"):
                parts.append(f"Explanation: {param['explanation']}")
            rng = param.get("range") or {}
            if rng.get("min") is not None or rng.get("max") is not None:
                units = rng.get("units") or ""
                parts.append(f"Range: {rng.get('min', '?')} to {rng.get('max', '?')} {units}".rstrip())
            if param.get("default"):
                parts.append(f"Default: {param['default']}")
            if param.get("notes"):
                parts.append(f"Notes: {param['notes']}")
            results.append({
                "id": f"{file_id}__{code}",
                "title": f"{code} {param.get('name', '')}".strip(),
                "content": _truncate(" | ".join(parts)),
                "source": _format_source(param.get("source")),
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
    terms = _terms_of(query)

    results = []

    # The KB nests prose under procedures/ and reference/, so walk recursively.
    for filepath in sorted(DATA_DIR.rglob("*")):
        if not filepath.is_file():
            continue
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

        fm_text = " ".join(f"{k} {v}" for k, v in frontmatter.items())
        # The body carries the answer; the frontmatter (title, topic,
        # keywords) is a boost rather than half the signal, so a document
        # that fully covers the query in prose is not penalised for having
        # terse metadata.
        score = min(
            _score_text(body, terms) + 0.3 * _score_text(fm_text, terms), 0.99
        )

        # Category is a soft boost, never a hard filter: the UI labels
        # ("Fault Codes & Diagnostics") don't literally appear in the
        # frontmatter slugs ("fault-codes"), so exact matching used to
        # discard every markdown document whenever a category was set.
        if category and score > 0:
            cat_terms = [t.strip("&,").lower() for t in category.split()]
            cat_terms = [t for t in cat_terms if len(t) > 2]
            haystack = " ".join((
                frontmatter.get("topic", ""),
                frontmatter.get("keywords", ""),
                frontmatter.get("title", ""),
            )).lower()
            if any(t in haystack for t in cat_terms):
                score = min(score * 1.25, 0.99)

        if score > 0:
            title = frontmatter.get("title", filepath.stem)
            snippet = _extract_snippet(body, terms)
            results.append({
                "id": filepath.stem,
                "title": title,
                "content": snippet,
                "source": _format_source(frontmatter.get("source")),
                "score": score,
            })

    # Drop weak matches rather than dressing them up as citations: an
    # answer the knowledge base does not support must reach the found:0
    # path so the agent says so plainly.
    results = [r for r in results if r["score"] >= MIN_RELEVANCE]
    results.sort(key=lambda r: r["score"], reverse=True)
    results = results[:5]

    for r in results:
        r["relevance"] = f"{min(r['score'], 0.99):.0%}"
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
            "about Optidrive E3 to ensure accuracy. Every result carries "
            "a `source` field naming the document, section and printed "
            "page - quote it verbatim in your answer."
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
                    "description": (
                        "Optional. Boosts documents matching the category; "
                        "never excludes results."
                    ),
                },
            },
            "required": ["query"],
        },
    },
}
