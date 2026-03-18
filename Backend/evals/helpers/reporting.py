"""Reporting utilities for writing evaluation results to files."""

import json


def save_json_results(results: list, filepath) -> None:
    """
    Save detailed results to a JSON file.
    
    Args:
        results: List of result dictionaries
        filepath: Path to write JSON file to
    """
    with open(filepath, "w") as f:
        json.dump(results, f, indent=2, default=str)


def save_summary_report(results: list, variant_name: str, session_id: str, filepath) -> None:
    """
    Save a human-readable summary report of evaluation results.
    
    Args:
        results: List of result dictionaries
        variant_name: Name of the variant being evaluated
        session_id: Session identifier
        filepath: Path to write summary file to
    """
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"Variant: {variant_name}\n")
        f.write(f"Session: {session_id}\n\n")
        for r in results:
            f.write(f"{'='*60}\n")
            f.write(f"[{r['question_id']}] {r['question']}\n")
            f.write(f"Latency: {r['latency']}s\n")
            f.write(f"Relevance: {r.get('relevance_score')}\n")
            f.write(f"Graceful: {r.get('graceful_failure_score')}\n")
            f.write(f"\nAgent response:\n{r.get('agent_text', 'EMPTY')}\n\n")


def print_metrics_summary(metrics: dict) -> None:
    """
    Print a formatted summary of aggregated metrics.
    
    Args:
        metrics: Dictionary of metrics from aggregate()
    """
    print(f"\n  avg_relevance:        {metrics['avg_relevance']}")
    print(f"  sql_success_rate:     {metrics['sql_success_rate']:.0%}")
    print(f"  avg_graceful_failure: {metrics['avg_graceful_failure_score']}")
    print(f"  avg_latency:          {metrics['avg_latency_standard']}s")
    print(f"  error_rate:           {metrics['error_rate']:.0%}")
