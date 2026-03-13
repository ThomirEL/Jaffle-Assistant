import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from database import run_query, get_schema
from prompts import build_system_prompt
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file

# Load the LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    max_retries=2,
)


# MCP - Tools for the agent to create visualizations or query the database. 
@tool
def query_database(sql: str) -> str:
    """
    Execute a SQL query against the Jaffle Shop DuckDB database.
    Use this whenever the user asks a question that requires data.
    Returns the query results as JSON.
    """
    result = run_query(sql)
    if not result["success"]:
        return f"Query failed with error: {result['error']}. Try fixing the SQL and run again."
    if result["row_count"] == 0:
        return "The query returned no results."
    return json.dumps(result, default=str)


@tool
def generate_visualization(
    data: str,
    chart_type: str,
    x_key: str,
    y_key: str,
    title: str,
) -> str:
    """
    Generate a chart specification from query results.
    Call this AFTER query_database when the data would be clearer as a chart.
    
    Args:
        data: The JSON string result from query_database
        chart_type: One of 'bar', 'line', 'pie'
        x_key: The column name to use for the X axis (or labels for pie)
        y_key: The column name to use for the Y axis (or values for pie)
        title: A clear, business-friendly chart title
    """
    return json.dumps({
        "type": "chart",
        "chart_type": chart_type,
        "x_key": x_key,
        "y_key": y_key,
        "title": title,
        "data": json.loads(data) if isinstance(data, str) else data,
    })


@tool
def generate_insight(data: str, question: str) -> str:
    """
    Write a short plain-English business insight based on query results.
    Call this to add narrative context on top of numbers.
    
    Args:
        data: The JSON string result from query_database
        question: The original question the user asked
    """
    # This just passes the data back with a flag — the agent writes the insight
    # naturally in its final response. The tool signals intent to the frontend.
    return json.dumps({
        "type": "insight",
        "data": json.loads(data) if isinstance(data, str) else data,
        "question": question,
    })



TOOLS = [query_database, generate_visualization, generate_insight]
llm_with_tools = llm.bind_tools(TOOLS)
tools_by_name = {t.name: t for t in TOOLS}


def run_agent(user_message: str, schema: str) -> dict:
    """
    Main agent loop. Handles tool calling manually to work around
    Gemini's MALFORMED_FUNCTION_CALL quirks.
    """
    system_prompt = build_system_prompt(schema)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]

    chart_spec = None
    max_iterations = 5  # prevent infinite loops

    for i in range(max_iterations):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        finish_reason = response.response_metadata.get("finish_reason", "")

        # Gemini returned a malformed call — ask it to try again
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
                tool_result = tools_by_name[tool_name].invoke(tool_args)

            # Capture chart spec if the visualization tool was called
            if tool_name == "generate_visualization":
                try:
                    chart_spec = json.loads(tool_result)
                except Exception:
                    pass

            # Add tool result back to the conversation
            from langchain_core.messages import ToolMessage
            messages.append(
                ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_call["id"],
                )
            )

    # Final text response from the agent
    final_text = ""
    if messages and hasattr(messages[-1], "content"):
        last = messages[-1]
        if hasattr(last, "tool_calls") and not last.tool_calls:
            final_text = last.content
        elif not hasattr(last, "tool_calls"):
            final_text = last.content

    return {
        "text": final_text,
        "chart": chart_spec,
    }