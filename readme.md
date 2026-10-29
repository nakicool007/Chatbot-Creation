# Playbook QA — Local Document Retrieval with Ollama

A Python application that answers process questions from PDF playbooks through a Streamlit chat interface. It combines page-aware PDF extraction, TF-IDF cosine-similarity retrieval, and an Ollama chat model, making the retrieval and prompt-building logic inspectable independently of model inference.

## Engineering highlights

- Splits page text into overlapping chunks (220 words, 45-word overlap by default), preserving filename and page metadata.
- Builds an in-memory TF-IDF index and retrieves ranked excerpts with configurable top-k and score thresholds.
- Returns a no-match response before calling the model when retrieval finds no relevant excerpts.
- Adds source/page context and citation instructions to the model prompt; users can inspect retrieved excerpts.
- Caches indexing using document paths, sizes, and modification timestamps.
- Includes six unit tests covering retrieval ranking, unmatched queries, prompt construction, history limits, and model discovery.
- Includes a Dockerfile with a Streamlit health check.

## Tech stack and architecture

| Component | Technology and role |
| --- | --- |
| Interface | Streamlit chat, session history, retrieval controls |
| Document parsing | pypdf, page-level text extraction |
| Retrieval | Python Counter/math, TF-IDF weights and cosine similarity |
| Generation | Ollama Python client; local or configured remote endpoint |
| Packaging and checks | Docker, Python unittest |

PDFs → page text → overlapping chunks → cached TF-IDF index. A question plus recent user questions drives retrieval; selected excerpts and bounded chat history are sent to Ollama.

This implementation does not use LangChain, an embedding model, or a vector database. Citation instructions guide model output but do not validate that generated claims are supported.

## Demo status

No recorded demo or sample PDF is committed yet. The repository's docs folder is empty, so a fresh checkout needs a text-based PDF before document QA works. Use synthetic or openly licensed documents for portfolio demonstrations.

For a short recording, show: a document-backed answer with retrieved excerpts visible; a question absent from the document; and a follow-up question. Record actual output and model name rather than presenting an illustrative answer as a measured result.

## Scope and limitations

- Retrieval is lexical; paraphrases without shared terms can be missed. Scanned PDFs require OCR outside this app.
- Prompt instructions and the no-match guard reduce unsupported answers but do not guarantee factuality.
- Model selection prefers configured names, but the UI falls back to available models if none match; the allowlist is not a strict security boundary.
- With no app password configured, the app permits access. Shared deployments need upstream authentication.
- No answer-quality, latency, throughput, or user-adoption measurements are included.

## Requirements

- Python 3.11 recommended
- Ollama running locally or reachable through `OLLAMA_HOST`
- At least one allowed Ollama chat model
- Python packages from `requirements.txt`

## Local Setup

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Pull a model if needed:

```powershell
ollama pull llama3.2
```

Create a `docs/` folder and place playbook PDFs there, or configure `PLAYBOOK_PDF_PATHS`.

Run the app:

```powershell
python -m streamlit run aiapp.py
```

Then open:

```text
http://localhost:8501
```

## Configuration

Use `.env.example` as a reference and export its settings into the process environment, or configure Streamlit secrets. The app reads environment variables first, then Streamlit secrets; it does not automatically load a `.env` file. For example, in PowerShell:

```powershell
$env:OLLAMA_MODELS = 'llama3.2'
python -m streamlit run aiapp.py
```

Important settings:

```text
APP_PASSWORD             Optional app password for local/internal protection
APP_PASSWORD_SHA256      Preferred hashed password value
AUTH_HANDLED_UPSTREAM    true when SSO/auth is enforced before Streamlit
PLAYBOOK_DOCS_DIR        Folder containing PDFs, default: docs
PLAYBOOK_PDF_PATHS       Semicolon-separated PDF paths
OLLAMA_HOST              Remote Ollama host, blank means local default
OLLAMA_MODELS            Semicolon-separated allowlist, or * for all available
ALLOW_FREE_CHAT          false by default, keeps answers playbook-scoped
MAX_PROMPT_CHARS         User prompt length limit
MAX_HISTORY_MESSAGES     Chat history sent to the model
MIN_RETRIEVAL_SCORE      Minimum retrieval score for excerpts
LOG_LEVEL                Python logging level
```

To generate a SHA-256 password hash:

```powershell
python -c "import hashlib, getpass; print(hashlib.sha256(getpass.getpass().encode()).hexdigest())"
```

## Docker

Build the image:

```powershell
docker build -t planview-eppm-chatbot .
```

Run with a mounted documents folder:

```powershell
docker run --rm -p 8501:8501 `
  -e APP_PASSWORD="change-me" `
  -e OLLAMA_HOST="http://host.docker.internal:11434" `
  -v "${PWD}\docs:/app/docs:ro" `
  planview-eppm-chatbot
```

PDFs are excluded from Docker build context by `.dockerignore`; mount them at runtime unless your deployment process intentionally injects them.

## Tests

Run the standard-library test suite:

```powershell
python -B -m unittest discover -s tests
```

## Production Notes

- Put the app behind company SSO or an authenticated internal gateway when possible. `APP_PASSWORD` is a baseline guard, not a full identity system.
- Use a managed Ollama endpoint or another managed model service for shared deployments.
- Keep playbook PDFs in controlled storage and mount or sync them into the app.
- Keep `ALLOW_FREE_CHAT=false` for factual process answers.
- Review logs for indexing errors after replacing PDFs.
