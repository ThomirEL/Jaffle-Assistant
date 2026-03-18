import logging
import json
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import get_schema
from agent import run_agent
from evals.multi_agent import run_multi_agent
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
    history: list[dict] = []


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
    logger.info(f"{'='*60}")

    try:
        # Run agent with a 90 second timeout
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                #lambda: run_agent(request.message, SCHEMA, base_prompt=BASELINE_PROMPT)
                lambda: run_multi_agent(request.message, SCHEMA)
            ),
            timeout=120.0
        )
    except asyncio.TimeoutError:
        logger.error("Agent timed out after 120s")
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
        logger.info(f"CHART: type={chart.get('chart_type')}  "
                    f"x={chart.get('x_key')}  "
                    f"y={chart.get('y_key')}  "
                    f"title={chart.get('title')}")
        logger.info(f"CHART DATA: {len(chart.get('data', {}).get('rows', []))} rows")
    else:
        logger.info("CHART: none")

    logger.info(f"{'='*60}\n")

    return result