# Planview EPPM Chatbot

This is a local Streamlit chatbot that uses Ollama for responses and the Planview EPPM playbooks as its knowledge source.

It does not fine-tune or permanently train the model. Instead, it uses retrieval augmented generation: the app extracts text from the PDFs, ranks the most relevant excerpts for each question, and sends those excerpts to the selected local Ollama model.

## What It Does

- Runs locally with Streamlit.
- Uses Ollama for local model inference.
- Reads the Resource Management and Work Management playbook PDFs from the configured local paths.
- Also reads any PDFs placed under a local `docs/` folder.
- Retrieves relevant playbook excerpts for each question.
- Instructs the model to answer only from the retrieved playbook context.
- Includes source and page citation guidance in the prompt.

## Supported Chat Models

The app currently lists these Ollama models:

- `llama3.2`
- `deepseek-r1:7b`
- `qwen3:8b`

The selected model must already be pulled in Ollama.

## Requirements

- Python 3.10+
- Ollama running locally
- At least one supported Ollama model
- Python packages from `requirements.txt`

## Installation

```powershell
pip install -r requirements.txt
```

Pull at least one chat model:

```powershell
ollama pull llama3.2
```

## Playbook Files

The app is configured to look for:

```text
C:\Users\nakul.kumbria\Downloads\Resource Management Playbook (1).pdf
C:\Users\nakul.kumbria\Downloads\Work Management Playbook (1).pdf
```

You can add more PDFs by creating a `docs/` folder in this project and placing them there. PDF files under `docs/` are ignored by git by default because these playbooks may contain company information.

## Run

```powershell
streamlit run aiapp.py
```

Then open:

```text
http://localhost:8501
```

## Notes

- Use a low temperature for factual company/process answers.
- Click `Refresh playbooks` in the sidebar after adding or replacing PDFs.
- If the playbooks do not contain an answer, the assistant is instructed to say so rather than guess.
- Chat history lasts only for the current Streamlit session.
