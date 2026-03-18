import json
import os
from datetime import datetime
from pathlib import Path
from threading import Lock

TRACKER_FILE = Path(__file__).parent / "token_usage.json"
_lock = Lock()


def _load() -> dict:
    if TRACKER_FILE.exists():
        try:
            with open(TRACKER_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"daily": {}, "sessions": []}


def _save(data: dict):
    with open(TRACKER_FILE, "w") as f:
        json.dump(data, f, indent=2)


def log_call(
    caller: str,        # e.g. "agent", "judge", "sql_sub_agent", "chart_sub_agent"
    model: str,
    input_tokens: int,
    output_tokens: int,
    session_id: str = None,
):
    """
    Log a single LLM call. Thread-safe.
    caller:       which part of the code made the call
    model:        model name string
    input_tokens: prompt token count
    output_tokens: completion token count
    session_id:   optional tag to group calls (e.g. eval run name)
    """
    today = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().isoformat()
    total = input_tokens + output_tokens

    with _lock:
        data = _load()

        # ── Daily aggregates ───────────────────────────────────────────────────
        if today not in data["daily"]:
            data["daily"][today] = {
                "total_requests": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "by_caller": {},
                "by_model": {},
            }

        day = data["daily"][today]
        day["total_requests"] += 1
        day["total_input_tokens"] += input_tokens
        day["total_output_tokens"] += output_tokens
        day["total_tokens"] += total

        # Per caller breakdown
        if caller not in day["by_caller"]:
            day["by_caller"][caller] = {"requests": 0, "tokens": 0}
        day["by_caller"][caller]["requests"] += 1
        day["by_caller"][caller]["tokens"] += total

        # Per model breakdown
        if model not in day["by_model"]:
            day["by_model"][model] = {"requests": 0, "tokens": 0}
        day["by_model"][model]["requests"] += 1
        day["by_model"][model]["tokens"] += total

        # ── Session log (every individual call) ───────────────────────────────
        data["sessions"].append({
            "timestamp": timestamp,
            "session_id": session_id or "unknown",
            "caller": caller,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total,
        })

        # Keep sessions log from growing forever — keep last 2000 entries
        if len(data["sessions"]) > 2000:
            data["sessions"] = data["sessions"][-2000:]

        _save(data)


def extract_usage(response) -> tuple[int, int]:
    """
    Extract input/output token counts from a LangChain response object.
    Works for both Groq and Google responses.
    """
    input_tokens = 0
    output_tokens = 0

    try:
        usage = None

        # Groq and OpenAI style
        if hasattr(response, "response_metadata"):
            meta = response.response_metadata
            usage = meta.get("token_usage") or meta.get("usage")

        # LangChain usage_metadata field (newer versions)
        if not usage and hasattr(response, "usage_metadata"):
            usage = response.usage_metadata

        if usage:
            if isinstance(usage, dict):
                input_tokens = (
                    usage.get("prompt_tokens") or
                    usage.get("input_tokens") or
                    usage.get("prompt_token_count") or 0
                )
                output_tokens = (
                    usage.get("completion_tokens") or
                    usage.get("output_tokens") or
                    usage.get("candidates_token_count") or 0
                )
            else:
                # Object with attributes
                input_tokens  = getattr(usage, "prompt_tokens", 0) or getattr(usage, "input_tokens", 0)
                output_tokens = getattr(usage, "completion_tokens", 0) or getattr(usage, "output_tokens", 0)

    except Exception:
        pass

    return input_tokens, output_tokens


def print_summary(session_id: str = None):
    """Print a summary of today's usage to the console."""
    data = _load()
    today = datetime.now().strftime("%Y-%m-%d")
    day = data["daily"].get(today, {})

    print(f"\n{'='*55}")
    print(f"TOKEN USAGE SUMMARY — {today}")
    print(f"{'='*55}")

    if not day:
        print("  No usage recorded today.")
        return

    print(f"  Total requests : {day['total_requests']}")
    print(f"  Input tokens   : {day['total_input_tokens']:,}")
    print(f"  Output tokens  : {day['total_output_tokens']:,}")
    print(f"  Total tokens   : {day['total_tokens']:,}")

    print(f"\n  By caller:")
    for caller, stats in sorted(day["by_caller"].items()):
        print(f"    {caller:<25} {stats['requests']:>4} req   {stats['tokens']:>8,} tokens")

    print(f"\n  By model:")
    for model, stats in sorted(day["by_model"].items()):
        print(f"    {model:<35} {stats['requests']:>4} req   {stats['tokens']:>8,} tokens")

    if session_id:
        session_calls = [s for s in data["sessions"] if s["session_id"] == session_id]
        session_tokens = sum(s["total_tokens"] for s in session_calls)
        print(f"\n  This eval run ({session_id}):")
        print(f"    Requests : {len(session_calls)}")
        print(f"    Tokens   : {session_tokens:,}")

    print(f"{'='*55}")
    print(f"  Full log: {TRACKER_FILE}\n")