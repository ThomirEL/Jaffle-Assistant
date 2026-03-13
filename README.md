# Jaffle Assistant

An AI-powered chat assistant for the Jaffle Shop dataset. Ask business questions in plain English and get answers backed by live data, with charts where relevant.

Built with LangChain, Gemini 2.5 Flash, FastAPI, DuckDB, and React.

---

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Google AI Studio API key](https://aistudio.google.com) (free tier works fine)

---

## Setup

**1. Add your API key**

Copy `.env.example` to `.env` and fill in your key:

```
GOOGLE_API_KEY=your_key_here
```

**2. Run**

```bash
docker compose up --build
```

Frontend -> http://localhost:3000  
API docs -> http://localhost:8000/docs

---

## Data Exploration Notebook

To explore the raw dataset before chatting with the agent:

```bash
pip install -r backend/requirements.txt
jupyter notebook data_exploration.ipynb
```

The notebook walks through the database tables, schemas, and sample rows.