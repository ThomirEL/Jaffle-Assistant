import sys
import time
import mlflow
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
BACKEND_DIR  = Path(__file__).parent.parent
MLFLOW_DIR   = BACKEND_DIR / "mlruns"
RESULTS_FILE = Path(__file__).parent / "eval_results.json"
SUMMARY_FILE = Path(__file__).parent / "eval_summary.txt"

sys.path.append(str(BACKEND_DIR))
mlflow.set_tracking_uri(f"file:///{MLFLOW_DIR}")

# ── Imports ───────────────────────────────────────────────────────────────────
from database import get_schema
from agent import run_agent
from prompts import BASELINE_PROMPT, REASONING_PROMPT
from evals.multi_agent import run_multi_agent, run_reasoning_multi_agent
from evals.eval_questions import EVAL_QUESTIONS
from evals.judge import score_response
from config import agent_llm, judge_llm
from evals.helpers.usage_tracker import UsageTracker
from evals.helpers.aggregation import aggregate
from evals.helpers.reporting import save_json_results, save_summary_report, print_metrics_summary

TRACKER = UsageTracker()


PROMPT_VARIANTS = [
    {
        "name": "baseline",
        "agent_type": "single",
        "description": "Single agent with standard business-assistant prompt",
        "system_prompt": BASELINE_PROMPT,
    },
    {
        "name": "reasoning",
        "agent_type": "single",
        "description": "Single agent with structured <thinking> reasoning protocol",
        "system_prompt": REASONING_PROMPT,
    },
    {
        "name": "multi_agent",
        "agent_type": "multi",
        "description": "Three sub-agents: SQL specialist, chart specialist, insight specialist",
        "system_prompt": None,
    },
    {
        "name": "reasoning_multi_agent",
        "agent_type": "reasoning_multi",
        "description": "Three sub-agents, each with <thinking> reasoning before acting",
        "system_prompt": None,
    },
]


# ── Runner ────────────────────────────────────────────────────────────────────

def run_question(variant: dict, question_config: dict, schema: str, session_id: str) -> dict:
    """
    Execute a single evaluation question against a variant.
    
    Args:
        variant: Variant configuration dictionary
        question_config: Question configuration from EVAL_QUESTIONS
        schema: Database schema information
        session_id: Session identifier for tracking
        
    Returns:
        Dictionary with question result and scores
    """
    start = time.time()
    try:
        if variant["agent_type"] == "multi":
            response = run_multi_agent(question_config["question"], schema)
        elif variant["agent_type"] == "reasoning_multi":
            response = run_reasoning_multi_agent(question_config["question"], schema)
        elif variant["agent_type"] == "single":
            response = run_agent(
                question_config["question"],
                schema,
                base_prompt=variant["system_prompt"],
                session_id=session_id,
            )
        else:
            raise ValueError(f"Unknown agent_type: {variant['agent_type']}")

        latency = time.time() - start
        error = None
    except Exception as e:
        response = {"text": "", "chart": None}
        latency = time.time() - start
        error = str(e)
        print(f"  Error running question {question_config['id']}: {error}")

    scores = score_response(
        question_config["question"],
        response,
        question_config,
        session_id=session_id,
    )

    print(f"    → text: {response.get('text', 'EMPTY')}")
    print(f"    → chart: {'yes' if response.get('chart') else 'no'}")

    return {
        "question_id": question_config["id"],
        "question":    question_config["question"],
        "category":    question_config["category"],
        "latency":     round(latency, 2),
        "error":       error,
        "agent_text":  response.get("text", ""),
        **scores,
    }




# In main — generate session_id and print summary at the end
def main():
    from token_tracker import print_summary
    from datetime import datetime

    print("Loading schema...")
    schema = get_schema()

    mlflow.set_tracking_uri(f"file:///{MLFLOW_DIR}")
    print(f"MLflow logging to: {MLFLOW_DIR}")
    mlflow.set_experiment("jaffle-agent-evals-run-2")

    for variant in PROMPT_VARIANTS:
        # Use variant name + timestamp as session ID
        session_id = f"{variant['name']}_{datetime.now().strftime('%H%M%S')}"

        print(f"\n{'='*60}")
        print(f"Variant  : {variant['name']}")
        print(f"Type     : {variant['agent_type']}")
        print(f"Desc     : {variant['description']}")
        print(f"Session  : {session_id}")
        print(f"{'='*60}")

        with mlflow.start_run(run_name=variant["name"]) as run:
            print(f"  MLflow run ID: {run.info.run_id}")

            mlflow.log_params({
                "variant_name":  variant["name"],
                "agent_type":    variant["agent_type"],
                "description":   variant["description"],
                "num_questions": len(EVAL_QUESTIONS),
                "session_id":    session_id,
            })

            results = []
            for q in EVAL_QUESTIONS:
                print(f"  {q['id']} [{q['category']}]: {q['question'][:55]}...")
                result = run_question(variant, q, schema, session_id=session_id)
                results.append(result)

                step = int(q["id"][1:])
                if result["relevance_score"] is not None:
                    mlflow.log_metric("question_relevance", result["relevance_score"], step=step)
                if result["graceful_failure_score"] is not None:
                    mlflow.log_metric("question_graceful", result["graceful_failure_score"], step=step)

                time.sleep(4)

            metrics = aggregate(results)
            mlflow.log_metrics(metrics)

            # Save results and summary reports
            save_json_results(results, RESULTS_FILE)
            mlflow.log_artifact(str(RESULTS_FILE))

            save_summary_report(results, variant["name"], session_id, SUMMARY_FILE)
            mlflow.log_artifact(str(SUMMARY_FILE))

            # Print metrics summary
            print_metrics_summary(metrics)

        # Print token summary after each variant
        print_summary(session_id=session_id)

    # Final summary across entire run
    print("\n\nAll variants done.")
    print_summary()
    print("Run `mlflow ui --backend-store-uri ./mlruns` to compare.")


if __name__ == "__main__":
    main()