"""Deterministic offline retrieval benchmark utilities.

This module intentionally avoids external LLM providers, API keys, and
production retrieval behavior changes. It evaluates ranked memory IDs against
version-controlled synthetic expected mappings.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Callable


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MEMORIES_PATH = BASE_DIR / "data" / "synthetic_memories.json"
DEFAULT_QUERIES_PATH = BASE_DIR / "data" / "rag_eval_queries.json"


Retriever = Callable[[str, list[dict[str, Any]], int], list[str]]


def load_json(path: str | Path) -> Any:
    """Load JSON data from disk."""
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def _tokenize(text: str) -> set[str]:
    """Tokenize text deterministically for the local baseline retriever."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def deterministic_keyword_retriever(
    query: str,
    memories: list[dict[str, Any]],
    top_k: int,
) -> list[str]:
    """Return ranked memory IDs using deterministic lexical overlap.

    This is only a local baseline/demo retriever. The benchmark can also accept
    a project retriever adapter without changing production retrieval behavior.
    """
    query_tokens = _tokenize(query)
    scored: list[tuple[int, str]] = []

    for memory in memories:
        memory_id = memory["memory_id"]
        content = memory.get("content", "")
        metadata = memory.get("metadata", {})
        metadata_text = " ".join(
            str(value) if not isinstance(value, list) else " ".join(map(str, value))
            for value in metadata.values()
        )
        memory_tokens = _tokenize(f"{content} {metadata_text}")
        overlap = len(query_tokens & memory_tokens)
        scored.append((overlap, memory_id))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [memory_id for score, memory_id in scored[:top_k] if score > 0]


def recall_at_k(expected_ids: set[str], retrieved_ids: list[str], k: int) -> float:
    """Calculate Recall@K."""
    if not expected_ids:
        return 0.0

    top_k = set(retrieved_ids[:k])
    return len(expected_ids & top_k) / len(expected_ids)


def precision_at_k(expected_ids: set[str], retrieved_ids: list[str], k: int) -> float:
    """Calculate Precision@K."""
    if k <= 0:
        return 0.0

    top_k = retrieved_ids[:k]
    if not top_k:
        return 0.0

    return len(expected_ids & set(top_k)) / k


def reciprocal_rank(expected_ids: set[str], retrieved_ids: list[str]) -> float:
    """Calculate reciprocal rank for the first relevant retrieved result."""
    for rank, memory_id in enumerate(retrieved_ids, start=1):
        if memory_id in expected_ids:
            return 1.0 / rank

    return 0.0


def source_hit_at_k(expected_ids: set[str], retrieved_ids: list[str], k: int) -> int:
    """Return 1 if at least one expected source appears in top K."""
    return int(bool(expected_ids & set(retrieved_ids[:k])))


def evaluate_single_query(
    expected_ids: list[str],
    retrieved_ids: list[str],
    k_values: tuple[int, ...] = (1, 5),
) -> dict[str, float | int]:
    """Evaluate one query's ranked retrieval output."""
    expected_set = set(expected_ids)
    metrics: dict[str, float | int] = {
        "mrr": reciprocal_rank(expected_set, retrieved_ids),
    }

    for k in k_values:
        metrics[f"recall@{k}"] = recall_at_k(expected_set, retrieved_ids, k)
        metrics[f"precision@{k}"] = precision_at_k(expected_set, retrieved_ids, k)
        metrics[f"source_hit@{k}"] = source_hit_at_k(expected_set, retrieved_ids, k)

    return metrics


def evaluate_retriever(
    memories: list[dict[str, Any]],
    queries: list[dict[str, Any]],
    retriever: Retriever = deterministic_keyword_retriever,
    top_k: int = 5,
    k_values: tuple[int, ...] = (1, 5),
) -> dict[str, Any]:
    """Run retrieval evaluation over all benchmark queries."""
    per_query_results = []

    for query_item in queries:
        retrieved_ids = retriever(query_item["query"], memories, top_k)
        metrics = evaluate_single_query(
            expected_ids=query_item["expected_memory_ids"],
            retrieved_ids=retrieved_ids,
            k_values=k_values,
        )

        per_query_results.append(
            {
                "query_id": query_item["query_id"],
                "query": query_item["query"],
                "expected_memory_ids": query_item["expected_memory_ids"],
                "retrieved_memory_ids": retrieved_ids,
                "metrics": metrics,
            }
        )

    aggregate: dict[str, float] = {}
    if per_query_results:
        metric_names = per_query_results[0]["metrics"].keys()
        for metric_name in metric_names:
            aggregate[metric_name] = sum(
                float(item["metrics"][metric_name]) for item in per_query_results
            ) / len(per_query_results)

    return {
        "num_queries": len(queries),
        "top_k": top_k,
        "aggregate_metrics": aggregate,
        "per_query": per_query_results,
    }


def save_json_report(report: dict[str, Any], output_path: str | Path) -> None:
    """Save benchmark report as JSON."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)


def save_csv_report(report: dict[str, Any], output_path: str | Path) -> None:
    """Save per-query benchmark results as CSV."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    metric_names = sorted(report["aggregate_metrics"].keys())

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "query_id",
                "query",
                "expected_memory_ids",
                "retrieved_memory_ids",
                *metric_names,
            ],
        )
        writer.writeheader()

        for item in report["per_query"]:
            row = {
                "query_id": item["query_id"],
                "query": item["query"],
                "expected_memory_ids": ",".join(item["expected_memory_ids"]),
                "retrieved_memory_ids": ",".join(item["retrieved_memory_ids"]),
            }
            row.update(item["metrics"])
            writer.writerow(row)


def run_benchmark(
    memories_path: str | Path = DEFAULT_MEMORIES_PATH,
    queries_path: str | Path = DEFAULT_QUERIES_PATH,
    top_k: int = 5,
) -> dict[str, Any]:
    """Run the default deterministic benchmark."""
    memories = load_json(memories_path)
    queries = load_json(queries_path)
    return evaluate_retriever(memories=memories, queries=queries, top_k=top_k)


def main() -> None:
    """CLI entry point for the offline benchmark."""
    parser = argparse.ArgumentParser(
        description="Run deterministic offline retrieval evaluation benchmark."
    )
    parser.add_argument("--memories", default=str(DEFAULT_MEMORIES_PATH))
    parser.add_argument("--queries", default=str(DEFAULT_QUERIES_PATH))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json-output", default="")
    parser.add_argument("--csv-output", default="")

    args = parser.parse_args()

    report = run_benchmark(
        memories_path=args.memories,
        queries_path=args.queries,
        top_k=args.top_k,
    )

    print(json.dumps(report["aggregate_metrics"], indent=2))

    if args.json_output:
        save_json_report(report, args.json_output)

    if args.csv_output:
        save_csv_report(report, args.csv_output)


if __name__ == "__main__":
    main()
