from collections import Counter
import hashlib
import hmac
import logging
from math import log, sqrt
import os
from pathlib import Path
import re
from typing import Any

import streamlit as st
from ollama import Client
from pypdf import PdfReader


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DOCS_DIR = BASE_DIR / "docs"
DEFAULT_ALLOWED_MODELS = [
    "llama3.2",
    "deepseek-r1:7b",
    "qwen3:8b",
    "gemma4",
]
DEFAULT_MAX_PROMPT_CHARS = 4000
DEFAULT_MAX_HISTORY_MESSAGES = 10
DEFAULT_MIN_RETRIEVAL_SCORE = 0.03
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 90.0

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger(__name__)

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


def get_config_value(name: str, default: str = "") -> str:
    env_value = os.getenv(name)
    if env_value is not None:
        return env_value

    try:
        secret_value = st.secrets.get(name)
    except Exception:
        secret_value = None

    if secret_value is None:
        return default

    return str(secret_value)


def get_bool_config(name: str, default: bool = False) -> bool:
    raw_value = get_config_value(name, str(default)).strip().lower()
    return raw_value in {"1", "true", "yes", "on"}


def get_int_config(name: str, default: int) -> int:
    raw_value = get_config_value(name, str(default)).strip()
    try:
        return int(raw_value)
    except ValueError:
        LOGGER.warning("Invalid integer config %s=%r; using %s", name, raw_value, default)
        return default


def get_float_config(name: str, default: float) -> float:
    raw_value = get_config_value(name, str(default)).strip()
    try:
        return float(raw_value)
    except ValueError:
        LOGGER.warning("Invalid float config %s=%r; using %s", name, raw_value, default)
        return default


def split_config_list(raw_value: str) -> list[str]:
    return [
        item.strip()
        for item in re.split(r"[;\n]", raw_value)
        if item.strip()
    ]


def resolve_project_path(value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return BASE_DIR / path


def configured_docs_dir() -> Path:
    return resolve_project_path(
        get_config_value("PLAYBOOK_DOCS_DIR", str(DEFAULT_DOCS_DIR))
    )


def configured_pdf_paths() -> list[Path]:
    return [
        resolve_project_path(path)
        for path in split_config_list(get_config_value("PLAYBOOK_PDF_PATHS"))
    ]


def configured_allowed_models() -> list[str]:
    raw_value = get_config_value("OLLAMA_MODELS")
    if not raw_value.strip():
        return DEFAULT_ALLOWED_MODELS.copy()
    return split_config_list(raw_value)


def is_authentication_configured() -> bool:
    return bool(
        get_config_value("APP_PASSWORD")
        or get_config_value("APP_PASSWORD_SHA256")
        or get_bool_config("AUTH_HANDLED_UPSTREAM", False)
    )


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def expected_password_hash() -> str:
    configured_hash = get_config_value("APP_PASSWORD_SHA256").strip()
    if configured_hash:
        return configured_hash

    password = get_config_value("APP_PASSWORD")
    if password:
        return hash_password(password)

    return ""


def require_authentication() -> bool:
    expected_hash = expected_password_hash()
    if not expected_hash:
        return True

    if st.session_state.get("authenticated"):
        return True

    st.title("Planview EPPM Chatbot")
    st.subheader("Sign in")

    with st.form("sign_in"):
        entered_password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")

    if submitted:
        entered_hash = hash_password(entered_password)
        if hmac.compare_digest(entered_hash, expected_hash):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Invalid password.")

    return False


def find_pdf_paths(
    docs_dir: Path | None = None,
    explicit_paths: list[Path] | None = None,
) -> list[Path]:
    paths: list[Path] = []
    docs_dir = docs_dir or configured_docs_dir()
    explicit_paths = explicit_paths or configured_pdf_paths()

    for path in explicit_paths:
        if path.exists() and path.is_file():
            paths.append(path)
        else:
            LOGGER.warning("Configured PDF path does not exist: %s", path)

    if docs_dir.exists():
        paths.extend(sorted(path for path in docs_dir.rglob("*.pdf") if path.is_file()))

    seen: set[str] = set()
    unique_paths: list[Path] = []
    for path in paths:
        key = str(path.resolve()).lower()
        if key not in seen:
            seen.add(key)
            unique_paths.append(path)

    return unique_paths


def document_signature(paths: list[Path]) -> tuple[tuple[str, int, int], ...]:
    signature: list[tuple[str, int, int]] = []
    for path in paths:
        try:
            stat_result = path.stat()
        except OSError:
            LOGGER.warning("PDF disappeared before indexing: %s", path)
            continue
        signature.append((str(path), stat_result.st_size, stat_result.st_mtime_ns))
    return tuple(signature)


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


def extract_model_names(list_response: Any) -> list[str]:
    models = getattr(list_response, "models", None)
    if models is None and isinstance(list_response, dict):
        models = list_response.get("models", [])

    model_names: list[str] = []
    for model in models or []:
        if isinstance(model, str):
            name = model
        elif isinstance(model, dict):
            name = model.get("model") or model.get("name")
        else:
            name = getattr(model, "model", None) or getattr(model, "name", None)

        if name:
            model_names.append(str(name))

    return sorted(set(model_names), key=str.lower)


def select_model_options(
    available_models: list[str],
    allowed_models: list[str],
) -> list[str]:
    if not available_models:
        return [model for model in allowed_models if model != "*"]

    if allowed_models == ["*"]:
        return available_models

    available_lookup = {model.lower(): model for model in available_models}
    selected: list[str] = []
    selected_keys: set[str] = set()

    for allowed_model in allowed_models:
        candidates = [allowed_model]
        if ":" not in allowed_model:
            candidates.append(f"{allowed_model}:latest")

        for candidate in candidates:
            actual_model = available_lookup.get(candidate.lower())
            if actual_model and actual_model.lower() not in selected_keys:
                selected.append(actual_model)
                selected_keys.add(actual_model.lower())
                break

    return selected


@st.cache_resource(show_spinner=False)
def get_ollama_client(host: str, timeout_seconds: float) -> Client:
    return Client(host=host or None, timeout=timeout_seconds)


@st.cache_data(ttl=60, show_spinner=False)
def list_available_models(host: str, timeout_seconds: float) -> list[str]:
    try:
        client = get_ollama_client(host, timeout_seconds)
        return extract_model_names(client.list())
    except Exception:
        LOGGER.warning("Unable to list Ollama models", exc_info=True)
        return []


@st.cache_resource(show_spinner=False)
def load_knowledge_base(
    signature: tuple[tuple[str, int, int], ...],
) -> dict[str, object]:
    chunks: list[dict[str, object]] = []
    errors: list[str] = []

    for path_string, _size, _mtime in signature:
        path = Path(path_string)
        try:
            reader = PdfReader(str(path))
        except Exception as error:
            LOGGER.exception("Failed to read PDF %s", path)
            errors.append(f"{path.name}: {error}")
            continue

        for page_number, page in enumerate(reader.pages, start=1):
            try:
                page_text = clean_text(page.extract_text() or "")
            except Exception as error:
                LOGGER.exception("Failed to extract text from %s page %s", path, page_number)
                errors.append(f"{path.name} page {page_number}: {error}")
                continue

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

    return {"chunks": chunks, "idf": idf, "errors": errors}


def retrieve_chunks(
    knowledge_base: dict[str, object],
    query: str,
    top_k: int,
    min_score: float = 0.0,
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
        if score >= min_score:
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
    history_limit: int = DEFAULT_MAX_HISTORY_MESSAGES,
) -> list[dict[str, str]]:
    if not use_playbooks:
        return history[-history_limit:] + [{"role": "user", "content": user_prompt}]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history[-history_limit:])
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


def extract_assistant_reply(response: Any) -> str:
    message = getattr(response, "message", None)
    if message is not None:
        content = getattr(message, "content", None)
        if content is not None:
            return str(content)
        if isinstance(message, dict):
            return str(message.get("content", ""))

    if isinstance(response, dict):
        return str(response.get("message", {}).get("content", ""))

    return ""


def main() -> None:
    st.set_page_config(page_title="Planview EPPM Chatbot", layout="centered")

    if not require_authentication():
        return

    st.title("Planview EPPM Chatbot")

    pdf_paths = find_pdf_paths()
    signature = document_signature(pdf_paths)
    knowledge_base = (
        load_knowledge_base(signature) if signature else {"chunks": [], "idf": {}, "errors": []}
    )
    indexed_chunks = knowledge_base.get("chunks", [])

    ollama_host = get_config_value("OLLAMA_HOST")
    ollama_timeout = get_float_config(
        "OLLAMA_TIMEOUT_SECONDS",
        DEFAULT_OLLAMA_TIMEOUT_SECONDS,
    )
    allowed_models = configured_allowed_models()
    available_models = list_available_models(ollama_host, ollama_timeout)
    model_options = select_model_options(available_models, allowed_models)

    if not model_options:
        model_options = available_models or DEFAULT_ALLOWED_MODELS.copy()

    with st.sidebar:
        st.header("Settings")

        model_name = st.selectbox("Ollama model", model_options, index=0)
        temperature = st.slider("Temperature", 0.0, 1.5, 0.2, 0.1)
        allow_free_chat = get_bool_config("ALLOW_FREE_CHAT", False)
        use_playbooks = (
            st.toggle("Use playbooks", value=True)
            if allow_free_chat
            else True
        )
        top_k = st.slider("Retrieved excerpts", 3, 8, 5)
        min_score = st.slider(
            "Minimum match score",
            0.0,
            0.20,
            get_float_config("MIN_RETRIEVAL_SCORE", DEFAULT_MIN_RETRIEVAL_SCORE),
            0.01,
        )
        show_context = st.toggle("Show retrieved excerpts", value=False)

        if st.button("Refresh playbooks"):
            load_knowledge_base.clear()
            list_available_models.clear()
            st.rerun()

        st.divider()
        if not is_authentication_configured():
            st.warning("Authentication is not configured.")
        if available_models:
            st.caption(f"{len(available_models)} Ollama models available")
        else:
            st.warning("Ollama models could not be verified.")

        st.divider()
        st.subheader("Indexed PDFs")
        if pdf_paths:
            for path in pdf_paths:
                st.caption(path.name)
            st.caption(f"{len(indexed_chunks)} text chunks loaded")
            if knowledge_base.get("errors"):
                st.warning(f"{len(knowledge_base['errors'])} indexing issue(s)")
        else:
            st.warning("No PDFs found. Configure PLAYBOOK_DOCS_DIR or PLAYBOOK_PDF_PATHS.")

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": GREETING}]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_prompt = st.chat_input("Ask about Planview EPPM...")

    if user_prompt:
        max_prompt_chars = get_int_config("MAX_PROMPT_CHARS", DEFAULT_MAX_PROMPT_CHARS)
        if len(user_prompt) > max_prompt_chars:
            st.warning(f"Question is too long. Limit it to {max_prompt_chars} characters.")
            return

        prior_history = st.session_state.messages.copy()
        st.session_state.messages.append({"role": "user", "content": user_prompt})

        with st.chat_message("user"):
            st.markdown(user_prompt)

        retrieval_query = build_retrieval_query(prior_history, user_prompt)
        matches = (
            retrieve_chunks(knowledge_base, retrieval_query, top_k, min_score)
            if use_playbooks
            else []
        )
        context = format_context(matches)
        model_messages = build_model_messages(
            prior_history,
            user_prompt,
            context,
            use_playbooks,
            get_int_config("MAX_HISTORY_MESSAGES", DEFAULT_MAX_HISTORY_MESSAGES),
        )

        if use_playbooks and not matches:
            assistant_reply = (
                "I could not find relevant playbook excerpts for that question."
            )
            with st.chat_message("assistant"):
                st.markdown(assistant_reply)

            st.session_state.messages.append(
                {"role": "assistant", "content": assistant_reply}
            )
            LOGGER.info("No retrieval matches for prompt: %s", user_prompt)
            return

        try:
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    client = get_ollama_client(ollama_host, ollama_timeout)
                    response = client.chat(
                        model=model_name,
                        messages=model_messages,
                        options={"temperature": temperature},
                    )

                    assistant_reply = extract_assistant_reply(response)
                    if not assistant_reply:
                        raise RuntimeError("Model response did not include assistant content.")

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

        except Exception:
            LOGGER.exception("Error generating response")
            with st.chat_message("assistant"):
                st.error(
                    "I could not connect to the model service. "
                    "Check the app logs and Ollama service health."
                )


if __name__ == "__main__":
    main()
