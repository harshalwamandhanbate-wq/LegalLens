import streamlit as st

st.set_page_config(page_title="Private Legal Triage Agent", layout="wide")

st.title("🛡️ Private Legal Document Triage Agent")
st.warning("⚖️ **Notice:** Not legal advice. Consult a qualified professional.")

uploaded_file = st.file_uploader("Upload a Contract (PDF)", type=["pdf"])

if uploaded_file is not None:
    # Create two equal-width columns
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📄 Raw Document Text")
        st.info("Member 2's PDF parser will output text here.")

    with col2:
        st.subheader("🤖 AI Triage & Evidence")
        if st.button("Run Analysis", type="primary"):
            st.success("Member 1's AI engine will output analysis here.")