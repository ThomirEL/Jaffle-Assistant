import json
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from database import run_query
from prompts import build_system_prompt, BASELINE_PROMPT
from config import agent_llm


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
    return json.dumps({
        "type": "chart",
        "chart_type": chart_type,
        "x_key": x_key,
        "y_key": y_key,
        "title": title,
        "data": json.loads(data) if isinstance(data, str) else data,
    })


def _generate_insight(data: str, question: str) -> str:
    return json.dumps({
        "type": "insight",
        "data": json.loads(data) if isinstance(data, str) else data,
        "question": question,
    })


# ── Tools ─────────────────────────────────────────────────────────────────────

TOOLS = [
    StructuredTool(
        name="query_database",
        description="Execute a SQL SELECT query against the Jaffle Shop DuckDB database. Use this whenever the user asks a question that requires data.",
        func=_query_database,
        args_schema=QueryDatabaseInput,
    ),
    StructuredTool(
        name="generate_visualization",
        description="Generate a chart specification from query results. Call this AFTER query_database when the data would be clearer as a chart — for rankings, trends, or breakdowns.",
        func=_generate_visualization,
        args_schema=GenerateVisualizationInput,
    ),
    StructuredTool(
        name="generate_insight",
        description="Write a short plain-English business insight based on query results. Call this to add narrative context on top of numbers.",
        func=_generate_insight,
        args_schema=GenerateInsightInput,
    ),
]

tools_by_name = {t.name: t for t in TOOLS}


# ── Agent ──────────────────────────────────────────────────────────────────────

def run_agent(user_message: str, schema: str, base_prompt: str = BASELINE_PROMPT) -> dict:
    """
    Main agent loop. Works with both Groq and Google providers.
    base_prompt: the system prompt template — must contain {schema} placeholder
                 OR will have schema appended automatically.
    """
    system_prompt = build_system_prompt(base_prompt, schema)
    
    # Bind tools fresh each call — required for Groq
    llm_with_tools = agent_llm.bind_tools(TOOLS)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]

    chart_spec = None
    max_iterations = 5

    for i in range(max_iterations):
        try:
            response = llm_with_tools.invoke(messages)
        except Exception as e:
            return {
                "text": f"The agent encountered an error: {str(e)}",
                "chart": None,
            }

        messages.append(response)

        # Handle Gemini malformed calls
        finish_reason = ""
        if hasattr(response, "response_metadata"):
            finish_reason = response.response_metadata.get("finish_reason", "")
        if finish_reason == "MALFORMED_FUNCTION_CALL":
            messages.append(
                HumanMessage(content="Your tool call was malformed. Please try again with valid arguments.")
            )
            continue

        # No tool calls — agent is done
        if not response.tool_calls:
            break

        # Execute each tool call
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

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

            messages.append(
                ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_call["id"],
                )
            )

    # ── Extract final text ─────────────────────────────────────────────────────
    final_text = ""
    for msg in reversed(messages):
        if isinstance(msg, (HumanMessage, ToolMessage)):
            continue
        content = msg.content if hasattr(msg, "content") else ""
        if isinstance(content, list):
            text_parts = [
                p.get("text", "") if isinstance(p, dict) else str(p)
                for p in content
            ]
            content = " ".join(text_parts).strip()
        if content.strip():
            final_text = content.strip()
            break

    return {
        "text": final_text,
        "chart": chart_spec,
    }