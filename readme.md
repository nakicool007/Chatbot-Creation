# Nakul Chatbot

This project is a local chatbot app built with Streamlit and Ollama. Right now it provides a simple chat interface where you can pick from a few local models, adjust temperature, and have a running conversation in the browser.

The current goal is to build a practical foundation for a larger chatbot portfolio. This app is the starting point: a lightweight local assistant that can grow into more capable tools, feature-rich assistants, and eventually task-specific agents.

## What This Chatbot Does

- Runs locally with Streamlit.
- Uses Ollama for local model inference.
- Lets you choose between supported local models in the sidebar.
- Keeps chat history during the current session.
- Exposes a temperature control for response style.

At the moment, the app supports these models if they are installed in Ollama:

- `llama3.2`
- `deepseek-r1:7b`
- `qwen3:8b`

## Project Direction

This chatbot is part of a broader build-out. The plan is to keep improving this app while also creating more chatbots with stronger capabilities, including:

- chatbots with better memory and context handling
- feature-specific assistants for focused workflows
- task-specific chatbots for domains like writing, research, planning, or automation
- agent-style systems that can perform multi-step tasks
- more advanced interfaces, tool usage, and integrations

The long-term direction is not just a single chatbot, but a collection of assistants with different purposes and levels of autonomy.

## Requirements

Install these before running the app:

- Python 3.10+
- [Ollama](https://ollama.com/)
- At least one supported Ollama model pulled locally

You will also need Python packages:

- `streamlit`
- `ollama`

## Installation

1. Clone this project or download it to your machine.
2. Open a terminal in the project folder.
3. Install the Python dependencies:

```powershell
pip install streamlit ollama
```

4. Make sure Ollama is installed and running.
5. Pull one or more of the supported models:

```powershell
ollama pull llama3.2
ollama pull deepseek-r1:7b
ollama pull qwen3:8b
```

## How To Run

Start the Streamlit app with:

```powershell
streamlit run aiapp.py
```

Then open the local URL shown in the terminal, usually:

```text
http://localhost:8501
```

## How To Use

1. Launch the app.
2. Choose an Ollama model from the sidebar.
3. Set the temperature to control how focused or creative responses should be.
4. Type a message into the chat box.
5. Continue the conversation as the session builds context.

## Notes

- Ollama must be running before the app can respond.
- The selected model must already be pulled locally.
- Chat history is stored in the Streamlit session state, so it lasts for the current session but is not permanent memory.
- If Ollama is unavailable, the app will show a connection error in the chat window.

## Current Stack

- Python
- Streamlit
- Ollama

## Next Steps

Planned improvements include:

- persistent conversation history
- better model management
- custom system prompts
- file and document input
- tool-enabled assistants
- workflow automation
- agent-based chatbot behavior
- dedicated chatbots for specific tasks and industries

## Vision

This repository represents the beginning of a larger chatbot-building journey. The idea is to keep iterating from a simple local assistant into more capable AI applications, including advanced assistants, domain-specific tools, and autonomous agents that can help with real tasks instead of only basic conversation.
