import re
import difflib
from pypdf import PdfReader

# Vague or ambiguous legal phrases to flag automatically (Criterion 3 & 6)
AMBIGUOUS_PHRASES = [
    "at sole discretion", "reasonable notice", "as deemed fit",
    "from time to time", "without prior notice", "as soon as practicable",
    "material breach", "unforeseen circumstances", "fair wear and tear",
    "any other charges", "solely determined by"
]

# Essential clauses expected in standard agreements ({OPT} Missing clause detection)
ESSENTIAL_CLAUSES = {
    "Payment / Consideration / Rent": [r"\brent\b", r"\bsalary\b", r"\bfee\b", r"\bpayment\b", r"\bconsideration\b"],
    "Termination & Notice Period": [r"\bterminat", r"\bnotice period\b", r"\bcancellation\b"],
    "Security Deposit / Refund Rules": [r"\bdeposit\b", r"\brefund\b", r"\breimbursement\b"],
    "Liability & Indemnification": [r"\bliabilit", r"\bindemnif", r"\bdamages\b"],
    "Dispute Resolution & Jurisdiction": [r"\biegislation\b", r"\bjurisdiction\b", r"\barbitration\b", r"\bcourt\b", r"\bgoverning law\b"],
    "Force Majeure / Unforeseen Events": [r"\bforce majeure\b", r"\bact of god\b"]
}

def extract_document_data(uploaded_file):
    """
    Ingests PDF or TXT locally. Handles malformed, encrypted, or scanned (empty) files gracefully.
    """
    filename = getattr(uploaded_file, "name", "document.pdf").lower()
    pages_data = []

    try:
        if filename.endswith(".txt") or filename.endswith(".md"):
            raw_bytes = uploaded_file.read()
            text = raw_bytes.decode("utf-8", errors="replace")
            uploaded_file.seek(0)
            if not text.strip():
                return {"error": "The uploaded text file is empty.", "pages": []}
            # Split plain text into logical page blocks of ~2500 chars
            for idx in range(0, len(text), 2500):
                pages_data.append({
                    "page_number": (idx // 2500) + 1,
                    "text": text[idx:idx + 2500].strip()
                })
            return {"error": None, "pages": pages_data}

        # Handle PDF files
        reader = PdfReader(uploaded_file)
        if reader.is_encrypted:
            return {"error": "This PDF is password-protected/encrypted. Please upload an unlocked PDF.", "pages": []}

        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages_data.append({
                    "page_number": page_num + 1,
                    "text": page_text.strip()
                })

        if not pages_data:
            return {
                "error": "No digital text layer detected. This appears to be a scanned image PDF. Local OCR is required to read image-only scans.",
                "pages": []
            }

        return {"error": None, "pages": pages_data}

    except Exception as e:
        return {"error": f"Malformed or unreadable file format: {str(e)}", "pages": []}


def extract_structured_metadata(full_text):
    """
    Automatically extracts Monetary Amounts, Dates/Durations, Ambiguous Terms, and Missing Clauses.
    """
    # 1. Monetary figures (INR, Rs, $, numbers with currency words)
    money_matches = list(set(re.findall(
        r"(?:Rs\.?|INR|\$|₹)\s?[\d,]+(?:\.\d{1,2})?|\b[\d,]+\s?(?:rupees|dollars|lakhs|thousand)\b",
        full_text, re.IGNORECASE
    )))[:12]

    # 2. Timeframes, Deadlines & Notice Periods
    time_matches = list(set(re.findall(
        r"\b\d+\s?(?:days|months|years|weeks|hours)\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        full_text, re.IGNORECASE
    )))[:12]

    # 3. Ambiguous / Vague Phrasing
    detected_ambiguities = []
    lower_text = full_text.lower()
    for phrase in AMBIGUOUS_PHRASES:
        if phrase in lower_text:
            detected_ambiguities.append(phrase)

    # 4. Missing vs Present Standard Clauses
    clause_audit = {}
    for clause_name, patterns in ESSENTIAL_CLAUSES.items():
        found = any(re.search(pat, lower_text) for pat in patterns)
        clause_audit[clause_name] = "Present" if found else "MISSING / SILENT"

    return {
        "monetary_terms": money_matches,
        "timeframes_and_dates": time_matches,
        "ambiguous_phrases": detected_ambiguities,
        "clause_audit": clause_audit
    }


def compare_two_clauses(text_a, text_b):
    """
    Generates a clean word-by-word comparison between two contract versions.
    """
    words_a = text_a.split()
    words_b = text_b.split()
    matcher = difflib.SequenceMatcher(None, words_a, words_b)
    
    diff_output = []
    added_count = 0
    removed_count = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            diff_output.append(" ".join(words_a[i1:i2]))
        elif tag == "delete":
            removed_count += (i2 - i1)
            diff_output.append(f"[-REMOVED: {' '.join(words_a[i1:i2])}-]")
        elif tag == "insert":
            added_count += (j2 - j1)
            diff_output.append(f"[+ADDED: {' '.join(words_b[j1:j2])}+]")
        elif tag == "replace":
            removed_count += (i2 - i1)
            added_count += (j2 - j1)
            diff_output.append(f"[-REMOVED: {' '.join(words_a[i1:i2])}-] [+ADDED: {' '.join(words_b[j1:j2])}+]")

    return " ".join(diff_output), added_count, removed_count