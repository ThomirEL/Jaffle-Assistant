import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openrouter import ChatOpenRouter

load_dotenv()

# Use this to swip from provider. Feel free to change to any provider you like that uses LangChain interfaces.
AGENT_PROVIDER = "openrouter"
JUDGE_PROVIDER = "openrouter"

GOOGLE_AGENT_MODEL = "gemini-2.5-flash"          # used when PROVIDER = "google"
GOOGLE_JUDGE_MODEL = "gemini-2.5-flash"          # used when PROVIDER = "google"

GROQ_AGENT_MODEL = "llama-3.3-70b-versatile"   # used when PROVIDER = "groq"
GROQ_JUDGE_MODEL = "llama-3.3-70b-versatile"   # used when PROVIDER = "groq"

OPENROUTER_AGENT_MODEL = "arcee-ai/trinity-large-preview:free"   # used when PROVIDER = "openrouter"
OPENROUTER_JUDGE_MODEL = "arcee-ai/trinity-large-preview:free"

AGENT_MODEL = ""

def make_llm(provider: str, temperature: float = 0):
    if provider == "groq":
        from langchain_groq import ChatGroq
        AGENT_MODEL = GROQ_AGENT_MODEL
        return ChatGroq(
            model=GROQ_AGENT_MODEL if provider == AGENT_PROVIDER else GROQ_JUDGE_MODEL,
            temperature=temperature,
            api_key=os.getenv("GROQ_API_KEY"),
        )

    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        AGENT_MODEL = GOOGLE_AGENT_MODEL
        return ChatGoogleGenerativeAI(
            model=GOOGLE_AGENT_MODEL if provider == AGENT_PROVIDER else GOOGLE_JUDGE_MODEL,
            temperature=temperature,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            max_retries=2,
        )

    elif provider == "openrouter":
        from langchain_openrouter import ChatOpenRouter
        AGENT_MODEL = OPENROUTER_AGENT_MODEL
        return ChatOpenRouter(
            model=OPENROUTER_AGENT_MODEL if provider == AGENT_PROVIDER else OPENROUTER_JUDGE_MODEL,
            temperature=temperature,
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )

    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'groq', 'google', 'ollama', or 'openrouter'.")


agent_llm = make_llm(AGENT_PROVIDER)
judge_llm  = make_llm(JUDGE_PROVIDER)