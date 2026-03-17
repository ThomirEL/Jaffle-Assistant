import sys
import os
import time
import json
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


# ── Prompt variants ───────────────────────────────────────────────────────────

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
        "description": "Three sub-agents each with <thinking> reasoning before acting",
        "system_prompt": None,
    },
]


# ── Runner ────────────────────────────────────────────────────────────────────

def run_question(variant: dict, question_config: dict, schema: str) -> dict:
    print(f"    Running question {question_config['id']} with variant {variant['name']}...")
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
            )

        else:
            raise ValueError(f"Unknown agent_type: {variant['agent_type']}")

        latency = time.time() - start
        error = None

    except Exception as e:
        response = {"text": "", "chart": None}
        latency = time.time() - start
        error = str(e)
        print(f"    Error running question {question_config['id']}: {error}")

    print(f"    → text: {response.get('text', 'EMPTY')}")
    print(f"    → chart: {'yes' if response.get('chart') else 'no'}")

    scores = score_response(question_config["question"], response, question_config)

    return {
        "question_id":  question_config["id"],
        "question":     question_config["question"],
        "category":     question_config["category"],
        "latency":      round(latency, 2),
        "error":        error,
        "agent_text":   response.get("text", ""),
        **scores,
    }


def aggregate(results: list) -> dict:
    standard = [r for r in results if not r["is_failure_case"]]
    failures  = [r for r in results if r["is_failure_case"]]

    def safe_avg(values):
        vals = [v for v in values if v is not None]
        return round(sum(vals) / len(vals), 2) if vals else 0.0

    return {
        "avg_relevance":              safe_avg([r["relevance_score"] for r in standard]),
        "sql_success_rate":           round(sum(1 for r in standard if r["sql_success"]) / max(len(standard), 1), 2),
        "chart_accuracy":             safe_avg([r["chart_score"] for r in standard if r["chart_score"] is not None]),
        "avg_latency_standard":       safe_avg([r["latency"] for r in standard]),
        "avg_graceful_failure_score": safe_avg([r["graceful_failure_score"] for r in failures]),
        "avg_latency_failure":        safe_avg([r["latency"] for r in failures]),
        "graceful_ambiguous":         safe_avg([r["graceful_failure_score"] for r in failures if r["failure_type"] == "ambiguous"]),
        "graceful_out_of_scope":      safe_avg([r["graceful_failure_score"] for r in failures if r["failure_type"] == "out_of_scope"]),
        "graceful_bad_sql":           safe_avg([r["graceful_failure_score"] for r in failures if r["failure_type"] in ("nonexistent_table", "missing_data")]),
        "graceful_adversarial":       safe_avg([r["graceful_failure_score"] for r in failures if r["failure_type"] in ("prompt_injection", "sql_injection")]),
        "error_rate":                 round(sum(1 for r in results if r["error"]) / max(len(results), 1), 2),
    }


def main():
    print("Loading schema...")
    schema = get_schema()

    if not schema:
        print("ERROR: Schema is empty. Check your database path in database.py")
        return

    print(f"MLflow logging to: {MLFLOW_DIR}")
    mlflow.set_experiment("jaffle-agent-evals")

    for variant in PROMPT_VARIANTS:
        print(f"\n{'='*60}")
        print(f"Variant : {variant['name']}")
        print(f"Type    : {variant['agent_type']}")
        print(f"Desc    : {variant['description']}")
        print(f"{'='*60}")

        with mlflow.start_run(run_name=variant["name"]) as run:
            print(f"  MLflow run ID: {run.info.run_id}")

            mlflow.log_params({
                "variant_name":  variant["name"],
                "agent_type":    variant["agent_type"],
                "description":   variant["description"],
                "num_questions": len(EVAL_QUESTIONS),
                "judge_model":   "groq/llama-3.3-70b-versatile",
            })

            results = []
            for q in EVAL_QUESTIONS:
                print(f"  {q['id']} [{q['category']}]: {q['question'][:55]}...")
                result = run_question(variant, q, schema)
                results.append(result)

                step = int(q["id"][1:])
                if result["relevance_score"] is not None:
                    mlflow.log_metric("question_relevance", result["relevance_score"], step=step)
                if result["graceful_failure_score"] is not None:
                    mlflow.log_metric("question_graceful", result["graceful_failure_score"], step=step)
                print(f"Sleeping for 15s to avoid rate limits...")
                time.sleep(15)  # avoid rate limits

            metrics = aggregate(results)
            mlflow.log_metrics(metrics)

            # Save JSON artifact
            with open(RESULTS_FILE, "w") as f:
                json.dump(results, f, indent=2, default=str)
            mlflow.log_artifact(str(RESULTS_FILE))

            # Save readable summary artifact
            with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
                f.write(f"Variant: {variant['name']}\n")
                f.write(f"Description: {variant['description']}\n\n")
                for r in results:
                    f.write(f"{'='*60}\n")
                    f.write(f"[{r['question_id']}] {r['question']}\n")
                    f.write(f"Category : {r['category']}\n")
                    f.write(f"Latency  : {r['latency']}s\n")
                    f.write(f"Relevance: {r.get('relevance_score')}\n")
                    f.write(f"Graceful : {r.get('graceful_failure_score')}\n")
                    f.write(f"\nAgent response:\n{r.get('agent_text', 'EMPTY')}\n")
                    if r.get("error"):
                        f.write(f"\nERROR: {r['error']}\n")
                    f.write("\n")
            mlflow.log_artifact(str(SUMMARY_FILE))

            print(f"\n  avg_relevance:          {metrics['avg_relevance']}")
            print(f"  sql_success_rate:       {metrics['sql_success_rate']:.0%}")
            print(f"  avg_graceful_failure:   {metrics['avg_graceful_failure_score']}")
            print(f"    ambiguous:            {metrics['graceful_ambiguous']}")
            print(f"    out_of_scope:         {metrics['graceful_out_of_scope']}")
            print(f"    bad_sql:              {metrics['graceful_bad_sql']}")
            print(f"    adversarial:          {metrics['graceful_adversarial']}")
            print(f"  avg_latency:            {metrics['avg_latency_standard']}s")
            print(f"  error_rate:             {metrics['error_rate']:.0%}")

    print("\n\nAll variants done.")
    print(f"Run: mlflow ui --backend-store-uri {MLFLOW_DIR}")


if __name__ == "__main__":
    main()