# Planview EPPM Chatbot

This is an internal Streamlit chatbot that answers Planview EPPM questions from indexed playbook PDFs. It uses retrieval augmented generation: the app extracts text from PDFs, ranks relevant excerpts for each question, and sends those excerpts to an Ollama chat model.

The model is not fine-tuned and the PDFs are not permanently trained into the model.

## What It Does

- Reads PDFs from a configured `docs/` folder or explicit PDF paths.
- Retrieves relevant playbook excerpts for each user question.
- Instructs the model to answer only from retrieved playbook context.
- Cites source filenames and page numbers in the prompt context.
- Supports app-level password protection.
- Discovers available Ollama models and filters them through a configured allowlist.
- Logs internal errors without exposing raw exception details to users.

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

Copy `.env.example` into your deployment environment and set values there. The app reads configuration from environment variables first, then Streamlit secrets.

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
