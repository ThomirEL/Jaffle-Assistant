import logging
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import get_schema
from agent import run_agent
from prompts import BASELINE_PROMPT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SCHEMA = get_schema()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []  # [{"role": "user", "content": "..."}, ...]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/schema")
def schema():
    return {"schema": SCHEMA}


@app.post("/chat")
async def chat(request: ChatRequest):
    logger.info(f"\n{'='*60}")
    logger.info(f"USER: {request.message}")
    logger.info(f"History length: {len(request.history)} messages")
    logger.info(f"{'='*60}")

    try:
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: run_agent(
                    request.message,
                    SCHEMA,
                    base_prompt=BASELINE_PROMPT,
                    history=request.history,
                )
            ),
            timeout=90.0
        )
    except asyncio.TimeoutError:
        logger.error("Agent timed out after 90s")
        raise HTTPException(
            status_code=504,
            detail="The agent took too long to respond. Try a more specific question."
        )
    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    logger.info(f"TEXT: {result.get('text', 'EMPTY')}")
    if result.get("chart"):
        chart = result["chart"]
        logger.info(f"CHART: type={chart.get('chart_type')} rows={len(chart.get('data', {}).get('rows', []))}")
    else:
        logger.info("CHART: none")
    logger.info(f"{'='*60}\n")

    return result