import io
from datetime import datetime
from pathlib import Path

import requests
import streamlit as st

from ai_agent import MODEL, OLLAMA_CHAT_URL, AIError, analyze_legal_text
from doc_parser import DocumentError, extract_pages
from report import build_html_report, build_markdown_report
from scanner import scan_document
from ui_helpers import (
    CSS, chips_html, clause_quotes, document_html, evidence_html, facts_html, hero_html,
    highlight_fragments, md_safe, parse_answer, parse_risk, scan_html, steps_html, verdict_html,
)

SAMPLE_PATH = Path(__file__).parent / "samples" / "sample_contract.pdf"
MAX_HISTORY = 20
SAMPLES = {
    "What if I breach it?": "What are the penalties or consequences if I breach this contract?",
    "Payments and deadlines": "What payment terms and deadlines does this contract set?",
    "How can it end?": "How can this contract be terminated, and by whom?",
}


# --------------------------------------------------------------------------- #
# Cached helpers
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def load_pages(file_bytes: bytes):
    """Cached so Streamlit reruns (every click) don't re-parse the PDF."""
    return extract_pages(io.BytesIO(file_bytes))


@st.cache_data(show_spinner=False)
def scan_cached(file_key: str, _pages):
    """Quick scan, cached per file (the leading underscore skips hashing the pages)."""
    return scan_document(_pages)


@st.cache_data(ttl=15, show_spinner=False)
def ollama_info():
    """Return (status, installed_models). Status is 'ready', 'missing' or 'offline'."""
    base = OLLAMA_CHAT_URL.rsplit("/api/", 1)[0]
    try:
        r = requests.get(f"{base}/api/tags", timeout=1.5)
        r.raise_for_status()
        names = [m.get("name", "") for m in r.json().get("models", [])]
    except (requests.exceptions.RequestException, ValueError):
        return "offline", []
    usable = sorted(n for n in names if "embed" not in n.lower())
    return ("ready" if usable else "missing"), usable


# --------------------------------------------------------------------------- #
# Callbacks
# --------------------------------------------------------------------------- #
def use_sample_question(question: str):
    st.session_state["question"] = question


def open_sample():
    st.session_state["use_sample"] = True


def close_sample():
    st.session_state["use_sample"] = False


def clear_history():
    st.session_state["history"] = []
    st.session_state.pop("result", None)


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
def sidebar(status: str, models: list[str]) -> str:
    """Draw the sidebar and return the model name to use."""
    chosen = MODEL
    with st.sidebar:
        st.markdown("### Local model")
        if status == "ready":
            default = next((i for i, n in enumerate(models) if n == MODEL or n.split(":")[0] == MODEL), 0)
            chosen = st.selectbox("Model", models, index=default, key="model")
            st.caption("Larger models are slower but usually read contracts more carefully.")
        elif status == "missing":
            st.error("Ollama is running, but no model is installed.")
            st.code(f"ollama pull {MODEL}", language="bash")
        else:
            st.error("Ollama is not running. Start it, then reload this page.")
            st.code("ollama serve", language="bash")
        st.markdown("### How answers are checked")
        st.caption(
            "After the model answers, LegalLens searches your PDF for the quoted clause. "
            "If the wording is not there, the answer is flagged as unverified."
        )
    return chosen


# --------------------------------------------------------------------------- #
# Result rendering
# --------------------------------------------------------------------------- #
def render_result(result: dict, show_excerpts: bool = True):
    kind = result["kind"]

    if kind == "rejected":
        st.warning("That question is not about this document. Ask about its clauses, parties, dates, money or risks.")
        return

    if kind == "not_found":
        st.info("This document does not seem to answer that. Nothing relevant turned up in the parts the model read.")
    else:
        sections = parse_answer(result["answer"])
        if sections is None:
            st.markdown(md_safe(result["answer"]))
        else:
            level, why = parse_risk(sections["risk level"])
            if level:
                st.markdown(verdict_html(level, why), unsafe_allow_html=True)
            st.markdown(md_safe(sections["analysis"]))
            quotes = clause_quotes(sections["relevant clause"])
            if quotes:
                st.markdown(evidence_html(quotes, result["grounded"], result["quote_pages"]), unsafe_allow_html=True)

    for w in result["warnings"]:
        st.warning(w)

    if show_excerpts:
        with st.expander("What the model read"):
            for c in result["excerpts"]:
                st.caption(f"Page {c['page']}")
                st.text(c["text"])


# --------------------------------------------------------------------------- #
# Tabs
# --------------------------------------------------------------------------- #
def tab_ask(pages: list[dict], model: str):
    st.text_input(
        "Your question",
        key="question",
        placeholder="Leave blank for a full triage of the document",
        label_visibility="collapsed",
    )
    cols = st.columns(len(SAMPLES))
    for col, (label, q) in zip(cols, SAMPLES.items()):
        col.button(label, key=f"sample_{label}", on_click=use_sample_question, args=(q,))

    question = st.session_state.get("question", "").strip()
    if st.button("Answer question" if question else "Run full triage", type="primary"):
        try:
            with st.spinner(f"Reading the contract with {model}..."):
                result = analyze_legal_text(pages, question, model=model)
            st.session_state["result"] = result
            if result["kind"] in ("ok", "not_found"):
                history = st.session_state.setdefault("history", [])
                history.append({
                    "question": question or "Full triage",
                    "result": result,
                    "time": datetime.now().strftime("%H:%M"),
                })
                del history[:-MAX_HISTORY]
            # Jump the viewer to the page where the quote was found
            if result["kind"] == "ok" and result["quote_pages"]:
                st.session_state["view_page"] = result["quote_pages"][0]
        except AIError as e:
            st.session_state.pop("result", None)
            st.error(str(e))

    result = st.session_state.get("result")
    if result:
        render_result(result)


def tab_scan(scan: dict):
    st.caption(
        "Found by keyword matching, with no AI involved. It is instant and repeatable, "
        "but it only spots wording, not meaning. Use it as a checklist of where to look."
    )
    findings = scan["findings"]
    if findings:
        high = sum(f["severity"] == "high" for f in findings)
        st.markdown(f"**{high} topic{'s' if high != 1 else ''} to look at closely**, "
                    f"{len(findings) - high} more worth a read.")
        st.markdown(scan_html(findings), unsafe_allow_html=True)
    else:
        st.info("No common red-flag wording found.")

    facts = facts_html(scan["facts"])
    if facts:
        st.markdown("**Key facts**")
        st.markdown(facts, unsafe_allow_html=True)


def tab_report(filename: str, pages: list[dict], scan: dict, model: str):
    history = st.session_state.get("history", [])

    st.markdown("**Download a report**")
    st.caption("Includes the quick scan and every question you asked in this session.")
    base = Path(filename).stem
    md = build_markdown_report(filename, len(pages), scan, history, model)
    html = build_html_report(filename, len(pages), scan, history, model)
    c1, c2 = st.columns(2)
    c1.download_button("Markdown (.md)", md, file_name=f"{base}-legallens.md", mime="text/markdown")
    c2.download_button("Web page (.html)", html, file_name=f"{base}-legallens.html", mime="text/html")
    st.caption("To get a PDF, open the .html file in your browser, choose Print, then Save as PDF.")

    st.markdown("**This session**")
    if not history:
        st.info("Questions you ask will be listed here.")
        return
    for h in reversed(history):
        label = h["question"] if len(h["question"]) <= 70 else h["question"][:67] + "..."
        with st.expander(f"{label}  ({h['time']})"):
            render_result(h["result"], show_excerpts=False)
    st.button("Clear history", on_click=clear_history)


# --------------------------------------------------------------------------- #
# Document viewer and workspace
# --------------------------------------------------------------------------- #
def show_document(pages: list[dict]):
    st.subheader("Contract")

    # Highlight the verified quote in the document text
    fragments = []
    result = st.session_state.get("result")
    if result and result["kind"] == "ok" and result["grounded"] is True:
        sections = parse_answer(result["answer"])
        if sections:
            fragments = highlight_fragments(clause_quotes(sections["relevant clause"]))

    options = ["All pages"] + [p["page"] for p in pages]
    selected = st.selectbox(
        "Page",
        options,
        key="view_page",
        format_func=lambda x: x if isinstance(x, str) else f"Page {x}",
        label_visibility="collapsed",
    )
    st.markdown(document_html(pages, selected, fragments), unsafe_allow_html=True)


def workspace(pages: list[dict], filename: str, file_key: str, model: str):
    chars = sum(len(p["text"]) for p in pages)
    st.markdown(chips_html(f"\U0001F4C4 {filename}", f"{len(pages)} pages", f"{chars:,} characters"), unsafe_allow_html=True)

    blank = [p["page"] for p in pages if not p["text"]]
    if blank:
        st.warning(
            f"No text could be read from page(s) {', '.join(map(str, blank))}. "
            "They may be scanned images, so they are left out of the analysis."
        )

    scan = scan_cached(file_key, pages)
    left, right = st.columns([1.1, 1], gap="large")
    # Right column first: an analysis may change which page the viewer shows
    with right:
        t_ask, t_scan, t_report = st.tabs(["Ask", "Quick scan", "Report"])
        with t_ask:
            tab_ask(pages, model)
        with t_scan:
            tab_scan(scan)
        with t_report:
            tab_report(filename, pages, scan, model)
    with left:
        show_document(pages)

    st.caption("LegalLens is an AI triage aid, not legal advice. Have a qualified lawyer check anything important.")


# --------------------------------------------------------------------------- #
def main():
    st.set_page_config(page_title="LegalLens", page_icon="\u2696\ufe0f", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)

    status, models = ollama_info()
    model = sidebar(status, models)
    st.markdown(hero_html(status, model), unsafe_allow_html=True)

    uploaded = st.file_uploader("Contract PDF", type=["pdf"])
    if uploaded is not None:
        st.session_state["use_sample"] = False
        name, data = uploaded.name, uploaded.getvalue()
    elif st.session_state.get("use_sample") and SAMPLE_PATH.exists():
        name, data = SAMPLE_PATH.name, SAMPLE_PATH.read_bytes()
        st.button("Close the sample", on_click=close_sample)
    else:
        if SAMPLE_PATH.exists():
            st.button("No contract handy? Try the sample", on_click=open_sample)
        st.markdown(steps_html(), unsafe_allow_html=True)
        return

    # New file: clear the old result and history, and reset the page viewer
    file_key = f"{name}:{len(data)}"
    if st.session_state.get("file_key") != file_key:
        st.session_state.update(file_key=file_key, view_page="All pages", history=[])
        st.session_state.pop("result", None)

    try:
        with st.spinner("Extracting text..."):
            pages = load_pages(data)
    except DocumentError as e:
        st.error(str(e))
        return

    workspace(pages, name, file_key, model)


if __name__ == "__main__":
    main()
