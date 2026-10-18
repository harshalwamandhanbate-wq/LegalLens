from pypdf import PdfReader

def extract_text_from_pdf(pdf_file):
    """
    Reads an uploaded PDF and returns its plain text page-by-page.
    """
    reader = PdfReader(pdf_file)
    extracted_text = ""
    
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            extracted_text += f"\n--- Page {page_num + 1} ---\n" + text
            
    return extracted_text

# Quick self-test to verify it works
if __name__ == "__main__":
    try:
        sample_text = extract_text_from_pdf(r"C:\Users\Free_\OneDrive\Desktop\12 hrs\sample.pdf.pdf")
        print("Success! Extracted text preview:")
        print(sample_text[:300]) # Prints first 300 characters
    except Exception as e:
        print(f"Error testing PDF extraction: {e}")