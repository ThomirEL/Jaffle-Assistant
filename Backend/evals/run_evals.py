import sys
import time
import mlflow
from pathlib import Path
from token_tracker import print_summary
from datetime import datetime

# Setup
BACKEND_DIR  = Path(__file__).parent.parent
MLFLOW_DIR   = BACKEND_DIR / "evals" / "eval_results" / "mlruns"
RESULTS_FILE = Path(__file__).parent / "eval_results" / "eval_results.json"
SUMMARY_FILE = Path(__file__).parent / "eval_results" / "eval_summary.txt"

sys.path.append(str(BACKEND_DIR))
mlflow.set_tracking_uri(f"file:///{MLFLOW_DIR}")

# Imports (after sys.path setup)
from database import get_schema
from agent import run_agent
from evals.multi_agent import run_multi_agent, run_reasoning_multi_agent
from evals.eval_configs.eval_questions import EVAL_QUESTIONS
from evals.judge import score_response
from evals.helpers.usage_tracker import UsageTracker
from evals.helpers.aggregation import aggregate
from evals.helpers.reporting import save_json_results, save_summary_report, print_metrics_summary
from evals.eval_configs.evals_variants import PROMPT_VARIANTS, AGENT_VARIANTS, UPDATED_BASELINE, SQL_UPDATED_BASELINE_PROMPT

TRACKER = UsageTracker()

# Constants
SQL_REPEATED_TIMES = 3
TYPE_OF_RUN = "sql_updated_baseline" # Change to agent, prompt, updated_baseline, sql_updated_baseline. Check readme for more details

def run_question(variant: dict, question_config: dict, schema: str, session_id: str) -> dict:
    start = time.time()
    try:
        if variant["agent_type"] == "multi":
            response = run_multi_agent(question_config["question"], schema)
        elif variant["agent_type"] == "reasoning_multi":
            response = run_reasoning_multi_agent(question_config["question"], schema)
        elif variant["agent_type"] == "single":
            prompt = variant["system_prompt"]
            if "{schema}" in prompt:
                prompt = prompt.format(schema=schema)
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
        response = {"text": "", "chart": None, "sql_queries": []}
        latency = time.time() - start
        error = str(e)
        print(f"  Error running question {question_config['id']}: {error}")

    sql_queries = response.get("sql_queries", [])

    scores = score_response(
        question_config["question"],
        response,
        question_config,
        session_id=session_id,
    )

    print(f"    → text: {response.get('text', 'EMPTY')[:80]}")
    print(f"    → chart: {'yes' if response.get('chart') else 'no'}")
    if sql_queries:
        for i, sql in enumerate(sql_queries):
            print(f"    → sql[{i}]: {sql[:120]}")

    return {
        "question_id":  question_config["id"],
        "question":     question_config["question"],
        "category":     question_config["category"],
        "latency":      round(latency, 2),
        "error":        error,
        "agent_text":   response.get("text", ""),
        "sql_queries":  sql_queries,      # ← saved to JSON
        **scores,
    }

def main():
    print("Loading schema...")
    schema = get_schema()

    mlflow.set_tracking_uri(f"file:///{MLFLOW_DIR}")
    print(f"MLflow logging to: {MLFLOW_DIR}")
    mlflow.set_experiment("jaffle-agent-evals-run-6-repeatability-with-sql-queries")

    
    if TYPE_OF_RUN == "agent":              # Test the 4 different agents variants (baseline, reasoning, multi agent, reasoning multi agent)
        variants_to_run = AGENT_VARIANTS
    elif TYPE_OF_RUN == "prompt":           # Test the 4 different "one shot" prompts (concise, analytical, baseline and )
        variants_to_run = PROMPT_VARIANTS   
    elif TYPE_OF_RUN == "updated_baseline":
        variants_to_run = UPDATED_BASELINE  # Test the new baseline prompt with improvements
    elif TYPE_OF_RUN == "sql_updated_baseline":
        variants_to_run = SQL_UPDATED_BASELINE_PROMPT * SQL_REPEATED_TIMES     # Test the updated baseline prompt. This is intendted to see if there is consistency between runs in sql queries. Change SQL_REPEATED_TIMES to have as many runs as you want. 
    

    for variant in variants_to_run:                              # Change this to AGENT_VARIANTS to run agent-based evals or PROMPT_VARIANTS to run prompt-based eval
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
                if TYPE_OF_RUN == "sql_updated_baseline" and ('q' not in q["id"]):
                    continue  # Only run SQL questions for the SQL-updated baseline variant

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