"""Aggregation utilities for evaluation results."""


def aggregate(results: list) -> dict:
    """
    Aggregate individual question results into overall metrics.
    
    Args:
        results: List of result dictionaries from run_question()
        
    Returns:
        Dictionary with aggregated metrics
    """
    standard = [r for r in results if not r["is_failure_case"]]
    failures = [r for r in results if r["is_failure_case"]]

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
