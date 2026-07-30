"""Retrieval must be citable and honest.

Two properties matter for the product: every result carries the document,
section and printed page the agent is required to quote, and a question
the knowledge base does not cover must reach the found:0 path so the
agent says so plainly instead of answering from an irrelevant document.
"""

import json

import pytest

from agent.tools.search_invertek_docs import (
    MIN_RELEVANCE,
    SKIP_FILES,
    _idf,
    _terms_of,
    search_invertek_docs,
)


def search(query, **kwargs):
    return json.loads(search_invertek_docs(query, **kwargs))


# --- citations --------------------------------------------------------------

@pytest.mark.parametrize("query", [
    "O-I overcurrent trip",          # fault_codes.json entry
    "P-08 motor rated current",      # parameters.json entry
    "brake resistor installation",   # markdown document
])
def test_every_result_carries_a_source(query):
    payload = search(query)
    assert payload["found"] > 0
    for doc in payload["documents"]:
        assert doc["source"], f"{doc['id']} has no citation"
        assert "Optidrive E3" in doc["source"]
        assert "p." in doc["source"] or "pp." in doc["source"]


def test_read_only_parameters_are_searchable_and_cited():
    payload = search("P00-13 trip log")
    ids = [d["id"] for d in payload["documents"]]
    assert any("P00-13" in i for i in ids)
    top = payload["documents"][0]
    assert "6.4" in top["source"]  # read-only status parameter section


def test_metadata_files_are_never_offered_as_sources():
    assert SKIP_FILES == {"manifest", "REVIEW_NOTES"}
    for query in ("manifest", "coverage notes", "kb_built"):
        for doc in search(query).get("documents", []):
            assert doc["id"] not in ("manifest", "REVIEW_NOTES")


# --- honesty ----------------------------------------------------------------

@pytest.mark.parametrize("query", [
    "recipe for chocolate cake",
    "what is the price of this drive",
    "how do I connect this to a PLC over EtherCAT",
    "how do I service the fan bearings",
])
def test_out_of_scope_questions_return_found_zero(query):
    payload = search(query)
    assert payload["found"] == 0
    message = payload["message"].lower()
    assert "no matching documents" in message
    assert "invertek technical support" in message


@pytest.mark.parametrize("query", [
    "O-I overcurrent trip",
    "U-Volt undervoltage",
    "acceleration ramp time P-03",
    "reset parameters to factory defaults",
    "single phase operation",
    "motor thermistor connection",
    "EMC compliant installation",
    "how do I set the maximum frequency",
])
def test_genuine_questions_still_retrieve(query):
    payload = search(query)
    assert payload["found"] > 0, f"{query!r} should be covered by the KB"


def test_results_never_fall_below_the_relevance_floor():
    payload = search("motor trips on overcurrent during acceleration")
    for doc in payload["documents"]:
        assert int(doc["relevance"].rstrip("%")) >= MIN_RELEVANCE * 100 - 1


# --- scoring internals ------------------------------------------------------

def test_stopwords_are_dropped_from_queries():
    assert _terms_of("how do I reset the drive") == ["reset", "drive"]
    # A query of pure filler still gets a literal attempt rather than nothing.
    assert _terms_of("what is it") == ["what", "is", "it"]


def test_ubiquitous_terms_carry_less_weight_than_rare_ones():
    # "drive" is in nearly every document; "thermistor" in a handful.
    assert _idf("thermistor") > _idf("drive")
    assert _idf("drive") < 1.0


def test_word_boundary_matching_avoids_substring_false_positives():
    # "is" must not match inside "resistance", which is what let unrelated
    # questions score full marks.
    from agent.tools.search_invertek_docs import _count_term

    assert _count_term("resistance and distance", "is") == 0
    assert _count_term("this is the value", "is") == 1


def test_category_boosts_but_never_excludes():
    plain = search("O-I overcurrent trip")
    boosted = search("O-I overcurrent trip", category="Fault Codes & Diagnostics")
    assert boosted["found"] == plain["found"]
