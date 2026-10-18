import io
import re
import difflib
from pypdf import PdfReader

# 1. Ambiguous / Vague Phrasing Library (Criterion 3 & 6)
AMBIGUOUS_PHRASES = {
    "at sole discretion": "Allows one party to make unilateral decisions without objective criteria.",
    "reasonable notice": "Does not define an exact number of days or hours.",
    "as deemed fit": "Subjective standard that creates enforcement ambiguity.",
    "from time to time": "Allows terms or fees to change unpredictably.",
    "without prior notice": "Removes advance warning before penalties or termination.",
    "as soon as practicable": "Vague deadline that can lead to dispute over delays.",
    "material breach": "Unclear threshold unless 'material' is explicitly defined in the text.",
    "fair wear and tear": "Often disputed during security deposit deductions unless itemized.",
    "any other charges": "Open-ended financial obligation without a clear cap."
}

# 2. Unusual / High-Risk Trap Clauses ({OPT} Unusual clause detection)
UNUSUAL_CLAUSE_PATTERNS = [
    ("Unilateral Modification Trap", r"(?i)\b(change|modify|amend)\b.{0,40}\b(without notice|at any time|sole discretion)\b"),
    ("Waiver of Legal Recourse", r"(?i)\b(waive|relinquish|forfeit)\b.{0,40}\b(right to sue|legal recourse|court|dispute)\b"),
    ("100% Forfeiture Penalty", r"(?i)\b(forfeit|lose)\b.{0,30}\b(entire|100%|full)\b.{0,30}\b(deposit|salary|payment)\b"),
    ("Extreme Non-Compete Restriction", r"(?i)\b(not to work|non-compete|competitor)\b.{0,50}\b([3-9]|10)\s?years\b"),
    ("Automatic Renewal Without Notice", r"(?i)\b(automatically renew|auto-renew)\b.{0,40}\b(unless|without)\b")
]

# 3. Standard Protective Clauses Audit ({OPT} Missing clause detection)
ESSENTIAL_CLAUSES = {
    "Payment / Consideration / Rent": [r"\brent\b", r"\bsalary\b", r"\bfee\b", r"\bpayment\b", r"\bconsideration\b", r"\bremuneration\b"],
    "Termination & Notice Period": [r"\bterminat", r"\bnotice period\b", r"\bcancellation\b", r"\bexit\b"],
    "Security Deposit / Refund Rules": [r"\bdeposit\b", r"\brefund\b", r"\breimbursement\b", r"\bescrow\b"],
    "Liability & Indemnification": [r"\bliabilit", r"\bindemnif", r"\bdamages\b", r"\bhold harmless\b"],
    "Dispute Resolution & Jurisdiction": [r"\blegislation\b", r"\bjurisdiction\b", r"\barbitration\b", r"\bcourt\b", r"\bgoverning law\b"],
    "Force Majeure / Unforeseen Events": [r"\bforce majeure\b", r"\bact of god\b", r"\bpandemic\b", r"\bnatural disaster\b"],
    "Confidentiality / Privacy": [r"\bconfidential", r"\bnon-disclosure\b", r"\bproprietary\b"]
}

# 4. Jurisdiction Detection Patterns ({OPT} Jurisdiction-aware warnings)
JURISDICTION_PATTERNS = {
    "India (General / Statutory Mention)": r"(?i)\b(india|indian contract act|arbitration and conciliation act|rupees|inr|₹|bengaluru|karnataka|mumbai|delhi|hyderabad|chennai|dharwad)\b",
    "United States / Delaware / NY": r"(?i)\b(delaware|new york|california|united states|u\.s\.a\.|usd)\b",
    "United Kingdom / English Law": r"(?i)\b(england and wales|united kingdom|london|gbp)\b"
}


def extract_document_data(uploaded_file):
    """
    Processes PDF/TXT strictly in memory (io.BytesIO) so ZERO temporary files are written to disk (Gate L9).
    """
    filename = getattr(uploaded_file, "name", "document.pdf").lower()
    pages_data = []

    try:
        raw_bytes = uploaded_file.read()
        uploaded_file.seek(0)

        if not raw_bytes:
            return {"error": "The uploaded file is completely empty (0 bytes).", "pages": []}

        if filename.endswith(".txt") or filename.endswith(".md"):
            text = raw_bytes.decode("utf-8", errors="replace")
            if not text.strip():
                return {"error": "The text file contains only whitespace.", "pages": []}
            for idx in range(0, len(text), 2200):
                pages_data.append({
                    "page_number": (idx // 2200) + 1,
                    "text": text[idx:idx + 2200].strip()
                })
            return {"error": None, "pages": pages_data}

        # Read PDF from RAM buffer (Zero disk footprints)
        pdf_stream = io.BytesIO(raw_bytes)
        reader = PdfReader(pdf_stream)

        if reader.is_encrypted:
            return {"error": "Encrypted/Password-protected PDF detected. Please upload an unlocked document.", "pages": []}

        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            # Clean excessive whitespace while preserving paragraph structure
            cleaned_text = re.sub(r"[ \t]+", " ", page_text).strip()
            if cleaned_text:
                pages_data.append({
                    "page_number": page_num + 1,
                    "text": cleaned_text
                })

        if not pages_data:
            return {
                "error": "No digital text layer found. This PDF appears to be a scanned image. Enable Local OCR (Tesseract) or upload a digital text PDF.",
                "pages": []
            }

        return {"error": None, "pages": pages_data}

    except Exception as e:
        return {"error": f"Malformed file structure caught safely: {str(e)}", "pages": []}


def extract_parties(full_text):
    """Extracts contracting party roles and names from preamble patterns."""
    parties_found = []
    role_patterns = [
        (r"(?i)\b(?:between|by and between)\s+([A-Z][A-Za-z0-9\s,\.&]{2,50}?)\s+(?:\(|hereinafter|and\b)", "Primary Party"),
        (r"(?i)\b(?:landlord|lessor|owner)[:\s-]+([A-Z][A-Za-z\s\.]{2,40})", "Landlord / Lessor"),
        (r"(?i)\b(?:tenant|lessee|occupant)[:\s-]+([A-Z][A-Za-z\s\.]{2,40})", "Tenant / Lessee"),
        (r"(?i)\b(?:employer|company|client)[:\s-]+([A-Z][A-Za-z0-9\s\.,&]{2,40})", "Employer / Client"),
        (r"(?i)\b(?:employee|contractor|consultant|vendor)[:\s-]+([A-Z][A-Za-z\s\.]{2,40})", "Employee / Contractor")
    ]
    for pat, label in role_patterns:
        for match in re.finditer(pat, full_text[:2500]):
            name = match.group(1).strip(" ,.-()")
            if len(name) > 2:
                parties_found.append(f"{label}: {name}")

    # Detect generic roles if explicit names aren't formatted cleanly
    if not parties_found:
        roles = []
        for r_word in ["Landlord", "Tenant", "Lessor", "Lessee", "Employer", "Employee", "Client", "Contractor", "Vendor", "Licensor", "Licensee"]:
            if re.search(rf"\b{r_word}\b", full_text, re.IGNORECASE):
                roles.append(r_word)
        if roles:
            parties_found.append("Detected Roles: " + ", ".join(sorted(set(roles))))
        else:
            parties_found.append("Parties not explicitly labeled in standard preamble format")

    return parties_found[:6]


def detect_conflicting_clauses(full_text):
    """
    Detects potential internal contradictions inside the document ({OPT} Conflicting clause detection).
    """
    conflicts = []
    lower = full_text.lower()

    # Check 1: Specific Notice Period vs "Without Prior Notice"
    has_notice_days = re.search(r"\b(\d+)\s?(?:days|months)\s+(?:prior\s+)?(?:written\s+)?notice\b", lower)
    has_no_notice = "without prior notice" in lower or "without notice" in lower
    if has_notice_days and has_no_notice:
        conflicts.append(
            f"Contradictory Notice Rules: Document specifies '{has_notice_days.group(0)}' in one section, "
            "but also permits action 'without prior notice' in another section."
        )

    # Check 2: Fixed Lock-in vs Terminate Anytime
    has_lockin = "lock-in period" in lower or "non-cancellable" in lower
    has_anytime = "terminate at any time" in lower or "terminate at will" in lower
    if has_lockin and has_anytime:
        conflicts.append(
            "Conflicting Termination Rights: Document mentions both a 'lock-in / non-cancellable period' "
            "and a right to 'terminate at any time'."
        )

    # Check 3: Full Refund vs Non-Refundable Deposit
    if ("refundable deposit" in lower or "full refund" in lower) and "non-refundable" in lower:
        conflicts.append(
            "Conflicting Deposit Terms: Document contains both 'refundable' and 'non-refundable' provisions."
        )

    return conflicts


def extract_structured_metadata(full_text):
    """
    Comprehensive local audit: Parties, Money, Deadlines, Ambiguities, Missing Clauses, Conflicts, Unusual Clauses, and Jurisdiction.
    """
    parties = extract_parties(full_text)

    money_matches = list(set(re.findall(
        r"(?:Rs\.?|INR|\$|₹)\s?[\d,]+(?:\.\d{1,2})?|\b[\d,]+\s?(?:rupees|dollars|lakhs|thousand|percent|%)\b",
        full_text, re.IGNORECASE
    )))[:15]

    time_matches = list(set(re.findall(
        r"\b\d+\s?(?:days|months|years|weeks|hours)\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        full_text, re.IGNORECASE
    )))[:15]

    lower_text = full_text.lower()
    detected_ambiguities = []
    for phrase, reason in AMBIGUOUS_PHRASES.items():
        if phrase in lower_text:
            detected_ambiguities.append({"phrase": phrase, "reason": reason})

    unusual_flags = []
    for title, pat in UNUSUAL_CLAUSE_PATTERNS:
        m = re.search(pat, full_text)
        if m:
            unusual_flags.append(f"{title}: \"...{m.group(0).strip()}...\"")

    conflicts = detect_conflicting_clauses(full_text)

    clause_audit = {}
    for clause_name, patterns in ESSENTIAL_CLAUSES.items():
        found = any(re.search(pat, lower_text) for pat in patterns)
        clause_audit[clause_name] = "Present" if found else "MISSING / SILENT"

    detected_jurisdictions = []
    for j_name, j_pat in JURISDICTION_PATTERNS.items():
        if re.search(j_pat, full_text):
            detected_jurisdictions.append(j_name)
    if not detected_jurisdictions:
        detected_jurisdictions.append("Unspecified Jurisdiction (Governing law not explicitly named)")

    return {
        "parties": parties,
        "monetary_terms": money_matches,
        "timeframes_and_dates": time_matches,
        "ambiguous_phrases": detected_ambiguities,
        "unusual_clauses": unusual_flags,
        "conflicts": conflicts,
        "clause_audit": clause_audit,
        "jurisdictions": detected_jurisdictions
    }


def compare_two_clauses(text_a, text_b):
    """
    Generates both plain-text diff markers and color-coded HTML diff for UI visualization.
    """
    words_a = text_a.split()
    words_b = text_b.split()
    matcher = difflib.SequenceMatcher(None, words_a, words_b)

    plain_diff = []
    html_diff = []
    added_count = 0
    removed_count = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            seg = " ".join(words_a[i1:i2])
            plain_diff.append(seg)
            html_diff.append(seg)
        elif tag == "delete":
            seg = " ".join(words_a[i1:i2])
            removed_count += (i2 - i1)
            plain_diff.append(f"[-REMOVED: {seg}-]")
            html_diff.append(f"<span style='background-color:#ffcccc;color:#990000;text-decoration:line-through;padding:2px 4px;border-radius:3px;'>{seg}</span>")
        elif tag == "insert":
            seg = " ".join(words_b[j1:j2])
            added_count += (j2 - j1)
            plain_diff.append(f"[+ADDED: {seg}+]")
            html_diff.append(f"<span style='background-color:#ccffcc;color:#006600;font-weight:bold;padding:2px 4px;border-radius:3px;'>{seg}</span>")
        elif tag == "replace":
            seg_a = " ".join(words_a[i1:i2])
            seg_b = " ".join(words_b[j1:j2])
            removed_count += (i2 - i1)
            added_count += (j2 - j1)
            plain_diff.append(f"[-REMOVED: {seg_a}-] [+ADDED: {seg_b}+]")
            html_diff.append(
                f"<span style='background-color:#ffcccc;color:#990000;text-decoration:line-through;padding:2px 4px;border-radius:3px;'>{seg_a}</span> "
                f"<span style='background-color:#ccffcc;color:#006600;font-weight:bold;padding:2px 4px;border-radius:3px;'>{seg_b}</span>"
            )

    return " ".join(plain_diff), " ".join(html_diff), added_count, removed_count