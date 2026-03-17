import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Use this to swip from provider. Feel free to change to any provider you like that uses LangChain interfaces.
PROVIDER    = "groq"          # "groq" or "google"

AGENT_MODEL = "gemini-2.5-flash"          # used when PROVIDER = "google"
JUDGE_MODEL = "gemini-2.5-flash"          # used when PROVIDER = "google"

GROQ_AGENT_MODEL = "llama-3.3-70b-versatile"   # used when PROVIDER = "groq"
GROQ_JUDGE_MODEL = "llama-3.3-70b-versatile"   # used when PROVIDER = "groq"


def make_llm(role: str = "agent", temperature: float = 0):
    """
    role: "agent" or "judge"
    Returns the correct LLM based on PROVIDER setting.
    """
    if PROVIDER == "groq":
        from langchain_groq import ChatGroq
        model = GROQ_AGENT_MODEL if role == "agent" else GROQ_JUDGE_MODEL
        return ChatGroq(
            model=model,
            temperature=temperature,
            api_key=os.getenv("GROQ_API_KEY"),
        )

    elif PROVIDER == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        model = AGENT_MODEL if role == "agent" else JUDGE_MODEL
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            max_retries=2,
        )

    else:
        raise ValueError(f"Unknown provider: {PROVIDER}. Use 'groq' or 'google'.")


agent_llm = make_llm("agent")
judge_llm  = make_llm("judge")