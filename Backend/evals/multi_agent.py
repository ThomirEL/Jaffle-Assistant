import json
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from database import run_query
from config import agent_llm


# ── Tool input schemas ─────────────────────────────────────────────────────────

class QueryDatabaseInput(BaseModel):
    sql: str = Field(description="A valid DuckDB SQL SELECT query to execute against the database.")


# ── Tool functions ─────────────────────────────────────────────────────────────

def _query_database(sql: str) -> str:
    result = run_query(sql)
    if not result["success"]:
        return f"Query failed: {result['error']}. Please fix the SQL and try again."
    if result["row_count"] == 0:
        return "The query returned no results."
    return json.dumps(result, default=str)


def _make_sql_tool():
    return StructuredTool(
        name="execute_sql",
        description="Execute a validated SQL SELECT query against the DuckDB database.",
        func=_query_database,
        args_schema=QueryDatabaseInput,
    )


# ── Sub-agent helpers ──────────────────────────────────────────────────────────

def _invoke_with_tools(system: str, user: str, tools: list) -> tuple[str, list]:
    """
    Runs a single sub-agent loop with the given tools.
    Returns (final_text, all_messages).
    """
    llm_with_tools = agent_llm.bind_tools(tools)
    tools_by_name = {t.name: t for t in tools}

    messages = [
        SystemMessage(content=system),
        HumanMessage(content=user),
    ]

    for _ in range(4):
        try:
            response = llm_with_tools.invoke(messages)
        except Exception as e:
            return f"Sub-agent error: {str(e)}", messages

        messages.append(response)

        if not response.tool_calls:
            break

        for tc in response.tool_calls:
            if tc["name"] in tools_by_name:
                try:
                    result = tools_by_name[tc["name"]].invoke(tc["args"])
                except Exception as e:
                    result = f"Tool error: {str(e)}"
            else:
                result = f"Unknown tool: {tc['name']}"

            messages.append(
                ToolMessage(content=str(result), tool_call_id=tc["id"])
            )

    # Extract final text
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
            return content.strip(), messages

    return "", messages


# ── Standard sub-agents ────────────────────────────────────────────────────────

def sql_agent(question: str, schema: str) -> dict:
    """Runs a SQL query and returns raw results."""
    system = f"""You are a SQL specialist for a DuckDB database.
Your ONLY job is to write correct SQL and return the results.
Do not explain or add narrative — just query and return data.

Schema:
{schema}

Rules:
- Only use tables in the schema above.
- Only SELECT queries. Never DROP, DELETE, UPDATE, INSERT.
- If the question cannot be answered from the schema, respond with exactly: CANNOT_ANSWER: <reason>
- If the question is ambiguous, respond with exactly: AMBIGUOUS: <one clarifying question>
"""

    text, _ = _invoke_with_tools(system, question, [_make_sql_tool()])

    if text.startswith("CANNOT_ANSWER:"):
        return {"success": False, "reason": text.replace("CANNOT_ANSWER:", "").strip()}
    if text.startswith("AMBIGUOUS:"):
        return {"success": False, "reason": text.replace("AMBIGUOUS:", "").strip(), "ambiguous": True}

    try:
        data = json.loads(text)
        return {"success": True, "data": data}
    except Exception:
        return {"success": True, "data": {"raw": text}}


def chart_agent(question: str, query_result: dict) -> dict | None:
    """Decides if a chart is appropriate and returns a spec."""
    system = """You are a data visualisation specialist.
Given a business question and query results, decide:
1. Should this be visualised as a chart?
2. If yes — what type (bar, line, pie) and which columns?

Rules:
- Use bar for rankings and comparisons.
- Use line for time series and trends.
- Use pie for proportions (max 6 categories).
- Do NOT suggest a chart for single numbers or text answers.
- If no chart is appropriate, respond with exactly: NO_CHART

If a chart is appropriate, respond with ONLY a JSON object:
{"chart_type": "bar", "x_key": "product_name", "y_key": "revenue", "title": "Top Products by Revenue"}
"""

    data_preview = json.dumps(query_result, default=str)[:1000]
    prompt = f"Question: {question}\n\nQuery result: {data_preview}"

    llm = agent_llm
    response = llm.invoke([SystemMessage(content=system), HumanMessage(content=prompt)])
    text = response.content.strip()

    if "NO_CHART" in text:
        return None

    # Strip markdown fences if present
    import re
    text = re.sub(r"```(?:json)?", "", text).strip()

    try:
        spec = json.loads(text)
        spec["data"] = query_result
        return spec
    except Exception:
        return None


def insight_agent(question: str, query_result: dict, chart_spec: dict | None) -> str:
    """Writes a plain-English business narrative."""
    system = """You are a business analyst writing insights for non-technical stakeholders.
Write 2-3 sentences maximum. Lead with the most important finding.
Use plain English — no jargon, no SQL, no column names.
Be specific with numbers."""

    data_preview = json.dumps(query_result, default=str)[:800]
    chart_context = f"A {chart_spec['chart_type']} chart was also generated." if chart_spec else ""

    response = agent_llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=f"Question: {question}\nData: {data_preview}\n{chart_context}\n\nWrite a short business insight."),
    ])
    return response.content.strip()


# ── Reasoning sub-agents ───────────────────────────────────────────────────────

def reasoning_sql_agent(question: str, schema: str) -> dict:
    """SQL agent that reasons step-by-step before writing any query."""
    system = f"""You are a SQL specialist for a DuckDB database.
Before writing any SQL, reason carefully inside <thinking> tags:

<thinking>
STEP 1 — What is the user asking? What metric does it map to?
STEP 2 — Which tables and columns are needed? Do they exist in the schema?
STEP 3 — Can this be answered? If not, what is closest? State assumptions.
STEP 4 — Draft the SQL. Use revenue = SUM(oi.quantity * oi.unit_price).
          Default filter: WHERE o.status = 'completed'. LIMIT 20 for lists.
STEP 5 — Validate: would this run on DuckDB? Does it answer the question?
</thinking>

Then call execute_sql with your validated query.

Schema:
{schema}

Hard rules:
- Only SELECT queries. Never DROP, DELETE, UPDATE, INSERT.
- If the question is unanswerable from the schema, respond: CANNOT_ANSWER: <reason>
- If the question is ambiguous, respond: AMBIGUOUS: <one clarifying question>
"""

    text, _ = _invoke_with_tools(system, question, [_make_sql_tool()])

    # Strip thinking block before checking response type
    if "</thinking>" in text:
        text = text.split("</thinking>")[-1].strip()

    if text.startswith("CANNOT_ANSWER:"):
        return {"success": False, "reason": text.replace("CANNOT_ANSWER:", "").strip()}
    if text.startswith("AMBIGUOUS:"):
        return {"success": False, "reason": text.replace("AMBIGUOUS:", "").strip(), "ambiguous": True}

    try:
        data = json.loads(text)
        return {"success": True, "data": data}
    except Exception:
        return {"success": True, "data": {"raw": text}}


def reasoning_chart_agent(question: str, query_result: dict) -> dict | None:
    """Chart agent that reasons about visualisation before committing."""
    system = """You are a data visualisation specialist.
Before deciding on a chart, reason inside <thinking> tags:

<thinking>
- How many data points are there? Is this a single number or a list?
- Does the question imply a comparison, trend, or breakdown?
- What chart type fits: bar (ranking/comparison), line (trend), pie (proportion)?
- Are there too many categories for a pie (>6)? Use bar instead.
- Would a table be clearer than a chart here?
</thinking>

Then respond with either:
- Exactly NO_CHART if no visualisation adds value
- A JSON object: {"chart_type": "bar", "x_key": "col1", "y_key": "col2", "title": "..."}
"""

    import re
    data_preview = json.dumps(query_result, default=str)[:1000]
    response = agent_llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=f"Question: {question}\n\nQuery result: {data_preview}"),
    ])

    text = response.content.strip()
    if "</thinking>" in text:
        text = text.split("</thinking>")[-1].strip()
    text = re.sub(r"```(?:json)?", "", text).strip()

    if "NO_CHART" in text:
        return None

    try:
        spec = json.loads(text)
        spec["data"] = query_result
        return spec
    except Exception:
        return None


def reasoning_insight_agent(question: str, query_result: dict, chart_spec: dict | None) -> str:
    """Insight agent that reasons about the key finding before writing."""
    system = """You are a business analyst writing insights for non-technical stakeholders.
Before writing, reason inside <thinking> tags:

<thinking>
- What is the single most important number or finding?
- Is there anything surprising or worth flagging?
- What context would make this more useful to a business user?
</thinking>

Then write 2-3 sentences of plain-English insight. Lead with the most important finding.
Never use SQL, column names, or technical jargon. Be specific with numbers.
"""

    data_preview = json.dumps(query_result, default=str)[:800]
    chart_context = f"A {chart_spec['chart_type']} chart was generated." if chart_spec else ""

    response = agent_llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=f"Question: {question}\nData: {data_preview}\n{chart_context}"),
    ])

    text = response.content.strip()
    if "</thinking>" in text:
        text = text.split("</thinking>")[-1].strip()
    return text


# ── Orchestrators ──────────────────────────────────────────────────────────────

def run_multi_agent(question: str, schema: str) -> dict:
    """Standard multi-agent: SQL → Chart → Insight."""
    sql_result = sql_agent(question, schema)

    if not sql_result["success"]:
        reason = sql_result.get("reason", "")
        if sql_result.get("ambiguous"):
            return {"text": f"Could you clarify: {reason}", "chart": None}
        return {
            "text": f"I wasn't able to answer that from the available data. {reason}",
            "chart": None,
        }

    query_data = sql_result["data"]
    chart_spec = chart_agent(question, query_data)
    narrative = insight_agent(question, query_data, chart_spec)

    return {"text": narrative, "chart": chart_spec}


def run_reasoning_multi_agent(question: str, schema: str) -> dict:
    """Reasoning multi-agent: each sub-agent thinks before acting."""
    sql_result = reasoning_sql_agent(question, schema)

    if not sql_result["success"]:
        reason = sql_result.get("reason", "")
        if sql_result.get("ambiguous"):
            return {"text": f"Could you clarify: {reason}", "chart": None}
        return {
            "text": f"I wasn't able to answer that from the available data. {reason}",
            "chart": None,
        }

    query_data = sql_result["data"]
    chart_spec = reasoning_chart_agent(question, query_data)
    narrative = reasoning_insight_agent(question, query_data, chart_spec)

    return {"text": narrative, "chart": chart_spec}