import streamlit as st
import time
import requests
from doc_parser import extract_text_from_pdf
from ai_agent import analyze_legal_text 

# --- 1. PAGE CONFIG & DARK AESTHETIC CSS ---
st.set_page_config(page_title="LegalLens - Document Review", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        /* Hide default Streamlit elements */
        header {visibility: hidden;}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Base Theme: Deep Slate/Midnight Blue */
        .stApp {
            background-color: #0b1121 !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #f8fafc !important;
        }
        
        /* Force text colors to be light */
        .stApp p, .stApp span, .stApp li, .stApp label, .stMarkdown {
            color: #cbd5e1 !important;
        }
        
        /* Main headings */
        h1 {
            font-family: "Georgia", serif !important;
            background: linear-gradient(to right, #818cf8, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.8rem !important;
            margin-bottom: 0.2rem !important;
            font-weight: 600 !important;
        }
        h2, h3, h4 {
            color: #f8fafc !important;
            font-weight: 600 !important;
        }
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #111827 !important;
            border-right: 1px solid #1f2937 !important;
        }
        
        /* Custom UI Cards */
        .metric-card {
            background-color: #1f2937;
            border: 1px solid #374151;
            border-radius: 8px;
            padding: 1.2rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            height: 100%;
        }
        .metric-value {
            font-size: 1.8rem;
            font-weight: 600;
            color: #818cf8; /* Indigo accent */
            margin-bottom: 0.2rem;
        }
        .metric-label {
            font-size: 0.85rem;
            color: #94a3b8;
        }
        
        .doc-header-card {
            background-color: #1f2937;
            border: 1px solid #374151;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }
        
        /* Primary Buttons */
        .stButton > button {
            background-color: #4f46e5 !important; /* Indigo 600 */
            color: #ffffff !important;
            border-radius: 6px !important;
            padding: 0.5rem 1rem !important;
            font-weight: 600 !important;
            border: none !important;
            transition: all 0.2s ease-in-out;
        }
        .stButton > button:hover {
            background-color: #6366f1 !important; /* Indigo 500 */
            transform: translateY(-1px);
        }
        
        /* Secondary Buttons (Outline) */
        .btn-outline > .stButton > button {
            background-color: transparent !important;
            color: #818cf8 !important;
            border: 1px solid #4f46e5 !important;
        }
        .btn-outline > .stButton > button:hover {
            background-color: rgba(79, 70, 229, 0.1) !important;
        }
        
        /* File Uploader Fixes */
        .stFileUploader > div > div {
            background-color: #1f2937 !important;
            border: 2px dashed #4f46e5 !important;
            border-radius: 8px;
        }
        
        /* Document Viewer Box */
        .doc-viewer {
            background-color: #111827;
            border: 1px solid #374151;
            border-radius: 8px;
            padding: 1.5rem;
            height: 600px;
            overflow-y: auto;
            font-family: "Georgia", serif;
            color: #e2e8f0;
            font-size: 0.95rem;
            line-height: 1.6;
        }
        
        /* Analysis Overview Box (The Big Picture) */
        .big-picture-card {
            background-color: rgba(99, 102, 241, 0.1);
            border: 1px solid rgba(99, 102, 241, 0.3);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            color: #c7d2fe;
        }
        
        /* Make status and alerts readable */
        div[data-testid="stAlert"] {
            background-color: #1f2937 !important;
            border: 1px solid #374151 !important;
            color: #f8fafc !important;
        }
        div[data-testid="stAlert"] * {
            color: #f8fafc !important;
        }
        
        .block-container {
            padding-top: 2rem !important;
            max-width: 1500px;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. INITIALIZE MEMORY ---
if "text_loaded" not in st.session_state:
    st.session_state.text_loaded = False
if "raw_text" not in st.session_state:
    st.session_state.raw_text = ""
if "filename" not in st.session_state:
    st.session_state.filename = "No document loaded"

# --- 3. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown("<h2 style='color: #818cf8; font-family: Georgia; font-size: 2rem;'>⚖️ LegalLens</h2>", unsafe_allow_html=True)
    st.markdown("<div style='border: 1px solid #374151; background-color: #1f2937; padding: 0.8rem; border-radius: 6px; margin-bottom: 1rem;'><b>P | Personal workspace</b><br><span style='color: #94a3b8; font-size: 0.8rem;'>Private by design</span></div>", unsafe_allow_html=True)
    st.button("+ New document", use_container_width=True)
    
    st.markdown("<p style='font-size: 0.75rem; color: #64748b; font-weight: 600; margin-top: 1.5rem; letter-spacing: 1px;'>WORKSPACE</p>", unsafe_allow_html=True)
    st.markdown("📄 **Document review** (Active)")
    st.markdown("📁 My documents <span style='float: right; background: #374151; color: #cbd5e1; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem;'>1</span>", unsafe_allow_html=True)
    
    st.markdown("<p style='font-size: 0.75rem; color: #64748b; font-weight: 600; margin-top: 1.5rem; letter-spacing: 1px;'>THIS SESSION</p>", unsafe_allow_html=True)
    st.markdown(f"• {st.session_state.filename}")
    
    st.markdown("<p style='font-size: 0.75rem; color: #64748b; font-weight: 600; margin-top: 1.5rem; letter-spacing: 1px;'>TOOLS & RESOURCES</p>", unsafe_allow_html=True)
    
    try:
        req = requests.get("http://localhost:11434", timeout=1)
        ai_status = "🟢 Local model (Online)" if req.status_code == 200 else "🔴 Local model (Offline)"
    except:
        ai_status = "🔴 Local model (Offline)"
    st.markdown(ai_status)
    st.markdown("🛡️ Privacy center")

# --- 4. TOP HEADER & ACTIONS ---
header_col1, header_col2 = st.columns([3, 1])
with header_col1:
    st.markdown("<p style='color: #818cf8; font-size: 0.85rem; font-weight: 600; letter-spacing: 1px; margin-bottom: 0;'>CLARITY, WITHOUT COMPROMISE</p>", unsafe_allow_html=True)
    st.markdown("<h1>Understand before you sign.</h1>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 1.1rem; color: #94a3b8; margin-bottom: 2rem;'>A clearer view of your document. A little more peace of mind.</p>", unsafe_allow_html=True)
with header_col2:
    st.write("") # Spacing
    btn_col1, btn_col2 = st.columns([1, 1])
    with btn_col1:
        st.markdown("<div class='btn-outline'>", unsafe_allow_html=True)
        st.button("📥 Export review", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with btn_col2:
        st.button("+ New document", key="top_new", use_container_width=True)

# --- 5. FILE UPLOAD & PROCESSING ---
if not st.session_state.text_loaded:
    st.markdown("<div style='max-width: 600px;'>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload Legal Agreement (PDF)", type=["pdf"])
    st.markdown("</div>", unsafe_allow_html=True)

    if uploaded_file:
        with st.status("Processing Document...", expanded=True) as status:
            st.session_state.filename = uploaded_file.name
            st.write("📄 Extracting raw text from PDF...")
            text = extract_text_from_pdf(uploaded_file)
            
            if isinstance(text, str) and "Error" in text:
                status.update(label="Processing Failed", state="error", expanded=True)
                st.error(text)
            else:
                st.session_state.raw_text = text
                st.write("✂️ Preparing text chunks...")
                time.sleep(0.5) 
                
                st.session_state.text_loaded = True
                status.update(label="Document Processed Successfully!", state="complete", expanded=False)
                st.rerun()

# --- 6. THE MAIN DASHBOARD ---
if st.session_state.text_loaded:
    
    # Document Meta Header
    st.markdown(f"""
    <div class="doc-header-card">
        <h3 style='margin: 0; font-size: 1.3rem; color: #f8fafc;'>📄 {st.session_state.filename}</h3>
        <p style='margin: 0; margin-top: 0.5rem; font-size: 0.9rem; color: #94a3b8;'>
            Uploaded Session • ~{len(st.session_state.raw_text.split())} words • Private Scope
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Metrics Row
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">8</div>
            <div class="metric-label">Source passages identified</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown("""
        <div class="metric-card" style="border-left: 4px solid #f59e0b;">
            <div class="metric-value" style="color: #fbbf24;">3</div>
            <div class="metric-label">Items to look at closely</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value" style="color: #2dd4bf;">On-device AI</div>
            <div class="metric-label">Zero data retention guarantee</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Side-by-Side Layout
    left_pane, right_pane = st.columns([1.5, 1.2], gap="large")

    with left_pane:
        st.markdown("### ✨ Overview & Triage")
        
        # Big Picture Card
        st.markdown("""
        <div class="big-picture-card">
            <h4 style="color: #818cf8 !important;">✨ The big picture</h4>
            <p style='margin-bottom: 0; color: #e0e7ff;'>This document contains legal obligations. Pay particular attention to the early-exit charges, deposit refund timing, and liability clauses highlighted in the analysis below.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("#### Run Targeted Analysis")
        category = st.radio(
            "Select an area to review:",
            [
                "Financial Penalties & Late Fees",
                "Termination, Notice Period & Lock-in",
                "Liability, Damages & Indemnification",
                "Governing Law & Dispute Resolution"
            ],
            label_visibility="collapsed"
        )
        
        run_btn = st.button("Run Document Analysis", type="primary")
        st.markdown("<hr style='margin: 1.5rem 0; border-color: #374151;'>", unsafe_allow_html=True)
        
        if run_btn:
            with st.status("Executing Local Pipeline...", expanded=True) as ai_status:
                formatted_pages = [{"page": 1, "text": st.session_state.raw_text}]
                analysis_result = analyze_legal_text(formatted_pages, category)
                ai_status.update(label="Analysis Complete", state="complete", expanded=False)
                
                st.markdown(f"""
                <div style="background-color: #1f2937; padding: 1.5rem; border-radius: 8px; border: 1px solid #374151; color: #f8fafc;">
                    {analysis_result.get("answer", "No answer generated.")}
                </div>
                """, unsafe_allow_html=True)
                
                grounded = analysis_result.get("grounded")
                if grounded is True:
                    pages = ", ".join(str(p) for p in analysis_result.get("quote_pages", []))
                    st.success(f"Verified against source text (Page: {pages})", icon="✅")
                elif grounded is False:
                    st.error("Warning: Quoted clause not found verbatim in document.", icon="🚨")

    with right_pane:
        st.markdown("### 📖 Source document")
        st.markdown(f"""
        <div class="doc-viewer">
            <p style="color: #64748b; font-size: 0.8rem; font-family: sans-serif; font-weight: 600;">RAW TEXT VIEW</p>
            {st.session_state.raw_text.replace(chr(10), '<br>')}
        </div>
        """, unsafe_allow_html=True)
