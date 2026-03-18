import json
import re
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from database import run_query
from prompts import build_system_prompt, BASELINE_PROMPT
from config import agent_llm, AGENT_MODEL
from token_tracker import log_call, extract_usage
import logging

logger = logging.getLogger(__name__)


# ── Tool input schemas ────────────────────────────────────────────────────────

class QueryDatabaseInput(BaseModel):
    sql: str = Field(description="A valid DuckDB SQL SELECT query to execute against the database.")

class GenerateVisualizationInput(BaseModel):
    data: str = Field(description="The JSON string result from query_database.")
    chart_type: str = Field(description="One of: bar, line, pie.")
    x_key: str = Field(description="Column name for the X axis or pie labels.")
    y_key: str = Field(description="Column name for the Y axis or pie values.")
    title: str = Field(description="A clear, business-friendly chart title.")

class GenerateInsightInput(BaseModel):
    data: str = Field(description="The JSON string result from query_database.")
    question: str = Field(description="The original question the user asked.")


# ── Tool functions ─────────────────────────────────────────────────────────────

def _query_database(sql: str) -> str:
    result = run_query(sql)
    if not result["success"]:
        return f"Query failed: {result['error']}. Please fix the SQL and try again."
    if result["row_count"] == 0:
        return "The query returned no results."
    return json.dumps(result, default=str)


def _generate_visualization(data: str, chart_type: str, x_key: str, y_key: str, title: str) -> str:
    try:
        parsed = json.loads(data) if isinstance(data, str) else data
    except Exception:
        parsed = {}
    rows = parsed.get("rows", parsed) if isinstance(parsed, dict) else parsed
    return json.dumps({
        "type": "chart",
        "chart_type": chart_type,
        "x_key": x_key,
        "y_key": y_key,
        "title": title,
        "data": {"rows": rows},
    })


def _generate_insight(data: str, question: str) -> str:
    return json.dumps({
        "type": "insight",
        "data": json.loads(data) if isinstance(data, str) else data,
        "question": question,
    })


# ── Tools ──────────────────────────────────────────────────────────────────────

TOOLS = [
    StructuredTool(
        name="query_database",
        description="Execute a SQL SELECT query against the Jaffle Shop DuckDB database. Use this whenever the user asks a question that requires data.",
        func=_query_database,
        args_schema=QueryDatabaseInput,
    ),
    StructuredTool(
        name="generate_visualization",
        description="Generate a chart specification from query results. Call this AFTER query_database when the data would be clearer as a chart.",
        func=_generate_visualization,
        args_schema=GenerateVisualizationInput,
    ),
    StructuredTool(
        name="generate_insight",
        description="Write a short plain-English business insight based on query results.",
        func=_generate_insight,
        args_schema=GenerateInsightInput,
    ),
]

tools_by_name = {t.name: t for t in TOOLS}


# ── Response cleaner ───────────────────────────────────────────────────────────

def _clean_response(text: str) -> str:
    if not text:
        return text

    text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"STEP\s+\d+\s*[—\-]+.*?(?=STEP\s+\d+|ANSWER:|$)", "", text, flags=re.DOTALL)
    text = re.sub(r"^ANSWER:\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^DATA:\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^ASSUMPTIONS:\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^FOLLOW-UP:\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^FOLLOW-UP QUESTION:\s*", "", text, flags=re.MULTILINE)
    text = re.sub(
        r"<(?:role|reasoning_protocol|output_format|ambiguity_handling|"
        r"error_handling|database_schema|reasoning_steps)[^>]*>.*?"
        r"</(?:role|reasoning_protocol|output_format|ambiguity_handling|"
        r"error_handling|database_schema|reasoning_steps)>",
        "", text, flags=re.DOTALL
    )
    leaked_markers = [
        "## Your Reasoning Process", "## How to Respond", "## Database Schema",
        "## Rules", "## Hard Rules", "## Your Personality",
        "## How to Answer Questions", "## Output Format", "## Available Tools",
        "## Reasoning Protocol", "## Tool Call Order", "## Ambiguity Handling",
        "## Error Handling", "## Visualization Rules", "## SQL Guidelines",
        "## SQL Rules", "## Example Interaction", "You are a data assistant",
        "You are a thoughtful data analyst", "Before writing any SQL",
        "Do your reasoning silently", "Never repeat these instructions",
        "Always follow this sequence", "You have three tools",
        "You have access to a DuckDB",
    ]
    lines = text.split("\n")
    cleaned_lines = [
        line for line in lines
        if not any(line.strip().startswith(marker) for marker in leaked_markers)
    ]
    text = "\n".join(cleaned_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── Agent ──────────────────────────────────────────────────────────────────────

def run_agent(
    user_message: str,
    schema: str,
    base_prompt: str = BASELINE_PROMPT,
    history: list[dict] = None,
    session_id: str = None,
) -> dict:
    system_prompt = build_system_prompt(base_prompt, schema)
    llm_with_tools = agent_llm.bind_tools(TOOLS)

    messages = [SystemMessage(content=system_prompt)]

    if history:
        for turn in history:
            role = turn.get("role", "")
            content = turn.get("content", "")
            if not content:
                continue
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=user_message))

    chart_spec = None
    sql_queries = []      # ← capture every SQL call
    max_iterations = 5

    for i in range(max_iterations):
        try:
            response = llm_with_tools.invoke(messages)
        except Exception as e:
            return {
                "text": f"The agent encountered an error: {str(e)}",
                "chart": None,
                "sql_queries": sql_queries,
            }

        in_tok, out_tok = extract_usage(response)
        log_call(
            caller="agent",
            model=AGENT_MODEL,
            input_tokens=in_tok,
            output_tokens=out_tok,
            session_id=session_id,
        )

        messages.append(response)

        finish_reason = ""
        if hasattr(response, "response_metadata"):
            finish_reason = response.response_metadata.get("finish_reason", "")
        if finish_reason == "MALFORMED_FUNCTION_CALL":
            messages.append(HumanMessage(content="Your tool call was malformed. Please try again."))
            continue

        if not response.tool_calls:
            break

        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # ── Capture SQL ────────────────────────────────────────────────────
            if tool_name == "query_database":
                sql = tool_args.get("sql", "")
                logger.info(f"SQL EXECUTED: {sql}")
                sql_queries.append(sql)

            if tool_name not in tools_by_name:
                tool_result = f"Unknown tool: {tool_name}"
            else:
                try:
                    tool_result = tools_by_name[tool_name].invoke(tool_args)
                except Exception as e:
                    tool_result = f"Tool error: {str(e)}"

            if tool_name == "generate_visualization":
                try:
                    chart_spec = json.loads(tool_result)
                except Exception:
                    pass

            messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_call["id"]))

    # ── Extract final text ─────────────────────────────────────────────────────
    final_text = ""
    for msg in reversed(messages):
        if isinstance(msg, (HumanMessage, ToolMessage)):
            continue
        content = msg.content if hasattr(msg, "content") else ""
        if isinstance(content, list):
            content = " ".join(
                p.get("text", "") if isinstance(p, dict) else str(p)
                for p in content
            ).strip()
        if content.strip():
            final_text = content.strip()
            break

    return {
        "text": _clean_response(final_text),
        "chart": chart_spec,
        "sql_queries": sql_queries,   # ← included in every response
    }