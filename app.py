"""General-purpose chat app using the same Ollama models as aiapp.py."""

import logging

import streamlit as st

from aiapp import (
    DEFAULT_ALLOWED_MODELS,
    DEFAULT_MAX_HISTORY_MESSAGES,
    DEFAULT_MAX_PROMPT_CHARS,
    DEFAULT_OLLAMA_TIMEOUT_SECONDS,
    configured_allowed_models,
    extract_assistant_reply,
    get_config_value,
    get_float_config,
    get_int_config,
    get_ollama_client,
    is_authentication_configured,
    list_available_models,
    require_authentication,
    select_model_options,
)

LOGGER = logging.getLogger(__name__)
GREETING = "Hi! Ask me anything."
SYSTEM_PROMPT = (
    "You are a helpful, general-purpose AI assistant. Answer clearly and accurately. "
    "If you are unsure, say so. Use plain language and include useful detail when needed."
)


def main() -> None:
    st.set_page_config(page_title="General AI Chat", page_icon="💬", layout="centered")

    if not require_authentication():
        return

    ollama_host = get_config_value("OLLAMA_HOST")
    timeout = get_float_config("OLLAMA_TIMEOUT_SECONDS", DEFAULT_OLLAMA_TIMEOUT_SECONDS)
    available_models = list_available_models(ollama_host, timeout)
    model_options = select_model_options(
        available_models, configured_allowed_models()
    ) or available_models or DEFAULT_ALLOWED_MODELS.copy()

    with st.sidebar:
        st.header("Chat settings")
        model_name = st.selectbox("Model", model_options)
        temperature = st.slider("Temperature", 0.0, 1.5, 0.7, 0.1)
        if st.button("Clear conversation"):
            st.session_state.messages = [{"role": "assistant", "content": GREETING}]
            st.rerun()
        st.divider()
        if available_models:
            st.caption(f"{len(available_models)} Ollama model(s) available")
        else:
            st.warning("Could not verify Ollama models. Check that Ollama is running.")
        if not is_authentication_configured():
            st.caption("Authentication is not configured.")

    st.title("General AI Chat")
    st.caption(f"Currently using **{model_name}**")

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": GREETING}]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_prompt = st.chat_input("Ask anything...")
    if not user_prompt:
        return

    max_chars = get_int_config("MAX_PROMPT_CHARS", DEFAULT_MAX_PROMPT_CHARS)
    if len(user_prompt) > max_chars:
        st.warning(f"Message is too long. Limit it to {max_chars} characters.")
        return

    history = st.session_state.messages[-get_int_config(
        "MAX_HISTORY_MESSAGES", DEFAULT_MAX_HISTORY_MESSAGES
    ):]
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history,
                {"role": "user", "content": user_prompt}]
    try:
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = get_ollama_client(ollama_host, timeout).chat(
                    model=model_name,
                    messages=messages,
                    options={"temperature": temperature},
                )
                reply = extract_assistant_reply(response)
                if not reply:
                    raise RuntimeError("Model response did not include assistant content.")
                st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})
    except Exception:
        LOGGER.exception("Error generating general chat response")
        with st.chat_message("assistant"):
            st.error("I could not connect to Ollama. Check that the service is running.")


if __name__ == "__main__":
    main()
