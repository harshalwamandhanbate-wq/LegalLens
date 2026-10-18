"""Offline tests: no Ollama and no Streamlit needed."""
from pathlib import Path

import pytest

from ai_agent import chunk_pages, select_chunks, verify_quote, _has_format
from doc_parser import DocumentError, extract_pages
from report import build_html_report, build_markdown_report, summarize
from scanner import scan_document
from ui_helpers import (
    clause_quotes, esc, highlight_fragments, highlight_text, md_safe, parse_answer, parse_risk,
)

SAMPLE = Path(__file__).parent.parent / "samples" / "sample_contract.pdf"

ANSWER = (
    "### \U0001F50D Analysis\nThe employee pays a $10,000 fine.\n"
    "### \U0001F6A9 Risk Level\n**HIGH** - Immediate termination and a large fine.\n"
    "### \U0001F4DC Relevant Clause\n\"Penalty for breach is immediate termination and a $10,000 fine.\""
)
PAGES = [
    {"page": 1, "text": "Intro line\nPenalty for breach is immediate termination and a $10,000 fine."},
    {"page": 2, "text": "Rent is due on the 1st. A late fee of $50 applies after the 5th."},
]


@pytest.fixture(scope="module")
def sample_pages():
    return extract_pages(SAMPLE)


# --- parsing the PDF -------------------------------------------------------- #
def test_sample_pdf_has_two_pages_of_text(sample_pages):
    assert len(sample_pages) == 2 and all(p["text"] for p in sample_pages)


def test_bad_pdf_gives_friendly_error(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"this is not a pdf")
    with pytest.raises(DocumentError):
        extract_pages(bad)


# --- chunking and retrieval --------------------------------------------------- #
def test_retrieval_prefers_relevant_chunk():
    filler = [{"page": 1, "text": "\n".join(f"Parking and lunch rule {i}." for i in range(400))}]
    pages = filler + [{"page": 2, "text": "The penalty for breach is a fine."}]
    chunks = chunk_pages(pages)
    selected, truncated = select_chunks(chunks, "What is the penalty for breach?", budget=2500)
    assert truncated
    assert any("penalty for breach" in c["text"] for c in selected)


# --- grounding check ---------------------------------------------------------- #
def test_quote_verification():
    assert verify_quote(ANSWER, PAGES) == (True, [1])
    assert verify_quote(ANSWER.replace("immediate termination", "a stern talking-to"), PAGES) == (False, [])
    assert verify_quote("### Relevant Clause\nNone", PAGES) == (None, [])


def test_format_check():
    assert _has_format(ANSWER)
    assert not _has_format("just some text")


# --- UI helpers ----------------------------------------------------------------- #
def test_parse_answer_and_risk():
    sections = parse_answer(ANSWER)
    assert set(sections) == {"analysis", "risk level", "relevant clause"}
    assert parse_risk(sections["risk level"]) == ("HIGH", "Immediate termination and a large fine.")
    assert clause_quotes(sections["relevant clause"])[0].startswith("Penalty for breach")


def test_escaping_blocks_html_and_latex():
    assert "<script>" not in esc("<script>alert(1)</script>")
    assert "$" not in esc("$10,000")
    assert md_safe("$5") == "\\$5"


def test_highlight_marks_quote_and_escapes_rest():
    frags = highlight_fragments(clause_quotes(parse_answer(ANSWER)["relevant clause"]))
    out = highlight_text("<b>x</b> Penalty for breach is immediate  termination and a $10,000 fine.", frags)
    assert "<mark>" in out and "&lt;b&gt;" in out and "\n" not in out


# --- quick scan ------------------------------------------------------------------ #
def test_scan_finds_flags_and_facts(sample_pages):
    scan = scan_document(sample_pages)
    labels = {f["label"] for f in scan["findings"]}
    assert {"Automatic renewal", "Penalties and fines", "Non-compete and exclusivity"} <= labels
    assert scan["findings"][0]["severity"] == "high"          # high severity sorted first
    assert any("50,000" in i["text"] for i in scan["facts"]["money"])
    assert any("90 days" in i["text"] for i in scan["facts"]["periods"])
    assert any("2026" in i["text"] for i in scan["facts"]["dates"])


# --- reports ----------------------------------------------------------------------- #
def make_history():
    result = {"kind": "ok", "answer": ANSWER, "grounded": True, "quote_pages": [1], "warnings": [], "excerpts": []}
    return [{"question": "What is the penalty?", "result": result, "time": "10:00"}]


def test_reports_contain_scan_and_answers(sample_pages):
    scan = scan_document(sample_pages)
    md = build_markdown_report("sample.pdf", 2, scan, make_history(), "gemma2:2b")
    html = build_html_report("sample.pdf", 2, scan, make_history(), "gemma2:2b")
    for text in (md, html):
        assert "What is the penalty?" in text and "Verified in the PDF (page 1)" in text
    assert "| Automatic renewal |" in md
    assert html.startswith("<!doctype html>")


def test_summarize_handles_not_found():
    s = summarize({"kind": "not_found", "answer": "x", "grounded": None, "quote_pages": []})
    assert s["level"] is None and "does not seem to answer" in s["analysis"]
