# LegalLens

**Private legal document triage.** Upload a contract, ask a question, and get a plain-language answer with the exact clause behind it. The clause is checked against your PDF and highlighted in the text.

Everything runs on your own computer using a local model through [Ollama](https://ollama.com). Your contracts are never uploaded anywhere.

> ⚖️ LegalLens is an AI triage aid, **not legal advice**. Have a qualified lawyer check anything important.

<!-- Add a screenshot: save it as docs/screenshot.png and uncomment the next line -->
<!-- ![LegalLens screenshot](docs/screenshot.png) -->

## Features

- **Risk verdict:** every answer starts with a Low, Medium or High risk banner and a short reason.
- **Quote checking:** the clause the model quotes is searched for word for word in your PDF. If it isn't there, the answer is flagged as unverified.
- **Evidence highlighting:** verified quotes are highlighted in the contract viewer, and the viewer jumps to the right page.
- **Works on long contracts:** the document is split into chunks and the most relevant ones are sent to the model, so clauses on page 20 are not silently dropped.
- **Stays on topic:** questions that are not about the document are rejected.
- **Clear errors:** password-protected, corrupted and scanned PDFs get a helpful message instead of a crash.
- **Private by design:** the app makes no third-party requests, not even for fonts.

## How it works

1. `doc_parser.py` reads the PDF page by page and cleans the text.
2. `ai_agent.py` splits the text into chunks, picks the ones that best match your question, and asks the local Gemma model for an analysis in a fixed format.
3. The same module then checks that the quoted clause really appears in the PDF.
4. `app.py` and `ui_helpers.py` display the verdict, the analysis, the evidence and the highlighted contract.

## Requirements

- Python 3.10 or newer
- [Ollama](https://ollama.com/download) installed and running
- The `gemma2:2b` model (about 1.6 GB)

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/YOUR-USERNAME/LegalLens.git
cd LegalLens

# 2. (Recommended) create a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 3. Install the Python packages
pip install -r requirements.txt

# 4. Download the model
ollama pull gemma2:2b
```

## Running the app

Make sure Ollama is running (it starts automatically on most systems, or run `ollama serve`), then:

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

> Use `streamlit run app.py`, not `python app.py`. A Streamlit app needs the Streamlit runtime to show its interface.

## Usage

1. Upload a contract as a PDF.
2. Type a question, click one of the quick questions, or leave the box empty for a full triage.
3. Click **Answer question** or **Run full triage**.
4. Read the verdict and analysis, then check the quoted clause. A green badge means the wording was found in your PDF. A red badge means it was not, so treat the answer as unverified.
5. Open **What the model read** to see exactly which excerpts were sent to the model.

## Project structure

```
LegalLens/
├── app.py               Streamlit app: page layout and flow
├── ui_helpers.py        Styling, HTML builders and answer parsing
├── ai_agent.py          Chunking, retrieval, Ollama calls, quote verification
├── doc_parser.py        PDF text extraction and error handling
├── requirements.txt     Python dependencies
└── .streamlit/
    └── config.toml      Light theme
```

## Configuration

Settings live at the top of `ai_agent.py`:

| Setting | Default | Purpose |
|---|---|---|
| `MODEL` | `gemma2:2b` | Any model you have pulled in Ollama |
| `OPTIONS` | temperature `0.0`, seed `42`, `num_ctx` 4096 | Generation settings; temperature 0 makes output repeatable |
| `CHUNK_CHARS` | `1000` | Size of each text chunk |
| `CONTEXT_BUDGET` | `7000` | Maximum characters of contract text sent to the model |

To use a larger model, run `ollama pull <model>`, change `MODEL`, and raise `num_ctx` and `CONTEXT_BUDGET` if your hardware allows.

## Limitations

- **Scanned PDFs are not supported.** The app needs a text layer. Run scans through OCR first, for example `ocrmypdf in.pdf out.pdf`.
- **Retrieval is keyword-based.** A question worded very differently from the contract can miss the right passage. Embedding-based search would improve this.
- **A 2B model makes mistakes.** It can misread clauses, misjudge risk, or wrongly reject a valid question. That is why the quote check exists, but the check only proves the quote is real, not that the interpretation is right.
- **Long documents are partly read.** When a contract is bigger than the model's working window, the app warns you which pages were analysed.
- **English contracts work best.**

## Troubleshooting

| Problem | Fix |
|---|---|
| "Cannot reach Ollama" | Start Ollama with `ollama serve` |
| "Model not installed" | Run `ollama pull gemma2:2b` |
| `streamlit` is not recognised | Use `python -m streamlit run app.py` |
| "No extractable text found" | The PDF is scanned. Run OCR on it first |
| Analysis is slow | Small models on CPU can take a minute. A GPU or a smaller context helps |

## Contributing

Issues and pull requests are welcome. For larger changes, please open an issue first to discuss what you would like to change.

## License

Add a license before sharing the project publicly, for example [MIT](https://choosealicense.com/licenses/mit/).
