import requests

OLLAMA_URL = "http://localhost:11434/api/generate"

def run_targeted_triage(clause_text, category_focus="General Triage"):
    prompt = f"""
You are an offline legal triage assistant. 
Analyze the provided text snippet specifically for: {category_focus}.

RULES:
1. State the RISK LEVEL clearly as [HIGH RISK], [MEDIUM RISK], or [LOW RISK].
2. Provide a 1-sentence plain English summary.
3. Quote the EXACT sentence from the text as evidence.
4. If this topic is not mentioned in the text, reply: "The document is silent on this matter."
5. Do NOT give legal validity opinions. Remind user to consult an advocate.

DOCUMENT TEXT:
\"\"\"
{clause_text}
\"\"\"

FORMAT:
- RISK: [HIGH / MEDIUM / LOW]
- SUMMARY:
- EXACT QUOTE:
- ESCALATION NOTE:
"""

    payload = {
        "model": "gemma:2b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1  # Stops the model from making things up
        }
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=90)
        if response.status_code == 200:
            return response.json().get("response", "No response generated.")
        return f"Error: HTTP {response.status_code}"
    except Exception:
        return "Error: Could not connect to Ollama. Make sure Ollama is running in background!"