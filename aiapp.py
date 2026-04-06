import streamlit as st
from ollama import chat

st.set_page_config(page_title="Nakul Chatbot", page_icon="🤖", layout="centered")

st.title("🤖 Nakul Chatbot")

with st.sidebar:
    st.header("Settings")

    model_options = [
        "llama3.2",
        "deepseek-r1:7b",
        "qwen3:8b",
    ]

    model_name = st.selectbox("Select Ollama model", model_options, index=0)
    temperature = st.slider("Temperature", 0.0, 1.5, 0.7, 0.1)

    st.caption("Make sure Ollama is running locally and the selected model is pulled.")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hi Nakul! I am your chatbot. Ask me anything.",
        }
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_prompt = st.chat_input("Type your message...")

if user_prompt:
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    with st.chat_message("user"):
        st.markdown(user_prompt)

    try:
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = chat(
                    model=model_name,
                    messages=st.session_state.messages,
                    options={
                        "temperature": temperature
                    },
                )

                assistant_reply = response["message"]["content"]
                st.markdown(assistant_reply)

        st.session_state.messages.append(
            {"role": "assistant", "content": assistant_reply}
        )

    except Exception as e:
        with st.chat_message("assistant"):
            st.error(f"Error connecting to Ollama: {e}")