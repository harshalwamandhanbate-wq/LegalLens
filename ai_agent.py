import requests

def ask_gemma(prompt_text):
    url = "http://localhost:11434/api/generate"
    
    # THE PARAMETER TUNING LAB
    payload = {
        "model": "gemma2:2b",
        "prompt": prompt_text,
        "stream": False,
        "options": {
            "temperature": 0.0,  # 0.0 forces the AI to always pick the highest-probability word (zero creativity).
            "top_p": 0.1,        # 0.1 cuts off the bottom 90% of potential words, forcing strict/formal vocabulary.
            "seed": 42           # Locks the initial random state so the exact same input yields the exact same output.
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=120)
        return response.json()["response"]
    except requests.exceptions.Timeout:
        return "System Error: AI generation timed out."
    except Exception as e:
        return f"System Error connecting to local AI: {e}"

def advanced_legal_analysis(contract_text, user_question):
    if not contract_text or len(contract_text.strip()) < 20:
        return "Error: Document text is missing or too short."
    
    safe_text = contract_text[:4000]
    
    # UPGRADE 2 & 3: Scope Locking and One-Shot Example added to the prompt
    master_prompt = f"""
    You are an expert legal AI triage assistant. Analyze the provided text and answer the user query.
    
    CRITICAL INSTRUCTIONS:
    1. STRICT ACCURACY: Base your answer ONLY on the provided text.
    2. OUT OF SCOPE: If the user query is NOT related to the contract (e.g., general knowledge, coding, jokes), you must reply EXACTLY: "Query rejected: Out of scope."
    3. MISSING INFO: If the text doesn't contain the answer, reply EXACTLY: "Information not found in the provided text."
    4. MANDATORY FORMAT: Follow the structure in the example below perfectly.
    
    --- EXAMPLE OF PERFECT OUTPUT ---
    ### 🔍 Analysis
    The tenant must pay rent by the 1st of the month. A late fee applies after the 5th.
    ### 🚩 Risk Level
    MEDIUM - Late fees are enforced strictly after a 4-day grace period.
    ### 📜 Relevant Clause
    "A late fee of $50 will be assessed if rent is not received by the 5th."
    ---------------------------------
    
    CONTRACT TEXT:
    {safe_text}
    
    USER QUERY:
    {user_question}
    """
    
    raw_answer = ask_gemma(master_prompt)
    
    disclaimer = "\n\n---\n⚠️ **DISCLAIMER:** This is an AI triage tool, not legal advice."
    
    return raw_answer + disclaimer

# --- YOUR TESTING LAB ---
if __name__ == "__main__":
    dummy_contract = """
    CONFIDENTIALITY AGREEMENT:
    The Employee agrees not to share company trade secrets. 
    Penalty for breach is immediate termination and a $10,000 fine.
    """
    
    print("\n--- SEED TEST: RUN 1 ---")
    response_1 = advanced_legal_analysis(dummy_contract, "Explain the penalty like I am 5 years old.")
    print(response_1)
    
    print("\n--- SEED TEST: RUN 2 ---")
    response_2 = advanced_legal_analysis(dummy_contract, "Explain the penalty like I am 5 years old.")
    print(response_2)
    
    print("\n--- VERDICT ---")
    if response_1 == response_2:
        print("✅ SUCCESS: Seed is locked. Responses are 100% identical.")
    else:
        print("❌ FAILED: Responses varied.")