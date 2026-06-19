from pathlib import Path

from app.evaluation.rag_benchmark import (
    deterministic_keyword_retriever,
    evaluate_retriever,
    evaluate_single_query,
    load_json,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
    save_csv_report,
    save_json_report,
    source_hit_at_k,
)


def test_recall_at_k():
    expected = {"mem_001", "mem_002"}
    retrieved = ["mem_003", "mem_001", "mem_004"]

    assert recall_at_k(expected, retrieved, 1) == 0.0
    assert recall_at_k(expected, retrieved, 2) == 0.5
    assert recall_at_k(expected, retrieved, 5) == 0.5


def test_precision_at_k():
    expected = {"mem_001"}
    retrieved = ["mem_003", "mem_001", "mem_004"]

    assert precision_at_k(expected, retrieved, 1) == 0.0
    assert precision_at_k(expected, retrieved, 2) == 0.5
    assert precision_at_k(expected, retrieved, 3) == 1 / 3


def test_reciprocal_rank():
    expected = {"mem_001"}
    retrieved = ["mem_003", "mem_001", "mem_004"]

    assert reciprocal_rank(expected, retrieved) == 0.5


def test_reciprocal_rank_returns_zero_when_no_relevant_result():
    expected = {"mem_999"}
    retrieved = ["mem_003", "mem_001", "mem_004"]

    assert reciprocal_rank(expected, retrieved) == 0.0


def test_source_hit_at_k():
    expected = {"mem_001"}
    retrieved = ["mem_003", "mem_001", "mem_004"]

    assert source_hit_at_k(expected, retrieved, 1) == 0
    assert source_hit_at_k(expected, retrieved, 2) == 1


def test_evaluate_single_query():
    result = evaluate_single_query(
        expected_ids=["mem_001"],
        retrieved_ids=["mem_003", "mem_001", "mem_004"],
        k_values=(1, 3),
    )

    assert result["recall@1"] == 0.0
    assert result["precision@1"] == 0.0
    assert result["source_hit@1"] == 0
    assert result["recall@3"] == 1.0
    assert result["precision@3"] == 1 / 3
    assert result["source_hit@3"] == 1
    assert result["mrr"] == 0.5


def test_evaluate_retriever_with_mocked_rankings():
    memories = [
        {"memory_id": "mem_001", "content": "alpha"},
        {"memory_id": "mem_002", "content": "beta"},
    ]
    queries = [
        {
            "query_id": "q_001",
            "query": "alpha question",
            "expected_memory_ids": ["mem_001"],
        }
    ]

    def fake_retriever(query, memories, top_k):
        return ["mem_002", "mem_001"]

    report = evaluate_retriever(
        memories=memories,
        queries=queries,
        retriever=fake_retriever,
        top_k=2,
        k_values=(1, 2),
    )

    assert report["num_queries"] == 1
    assert report["aggregate_metrics"]["recall@1"] == 0.0
    assert report["aggregate_metrics"]["recall@2"] == 1.0
    assert report["aggregate_metrics"]["precision@2"] == 0.5
    assert report["aggregate_metrics"]["mrr"] == 0.5


def test_deterministic_keyword_retriever_returns_stable_order():
    memories = [
        {
            "memory_id": "mem_b",
            "content": "User likes machine learning and IoT.",
            "metadata": {"entities": ["machine learning"]},
        },
        {
            "memory_id": "mem_a",
            "content": "User likes machine learning.",
            "metadata": {"entities": ["machine learning"]},
        },
    ]

    first_run = deterministic_keyword_retriever(
        "machine learning interest",
        memories,
        top_k=2,
    )
    second_run = deterministic_keyword_retriever(
        "machine learning interest",
        memories,
        top_k=2,
    )

    assert first_run == second_run


def test_version_controlled_dataset_files_load():
    base_path = Path(__file__).resolve().parents[1] / "app" / "evaluation" / "data"

    memories = load_json(base_path / "synthetic_memories.json")
    queries = load_json(base_path / "rag_eval_queries.json")

    assert memories
    assert queries
    assert all("memory_id" in memory for memory in memories)
    assert all("expected_memory_ids" in query for query in queries)


def test_report_writers_create_json_and_csv(tmp_path):
    report = {
        "num_queries": 1,
        "top_k": 2,
        "aggregate_metrics": {
            "recall@2": 1.0,
            "precision@2": 0.5,
            "mrr": 0.5,
            "source_hit@2": 1.0,
        },
        "per_query": [
            {
                "query_id": "q_001",
                "query": "sample query",
                "expected_memory_ids": ["mem_001"],
                "retrieved_memory_ids": ["mem_002", "mem_001"],
                "metrics": {
                    "recall@2": 1.0,
                    "precision@2": 0.5,
                    "mrr": 0.5,
                    "source_hit@2": 1,
                },
            }
        ],
    }

    json_path = tmp_path / "reports" / "benchmark.json"
    csv_path = tmp_path / "reports" / "benchmark.csv"

    save_json_report(report, json_path)
    save_csv_report(report, csv_path)

    assert json_path.exists()
    assert csv_path.exists()
    assert "sample query" in csv_path.read_text(encoding="utf-8")
