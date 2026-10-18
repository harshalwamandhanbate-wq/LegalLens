import streamlit as st

# 1. THE IMPORTS (This is where your team's files connect!)
# Pulls the PDF reader from Member 2
from engine import extract_text_from_pdf 
# Pulls the AI Brain from Member 1 (You)
from ai_agent import advanced_legal_analysis 

st.title("⚖️ Local Legal Triage Agent")

# 2. THE UI
uploaded_file = st.file_uploader("Upload a PDF Contract", type="pdf")
user_query = st.text_input("What do you want to know about this contract?")

if st.button("Run AI Analysis"):
    
    # 3. THE INTEGRATION
    if uploaded_file and user_query:
        
        # Step A: Member 2's engine reads the file
        with st.spinner("Reading PDF..."):
            extracted_text = extract_text_from_pdf(uploaded_file)
            
        # Step B: Member 1's brain analyzes the text
        with st.spinner("AI is analyzing (Zero-Temperature)..."):
            final_answer = advanced_legal_analysis(extracted_text, user_query)
            
        # Step C: Member 3's UI displays the result
        st.markdown("### Official Analysis")
        st.info(final_answer)
        
    else:
        st.error("Please upload a file and type a question.")
