import streamlit as st
from engine import extract_text_from_pdf 
from ai_agent import advanced_legal_analysis 

# --- 1. V0 / NEXT.JS STYLE CSS INJECTION ---
# This must be the very first Streamlit command
st.set_page_config(page_title="Private Legal Agent", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
        /* Hide the default Streamlit top header and hamburger menu */
        header {visibility: hidden;}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Modern minimalist background */
        .stApp {
            background-color: #f8fafc; /* Very light slate */
            font-family: 'Inter', -apple-system, sans-serif;
        }
        
        /* Style the upload box to look like a modern v0 drag-and-drop zone */
        .stFileUploader > div > div {
            border: 2px dashed #cbd5e1;
            border-radius: 12px;
            background-color: #ffffff;
            padding: 20px;
            transition: all 0.3s ease;
        }
        .stFileUploader > div > div:hover {
            border-color: #94a3b8;
        }
        
        /* Clean white text inputs with subtle borders */
        .stTextArea > div > div > textarea {
            background-color: #ffffff;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        }
        
        /* Primary Button styling (Vercel-like sleek black button) */
        .stButton > button {
            background-color: #0f172a !important;
            color: #ffffff !important;
            border-radius: 8px !important;
            padding: 12px 24px !important;
            font-weight: 600 !important;
            border: none !important;
            width: 100%;
            transition: all 0.2s ease;
        }
        .stButton > button:hover {
            background-color: #334155 !important;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        }
        
        /* Custom spacing for the layout */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
            max-width: 1200px;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. MODERN UI LAYOUT ---
# Centered Header
st.markdown("<h1 style='text-align: center; color: #0f172a; font-weight: 800; margin-bottom: 0.5rem;'>⚖️ Private Legal Triage</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; font-size: 1.1rem; margin-bottom: 3rem;'>100% On-Device Analysis • Zero Data Retention</p>", unsafe_allow_html=True)

# Create two clean columns (left side slightly smaller than right side)
col1, col2 = st.columns([1, 1.2], gap="large")

with col1:
    st.markdown("<h3 style='color: #334155; font-size: 1.2rem;'>📄 Document Ingestion</h3>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload Contract", type="pdf", label_visibility="collapsed")
    
    st.markdown("<br><h3 style='color: #334155; font-size: 1.2rem;'>🎯 Query Engine</h3>", unsafe_allow_html=True)
    user_query = st.text_area("Question", 
                              placeholder="e.g., 'What is the governing law?' or 'List all financial penalties.'",
                              height=120,
                              label_visibility="collapsed")
    
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_button = st.button("Run Offline Analysis →")

with col2:
    st.markdown("<h3 style='color: #334155; font-size: 1.2rem;'>⚡ AI Output & Analysis</h3>", unsafe_allow_html=True)
    
    if analyze_button:
        if uploaded_file is None:
            st.warning("Please upload a document first.", icon="⚠️")
        elif user_query.strip() == "":
            st.warning("Please enter a query.", icon="⚠️")
        else:
            # Modern expandable status loader
            with st.status("Executing Local Pipeline...", expanded=True) as status:
                st.write("📄 Extracting raw text via pypdf...")
                extracted_text = extract_text_from_pdf(uploaded_file)
                
                if "Error" in extracted_text:
                    status.update(label="Processing Failed", state="error", expanded=True)
                    st.error(extracted_text)
                else:
                    st.write("🧠 Routing through Gemma 2B (Temp: 0.0)...")
                    final_answer = advanced_legal_analysis(extracted_text, user_query)
                    
                    status.update(label="Analysis Complete", state="complete", expanded=False)
            
            # The Final Answer Card (White background, shadow, rounded corners)
            st.markdown(f"""
            <div style="background-color: #ffffff; padding: 24px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);">
                {final_answer}
            </div>
            """, unsafe_allow_html=True)
            
    else:
        # Empty State Placeholder (Before they click run)
        st.markdown("""
        <div style="background-color: #f1f5f9; padding: 40px; border-radius: 12px; border: 1px dashed #cbd5e1; text-align: center; color: #94a3b8; margin-top: 1rem;">
            Upload a document and run an analysis to view AI outputs here.
        </div>
        """, unsafe_allow_html=True)
