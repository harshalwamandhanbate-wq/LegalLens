"""Run LegalLens over a sample of CUAD contracts and report how well it does.

Usage (from the LegalLens folder, with Ollama running):

    python evaluate_cuad.py --pdf-dir datasets/cuad/full_contract_pdf \
                            --labels datasets/cuad/master_clauses.csv --limit 20

Outputs (in --out, default "results"):
    cuad_results.csv   one row per (contract, question)
    cuad_summary.md    headline numbers, ready to paste into a README or slides

What is measured
  - Quote check: is the clause the model quoted really in the PDF? (grounding)
  - Clause finding vs expert labels: when CUAD says a clause exists, did the
    model return a verified quote? When CUAD says it does not, did the model
    correctly say "not found"?
These are commercial contracts, so the numbers say nothing about rental or
employment documents. CUAD is CC BY 4.0: cite the NeurIPS 2021 paper.
"""
import argparse
import csv
import random
import re
import sys
import time
from pathlib import Path

from ai_agent import MODEL, AIError, analyze_legal_text
from doc_parser import DocumentError, extract_pages
from ui_helpers import parse_answer, parse_risk

# (id, question asked, CUAD category used to look up the expert label)
QUESTIONS = [
    ("governing_law", "What law governs this contract?", "Governing Law"),
    ("non_compete", "Is there a non-compete clause that restricts either party?", "Non-Compete"),
    ("termination", "Can either party terminate this contract for convenience, without cause?", "Termination For Convenience"),
    ("renewal", "What is the renewal term of this contract?", "Renewal Term"),
    ("liability_cap", "Is there a cap on liability or damages?", "Cap On Liability"),
    ("anti_assignment", "Can the contract be assigned to someone else without consent?", "Anti-Assignment"),
]


def norm_name(name: str) -> str:
    """'My_Contract.pdf' and 'my contract.txt' both become 'mycontract'."""
    return re.sub(r"[^a-z0-9]", "", Path(name).stem.lower())


def load_labels(path: Path | None) -> dict[str, dict]:
    """Read CUAD master_clauses.csv into {normalised filename: row with lowercase keys}."""
    if not path:
        return {}
    labels = {}
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        for row in csv.DictReader(f):
            row = {(k or "").strip().lower(): (v or "") for k, v in row.items()}
            fname = row.get("filename") or row.get("document name") or ""
            if fname:
                labels[norm_name(fname)] = row
    return labels


def clause_present(row: dict | None, category: str):
    """True / False from the expert label, or None if the label is unavailable."""
    if not row:
        return None
    value = row.get(f"{category}-answer".lower())
    if value is None:
        return None
    value = value.strip()
    return bool(value) and value != "[]"


def pick_pdfs(pdf_dir: Path, limit: int, seed: int) -> list[Path]:
    pdfs = sorted(pdf_dir.rglob("*.pdf"))
    if not pdfs:
        sys.exit(f"No PDFs found in {pdf_dir}")
    random.Random(seed).shuffle(pdfs)
    return sorted(pdfs[:limit])


def pct(n: int, d: int) -> str:
    return f"{100 * n / d:.0f}% ({n}/{d})" if d else "n/a"


def run(args) -> list[dict]:
    labels = load_labels(Path(args.labels)) if args.labels else {}
    if args.labels and not labels:
        print("Warning: no rows read from the labels file, label comparison is skipped.")

    pdfs = pick_pdfs(Path(args.pdf_dir), args.limit, args.seed)
    print(f"Evaluating {len(pdfs)} contracts x {len(QUESTIONS)} questions with {args.model}\n")

    rows = []
    for i, pdf in enumerate(pdfs, start=1):
        try:
            pages = extract_pages(pdf)
        except DocumentError as e:
            print(f"[{i}/{len(pdfs)}] SKIP {pdf.name}: {e}")
            continue
        label_row = labels.get(norm_name(pdf.name))
        print(f"[{i}/{len(pdfs)}] {pdf.name} ({len(pages)} pages)")

        for qid, question, category in QUESTIONS:
            start = time.time()
            row = {
                "contract": pdf.name, "pages": len(pages), "question": qid,
                "kind": "", "risk": "", "grounded": "", "quote_pages": "",
                "truncated": "", "seconds": "", "label_has_clause": "", "agrees": "", "error": "",
            }
            try:
                result = analyze_legal_text(pages, question, model=args.model)
            except AIError as e:
                if "Cannot reach Ollama" in str(e):
                    sys.exit(f"\n{e}")
                row["error"] = str(e)
                rows.append(row)
                print(f"    {qid}: ERROR {e}")
                continue

            row["seconds"] = round(time.time() - start, 1)
            row["kind"] = result["kind"]
            row["grounded"] = result["grounded"]
            row["quote_pages"] = " ".join(map(str, result["quote_pages"]))
            row["truncated"] = any("longer than the model" in w for w in result["warnings"])
            if result["kind"] == "ok":
                sections = parse_answer(result["answer"])
                if sections:
                    row["risk"] = parse_risk(sections["risk level"])[0] or ""

            expected = clause_present(label_row, category)
            if expected is not None:
                found = result["kind"] == "ok" and result["grounded"] is True
                row["label_has_clause"] = expected
                row["agrees"] = (found == expected)

            rows.append(row)
            print(f"    {qid}: {result['kind']}, quote {result['grounded']}, {row['seconds']}s")
    return rows


def summarise(rows: list[dict], model: str, n_contracts: int) -> str:
    ok_rows = [r for r in rows if not r["error"]]
    errors = len(rows) - len(ok_rows)
    kinds = {k: sum(r["kind"] == k for r in ok_rows) for k in ("ok", "not_found", "rejected")}
    verified = sum(r["grounded"] is True for r in ok_rows)
    unverified = sum(r["grounded"] is False for r in ok_rows)
    unchecked = sum(r["kind"] == "ok" and r["grounded"] is None for r in ok_rows)
    truncated = sum(r["truncated"] is True for r in ok_rows)
    secs = [r["seconds"] for r in ok_rows if r["seconds"] != ""]
    labelled = [r for r in ok_rows if r["agrees"] != ""]
    agree = sum(r["agrees"] is True for r in labelled)

    out = [
        "# LegalLens evaluation on CUAD", "",
        f"- Model: `{model}`",
        f"- Contracts evaluated: {n_contracts}",
        f"- Questions per contract: {len(QUESTIONS)}",
        f"- Runs: {len(rows)} ({errors} errors)", "",
        "## Headline numbers", "",
        "| Metric | Result |", "|---|---|",
        f"| Answers with a quoted clause that was **verified** in the PDF | {pct(verified, verified + unverified)} |",
        f"| Answers with a quote **not found** in the PDF (possible hallucination) | {pct(unverified, verified + unverified)} |",
        f"| Answers where the quote could not be checked | {unchecked} |",
        f'| Answered "not found" | {pct(kinds["not_found"], len(ok_rows))} |',
        f"| Wrongly rejected as out of scope | {pct(kinds['rejected'], len(ok_rows))} |",
        f"| Runs where the contract was longer than the model window | {pct(truncated, len(ok_rows))} |",
        f"| Agreement with CUAD expert labels | {pct(agree, len(labelled))} |",
        f"| Average time per question | {sum(secs) / len(secs):.1f} s |" if secs else "| Average time per question | n/a |",
        "", "## By question", "",
        "| Question | Verified quotes | Agrees with label |", "|---|---|---|",
    ]
    for qid, _, _ in QUESTIONS:
        q_rows = [r for r in ok_rows if r["question"] == qid]
        q_ver = sum(r["grounded"] is True for r in q_rows)
        q_chk = sum(r["grounded"] in (True, False) for r in q_rows)
        q_lab = [r for r in q_rows if r["agrees"] != ""]
        q_agree = sum(r["agrees"] is True for r in q_lab)
        out.append(f"| {qid} | {pct(q_ver, q_chk)} | {pct(q_agree, len(q_lab))} |")

    out += [
        "", "## How to read this", "",
        "- A verified quote proves the wording exists in the contract, not that the model interpreted it correctly.",
        '- "Agreement with labels" counts a hit when CUAD marks a clause as present and the model returns a verified quote, '
        'or CUAD marks it absent and the model says "not found". It is a rough measure: the model may find a related '
        "clause that the expert did not label.",
        "- Long CUAD contracts exceed the model window, so retrieval may miss the right passage.",
        "- CUAD covers commercial contracts. Do not present these numbers as proof for rental or employment documents.",
        "- Data: CUAD, CC BY 4.0, Hendrycks et al., NeurIPS 2021.",
    ]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Evaluate LegalLens on CUAD contracts.")
    ap.add_argument("--pdf-dir", required=True, help="Folder with CUAD PDFs (full_contract_pdf)")
    ap.add_argument("--labels", help="Path to CUAD master_clauses.csv (optional)")
    ap.add_argument("--limit", type=int, default=20, help="How many contracts to test (default 20)")
    ap.add_argument("--model", default=MODEL, help=f"Ollama model (default {MODEL})")
    ap.add_argument("--seed", type=int, default=42, help="Seed for picking the same contracts each run")
    ap.add_argument("--out", default="results", help="Output folder (default results)")
    args = ap.parse_args()

    rows = run(args)
    if not rows:
        sys.exit("Nothing was evaluated.")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "cuad_results.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary = summarise(rows, args.model, len({r["contract"] for r in rows}))
    (out_dir / "cuad_summary.md").write_text(summary, encoding="utf-8")
    print("\n" + summary)
    print(f"Saved: {csv_path} and {out_dir / 'cuad_summary.md'}")


if __name__ == "__main__":
    main()
