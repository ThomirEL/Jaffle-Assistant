# Jaffle Assistant

An AI-powered chat assistant for the Jaffle Shop dataset. Ask business questions
in plain English and get answers backed by real data, with charts when relevant.

Built with LangChain, FastAPI, DuckDB, and React (with Nivo)

---

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Google AI Studio API key](https://aistudio.google.com) (free tier works fine)
- Python 3.11+ (for running evals locally, not needed for the app itself)

---

## Setup

**1. Add your API keys**

Copy `.env.example` to `.env` and fill in your keys:
```
GOOGLE_API_KEY=your_gemini_key_here
GROQ_API_KEY=your_groq_key_here
OPENROUTER_API_KEY=your_openrouter_key_here
```

You only need the keys for the providers you intend to use.
Get a free Groq key at [console.groq.com](https://console.groq.com).
Get a free OpenRouter key at [openrouter.ai](https://openrouter.ai).
Get a free Gemini key at [ai.google.dev](https://ai.google.dev/gemini-api/docs)

**2. Configure your provider**

Open `backend/config.py` and set your preferred provider and models:
```python
AGENT_PROVIDER = "groq"       # "groq", "google", "openrouter", or "ollama"
JUDGE_PROVIDER = "groq"       # same options. Only used for running evaluations

AGENT_MODEL = "llama-3.3-70b-versatile"
JUDGE_MODEL  = "llama-3.3-70b-versatile" # Only used for running evaluations
```

**3. Run the app**
```bash
docker compose up --build
```

Frontend → http://localhost:3000
API docs → http://localhost:8000/docs

---

## Data Exploration Notebook

To explore the raw dataset before chatting with the agent:
```bash
pip install -r Data Exploration/requirements.txt
jupyter notebook Data Exploration/data_exploration.ipynb
```

The notebook walks through the database tables, schemas, and sample rows.

---

## Running Evaluations

Evals run locally against your Python environment — they do not require Docker.

**1. Install dependencies**
```bash
cd backend
pip install -r Backend/requirements.txt
```

**2. Run the eval suite**
```bash
cd backend
python evals/run_evals.py
```
Depending on what type of evaluation you want to run, you need to change the settings. 
If you want to test the 4 different agent variants (baseline, reasoning, multi-agent, reasoning multi-agent) set TYPE_OF_RUN to "agents"

If you want to test the 4 different prompt variations of the baseline set TYPE_OF_RUN to "prompts"

If you want to test the updated baseline prompt set TYPE_OF_RUN to "updated_baseline"

If you want to test for consistency of SQL queries set TYPE_OF_RUN to "sql_updated_baseline"

Results are saved to `backend/evals/eval_results/eval_results.json` and
`backend/evals/eval_results/eval_summary.txt` after each run.

**3. Change the experiment name between runs**

Open `backend/evals/run_evals.py` and update the experiment name at the top
so runs don't overwrite each other in MLflow:
```python
EXPERIMENT_NAME = "jaffle-agent-evals-run-2"
```

---

## Viewing Eval Results in MLflow

After running evals, open the MLflow UI to compare variants side by side.
```bash
cd backend/evals/eval_results
mlflow ui --backend-store-uri ./mlruns
```

Then open http://localhost:5000 in your browser.

To compare runs across experiments, use the MLflow UI sidebar to switch
between experiment names.

---

