from collections import Counter
from math import log, sqrt
from pathlib import Path
import re

import streamlit as st
from ollama import chat
from pypdf import PdfReader


BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"

DEFAULT_PDF_PATHS = [
    Path(r"C:\Users\nakul.kumbria\Downloads\Resource Management Playbook (1).pdf"),
    Path(r"C:\Users\nakul.kumbria\Downloads\Work Management Playbook (1).pdf"),
]

GREETING = (
    "Hi Nakul. Ask me a Planview EPPM question and I will answer from the "
    "Resource Management and Work Management playbooks."
)

SYSTEM_PROMPT = """You are a Planview EPPM assistant for company users.
Answer using only the supplied playbook context.
If the context does not contain the answer, say that the answer is not available in the indexed playbooks.
Do not invent company policy, process steps, role responsibilities, URLs, or field definitions.
When the answer uses a playbook excerpt, cite the source and page in brackets.
Keep answers direct and practical. Use numbered steps for procedures."""

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_/-]{1,}", re.IGNORECASE)
STOP_WORDS = {
    "about",
    "above",
    "after",
    "again",
    "against",
    "also",
    "another",
    "because",
    "before",
    "being",
    "between",
    "both",
    "could",
    "does",
    "doing",
    "down",
    "during",
    "each",
    "from",
    "further",
    "have",
    "having",
    "into",
    "more",
    "most",
    "only",
    "other",
    "over",
    "same",
    "should",
    "such",
    "than",
    "that",
    "their",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "under",
    "until",
    "very",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "would",
    "your",
}


def find_pdf_paths() -> list[Path]:
    paths: list[Path] = []

    for path in DEFAULT_PDF_PATHS:
        if path.exists():
            paths.append(path)

    if DOCS_DIR.exists():
        paths.extend(sorted(DOCS_DIR.rglob("*.pdf")))

    seen: set[str] = set()
    unique_paths: list[Path] = []
    for path in paths:
        key = str(path.resolve()).lower()
        if key not in seen:
            seen.add(key)
            unique_paths.append(path)

    return unique_paths


def document_signature(paths: list[Path]) -> tuple[tuple[str, int, int], ...]:
    return tuple(
        (str(path), path.stat().st_size, path.stat().st_mtime_ns) for path in paths
    )


def clean_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def tokenize(text: str) -> list[str]:
    return [
        token.lower()
        for token in TOKEN_RE.findall(text)
        if len(token) > 2 and token.lower() not in STOP_WORDS
    ]


def chunk_text(text: str, max_words: int = 220, overlap: int = 45) -> list[str]:
    words = text.split()
    if not words:
        return []

    if len(words) <= max_words:
        return [" ".join(words)]

    chunks: list[str] = []
    step = max_words - overlap
    for start in range(0, len(words), step):
        chunk_words = words[start : start + max_words]
        if len(chunk_words) < 35 and chunks:
            break
        chunks.append(" ".join(chunk_words))

    return chunks


@st.cache_resource(show_spinner=False)
def load_knowledge_base(
    signature: tuple[tuple[str, int, int], ...],
) -> dict[str, object]:
    chunks: list[dict[str, object]] = []

    for path_string, _size, _mtime in signature:
        path = Path(path_string)
        reader = PdfReader(str(path))

        for page_number, page in enumerate(reader.pages, start=1):
            page_text = clean_text(page.extract_text() or "")
            for chunk_number, text in enumerate(chunk_text(page_text), start=1):
                counts = Counter(tokenize(text))
                if not counts:
                    continue

                chunks.append(
                    {
                        "source": path.name,
                        "page": page_number,
                        "chunk": chunk_number,
                        "text": text,
                        "counts": dict(counts),
                    }
                )

    document_frequency: Counter[str] = Counter()
    for chunk in chunks:
        document_frequency.update(chunk["counts"].keys())

    idf = {
        term: log((1 + len(chunks)) / (1 + frequency)) + 1
        for term, frequency in document_frequency.items()
    }

    for chunk in chunks:
        weights: dict[str, float] = {}
        norm = 0.0

        for term, frequency in chunk["counts"].items():
            weight = (1 + log(frequency)) * idf[term]
            weights[term] = weight
            norm += weight * weight

        chunk["weights"] = weights
        chunk["norm"] = sqrt(norm) or 1.0
        del chunk["counts"]

    return {"chunks": chunks, "idf": idf}


def retrieve_chunks(
    knowledge_base: dict[str, object], query: str, top_k: int
) -> list[dict[str, object]]:
    chunks = knowledge_base.get("chunks", [])
    idf = knowledge_base.get("idf", {})
    query_counts = Counter(tokenize(query))

    if not chunks or not query_counts:
        return []

    query_weights: dict[str, float] = {}
    query_norm = 0.0
    for term, frequency in query_counts.items():
        if term not in idf:
            continue
        weight = (1 + log(frequency)) * idf[term]
        query_weights[term] = weight
        query_norm += weight * weight

    query_norm = sqrt(query_norm) or 1.0
    if not query_weights:
        return []

    scored_chunks: list[dict[str, object]] = []
    for chunk in chunks:
        dot_product = sum(
            weight * chunk["weights"].get(term, 0.0)
            for term, weight in query_weights.items()
        )
        score = dot_product / (query_norm * chunk["norm"])
        if score > 0:
            scored_chunks.append({**chunk, "score": score})

    scored_chunks.sort(key=lambda item: item["score"], reverse=True)
    return scored_chunks[:top_k]


def format_context(matches: list[dict[str, object]]) -> str:
    if not matches:
        return "No relevant playbook excerpts were retrieved."

    context_parts: list[str] = []
    for index, match in enumerate(matches, start=1):
        context_parts.append(
            f"[Source {index}: {match['source']}, p. {match['page']}]\n"
            f"{match['text']}"
        )

    return "\n\n".join(context_parts)


def build_retrieval_query(history: list[dict[str, str]], current_prompt: str) -> str:
    recent_user_messages = [
        message["content"]
        for message in history
        if message.get("role") == "user"
    ][-3:]
    return "\n".join([*recent_user_messages, current_prompt])


def build_model_messages(
    history: list[dict[str, str]],
    user_prompt: str,
    context: str,
    use_playbooks: bool,
) -> list[dict[str, str]]:
    if not use_playbooks:
        return history[-10:] + [{"role": "user", "content": user_prompt}]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history[-8:])
    messages.append(
        {
            "role": "user",
            "content": (
                "Question:\n"
                f"{user_prompt}\n\n"
                "Playbook context:\n"
                f"{context}"
            ),
        }
    )
    return messages


def main() -> None:
    st.set_page_config(page_title="Planview EPPM Chatbot", layout="centered")

    st.title("Planview EPPM Chatbot")

    pdf_paths = find_pdf_paths()
    signature = document_signature(pdf_paths)
    knowledge_base = (
        load_knowledge_base(signature) if signature else {"chunks": [], "idf": {}}
    )

    with st.sidebar:
        st.header("Settings")

        model_options = [
            "llama3.2",
            "deepseek-r1:7b",
            "qwen3:8b",
            "gemma4"
        ]

        model_name = st.selectbox("Ollama model", model_options, index=0)
        temperature = st.slider("Temperature", 0.0, 1.5, 0.2, 0.1)
        use_playbooks = st.toggle("Use playbooks", value=True)
        top_k = st.slider("Retrieved excerpts", 3, 8, 5)
        show_context = st.toggle("Show retrieved excerpts", value=False)

        if st.button("Refresh playbooks"):
            load_knowledge_base.clear()
            st.rerun()

        st.divider()
        st.subheader("Indexed PDFs")
        if pdf_paths:
            for path in pdf_paths:
                st.caption(path.name)
            st.caption(f"{len(knowledge_base['chunks'])} text chunks loaded")
        else:
            st.warning("No PDFs found in the default locations or docs folder.")

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": GREETING}]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_prompt = st.chat_input("Ask about Planview EPPM...")

    if user_prompt:
        prior_history = st.session_state.messages.copy()
        st.session_state.messages.append({"role": "user", "content": user_prompt})

        with st.chat_message("user"):
            st.markdown(user_prompt)

        retrieval_query = build_retrieval_query(prior_history, user_prompt)
        matches = (
            retrieve_chunks(knowledge_base, retrieval_query, top_k)
            if use_playbooks
            else []
        )
        context = format_context(matches)
        model_messages = build_model_messages(
            prior_history, user_prompt, context, use_playbooks
        )

        try:
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = chat(
                        model=model_name,
                        messages=model_messages,
                        options={"temperature": temperature},
                    )

                    assistant_reply = response["message"]["content"]
                    st.markdown(assistant_reply)

                    if show_context and use_playbooks:
                        with st.expander("Retrieved excerpts"):
                            for match in matches:
                                st.markdown(
                                    f"**{match['source']}, p. {match['page']}** "
                                    f"(score: {match['score']:.3f})"
                                )
                                st.write(match["text"])

            st.session_state.messages.append(
                {"role": "assistant", "content": assistant_reply}
            )

        except Exception as error:
            with st.chat_message("assistant"):
                st.error(f"Error connecting to Ollama: {error}")


if __name__ == "__main__":
    main()
