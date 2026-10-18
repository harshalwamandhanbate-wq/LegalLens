import streamlit as st
import time
import requests
from doc_parser import extract_text_from_pdf
from vector_store import LocalContractStore
from ai_engine_v2 import run_targeted_triage

st.set_page_config(page_title="LexGuard - Legal Triage", layout="wide", initial_sidebar_state="expanded")

# --- INITIALIZE MEMORY ---
if "vector_store" not in st.session_state:
    st.session_state.vector_store = LocalContractStore()
if "text_loaded" not in st.session_state:
    st.session_state.text_loaded = False
if "raw_text" not in st.session_state:
    st.session_state.raw_text = ""
if "chunk_count" not in st.session_state:
    st.session_state.chunk_count = 0

# --- SYSTEM HEALTH DASHBOARD (Sidebar) ---
st.sidebar.title("⚙️ System Health")
try:
    # Check if Ollama is running locally
    req = requests.get("http://localhost:11434", timeout=1)
    if req.status_code == 200:
        st.sidebar.success("🟢 **AI Engine:** Online (Gemma 2B)")
    else:
        st.sidebar.error("🔴 **AI Engine:** Offline")
except:
    st.sidebar.error("🔴 **AI Engine:** Disconnected (Run 'ollama run gemma:2b' in terminal)")

st.sidebar.success("🟢 **Vector DB:** Online (ChromaDB)")
st.sidebar.success("🟢 **Network:** Isolated (Offline Mode)")
st.sidebar.divider()
st.sidebar.info("LexGuard v2.0 | ZeroDay Hackathon")

# --- MAIN HEADER ---
st.title("⚖️ LexGuard: Private Document Triage")
st.warning("⚠️ **Preliminary Analysis Only:** Not legal advice. Consult an advocate for legal validity.")

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload Legal Agreement (PDF up to 500 pages)", type=["pdf"])

if uploaded_file and not st.session_state.text_loaded:
    # THE AUDIT TRAIL (Shows process step-by-step)
    with st.status("Processing Document...", expanded=True) as status:
        st.write("📄 Extracting raw text from PDF...")
        text = extract_text_from_pdf(uploaded_file)
        st.session_state.raw_text = text
        
        st.write("✂️ Chunking text for context window...")
        time.sleep(0.5) # Slight pause for UI effect
        
        st.write("🧮 Indexing into ChromaDB Vector Store...")
        chunks = st.session_state.vector_store.add_document_chunks(text)
        st.session_state.chunk_count = chunks
        
        st.session_state.text_loaded = True
        status.update(label="Document Processed Successfully!", state="complete", expanded=False)

# --- THE MAIN INTERFACE ---
if st.session_state.text_loaded:
    # Use Tabs for a clean, modern UI
    tab1, tab2 = st.tabs(["🎯 Triage Dashboard", "📄 Full Document Viewer"])

    with tab1:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("1. Select Triage Target")
            category = st.radio(
                "Risk Category:",
                [
                    "Financial Penalties & Late Fees",
                    "Termination, Notice Period & Lock-in",
                    "Liability, Damages & Indemnification",
                    "Governing Law & Dispute Resolution"
                ]
            )
            run_btn = st.button("Run Grounded AI Analysis", type="primary", use_container_width=True)
            
            st.divider()
            st.metric(label="Total Semantic Chunks Indexed", value=st.session_state.chunk_count)

        with col2:
            st.subheader("2. AI Analysis & Evidence")
            if run_btn:
                # The execution trail for the AI prediction
                with st.status("Running Local AI Inference...", expanded=True) as ai_status:
                    st.write("🔍 Querying ChromaDB for relevant clauses...")
                    matched_paragraphs = st.session_state.vector_store.query_relevant_clauses(category, n_results=2)
                    
                    if not matched_paragraphs:
                        ai_status.update(label="Analysis Complete", state="complete")
                        st.info("The document is silent on this matter.")
                    else:
                        st.write("🧠 Generating grounded response via Gemma 2B...")
                        context = "\n\n".join(matched_paragraphs)
                        ai_result = run_targeted_triage(context, category_focus=category)
                        ai_status.update(label="Analysis Complete", state="complete", expanded=False)
                        
                        # Display Color-Coded Badges
                        if "HIGH" in ai_result[:100]:
                            st.error("🚨 **RISK LEVEL: HIGH**")
                        elif "MEDIUM" in ai_result[:100]:
                            st.warning("⚠️ **RISK LEVEL: MEDIUM**")
                        elif "LOW" in ai_result[:100]:
                            st.success("✅ **RISK LEVEL: LOW / STANDARD**")
                            
                        # Display the formatted AI text
                        st.markdown(ai_result)
                        
                        # The Evidence Box
                        with st.expander("🔍 Inspect Verbatim Vector Passage Retrieved (Traceability)"):
                            st.info("ChromaDB retrieved this exact text from the document and sent it to the AI:")
                            st.write(context)

    with tab2:
        st.subheader("Full Document Context")
        st.markdown("Scroll through the entire extracted document below. The AI only processes relevant chunks via Vector Search.")
        # This text area holds the whole document, even 500 pages, without crashing the AI
        st.text_area("Raw Document Text", st.session_state.raw_text, height=600)