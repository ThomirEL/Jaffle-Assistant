import duckdb

DB_PATH = "jaffle_shop.duckdb"


def get_connection():
    return duckdb.connect(DB_PATH)


def get_schema() -> str:
    """
    Introspects the database and returns a human + LLM readable schema string.
    This gets injected into the system prompt at startup.
    """
    con = get_connection()
    tables = con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
    ).fetchall()

    schema_parts = []

    for (table_name,) in tables:
        columns = con.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        # PRAGMA returns: cid, name, type, notnull, dflt_value, pk
        col_descriptions = [f"  - {col[1]} ({col[2]})" for col in columns]

        # Grab a sample row so the LLM understands the data shape
        sample = con.execute(f"SELECT * FROM {table_name} LIMIT 1").fetchdf()
        sample_str = sample.to_string(index=False)

        schema_parts.append(
            f"Table: {table_name}\n"
            f"Columns:\n" + "\n".join(col_descriptions) + "\n"
            f"Sample row:\n{sample_str}"
        )

    con.close()
    return "\n\n".join(schema_parts)


def run_query(sql: str) -> dict:
    """
    Executes a SQL query and returns results as a dict the agent can work with.
    """
    try:
        con = get_connection()
        df = con.execute(sql).fetchdf()
        con.close()
        return {
            "success": True,
            "columns": list(df.columns),
            "rows": df.to_dict(orient="records"),
            "row_count": len(df),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }