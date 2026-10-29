# Portfolio review — October 29, 2026

Scope: current main-branch trees, READMEs and core implementation files for the five requested repositories. Rankings reflect engineering evidence and relevance to SDE/AI interviews, not measured hiring outcomes.

| Priority | Repository | Recommendation | Interview-value gaps |
| --- | --- | --- | --- |
| 1 | Chatbot-Creation | Lead AI project; also useful for Python SDE applications | Empty docs directory; no synthetic sample PDF, recording, retrieval evaluation, citation validation or latency evidence |
| 2 | AI-Story-Writer | Lead web/backend project after recruiter access is resolved | Private repository; no recorded demo, tests, streaming, deadlines or concurrency cap |
| 3 | API-Automation | Supporting enterprise integration project | README advertises EPPM user deactivation without a matching script; missing dependency/setup instructions and sample output; jira.py shadows the jira package and executes network/email work at import |
| 4 | Langchain | Keep as an exploration repository until reproducibility improves | README advertises Chroma, while principal PDF scripts use FAISS HNSW; placeholder clone URL; nested working directory omitted; wrong streamlit filename; hard-coded PDF directory; no UI upload despite README claim |
| 5 | Nakul-Kumbria-Website | Use as the navigation hub rather than a lead engineering case study | Generic/incomplete README; repeated project cards; practice projects receive substantial space; neither top-two project is linked in current HTML |

## Featured ordering

For AI applications: Playbook QA first, Story Foundry second, API Automation third.
For SDE applications: Story Foundry first, Playbook QA second, API Automation third.
Keep the personal website as the landing link. Link directly to case studies and source; do not ask recruiters to hunt through every repository.
AI-Story-Writer remains private. This review does not change repository visibility.

## Proposed repository descriptions

Chatbot-Creation: Python/Streamlit PDF question answering with TF-IDF retrieval, page-aware context, Ollama generation, unit tests, and Docker packaging.

AI-Story-Writer: Local Node.js storytelling app that runs concurrent Ollama drafts and synthesizes successful outputs, with a vanilla JavaScript UI and per-model error handling.

## Resume-ready bullets

These describe committed code, with no invented adoption, accuracy, cost, or speed metrics.

### Playbook QA — Python, Streamlit, Ollama, pypdf, Docker

- Built a PDF question-answering app with page-aware extraction, overlapping text chunks, and TF-IDF cosine-similarity retrieval to supply relevant playbook excerpts to local Ollama models.
- Implemented configurable retrieval thresholds, bounded conversation context, a no-match guard, and six unit tests covering retrieval, prompt construction, and model discovery.

SDE emphasis: Implemented cached document indexing, configurable model-service timeouts, and Docker packaging with a Streamlit health check for a Python document-QA application.

### Story Foundry — JavaScript, Node.js, Ollama HTTP APIs

- Built a browser-based writing app with a Node.js HTTP backend that discovers installed Ollama models and orchestrates concurrent story generation using Promise.all.
- Implemented per-model failure handling and a synthesis pass over successful drafts, with single-model selection and optional continuation from recent browser-held conversation history.

AI emphasis: Designed a multi-model generation-and-synthesis workflow with configurable story prompts and independently surfaced generator and synthesis errors.

## Concrete demo work still needed

### Playbook QA
Create a small synthetic PDF describing a fictional approval process. Record a supported question, visible retrieved excerpts, and a fresh-session out-of-scope question. A follow-up can reuse earlier query terms, so do not assume every off-topic follow-up will trigger the no-match guard.
Add a small evaluation set with expected source pages. Measure retrieval hit rate at k and review answer support separately. Tests currently exercise helper logic, not end-to-end factuality or PDF parsing.

### Story Foundry
Record single-model and all-model runs with the same prompt; show model versions and hardware. Capture actual wall-clock latency before making speed claims. Add mocked API tests for partial generator failure, all-model failure, invalid requests, and synthesis failure. Bound concurrency and add request deadlines before shared hosting.

### API Automation
Choose one canonical script, externalize configuration, add synthetic Jira fixtures and a no-send demo mode, and document Windows/Outlook requirements. Do not run the current scripts just to demonstrate them: some call mail.Send(). Burndown is reconstructed from current issue points/status history, so do not claim exact historical Jira parity without validating scope changes, reopenings and full changelog coverage.

### Langchain
Align README with FAISS/HNSW, fix the working directory and Project16_streamlite.py name, configure the PDF directory, and reproduce a clean install. Do not describe EPPM.py's fixed FAQ dictionary as RAG. The experimental lanserve.py defines an app but does not register the chain routes.

### Website
Reduce duplicate cards, feature the top projects with a short problem/architecture/demo/source structure, and mark private source honestly. Replace the generic README tree with actual filenames. Current live links were observed in HTML but not exercised in this source review.

## Change scope

Documentation changes only: rewritten project framing, stack roles, architecture, setup corrections, demo guidance, limitations, and reusable resume wording. No application behavior or repository visibility changes.
