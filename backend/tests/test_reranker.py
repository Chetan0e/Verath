import asyncio
import threading
import time
import pytest
from unittest.mock import MagicMock


def _make_candidates(n: int):
    return [{"text": f"memory text {i}", "id": f"mem_{i}", "metadata": {}} for i in range(n)]


class TestAsyncRerank:
    """Unit tests for async_rerank() covering correctness and non-blocking behaviour."""

    async def test_async_rerank_returns_sorted_results(self, monkeypatch):
        """async_rerank returns top_k candidates sorted by rerank_score descending."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.1, 0.9, 0.5]
        monkeypatch.setattr("app.services.reranker._get_cross_encoder", lambda: mock_model)

        from app.services.reranker import async_rerank

        result = await async_rerank(
            query="test query",
            candidates=_make_candidates(3),
            top_k=2,
        )

        assert len(result) == 2
        assert result[0]["rerank_score"] > result[1]["rerank_score"]
        assert result[0]["text"] == "memory text 1"  # highest mock score (0.9)

    async def test_async_rerank_adds_confidence_field_in_range(self, monkeypatch):
        """Each returned item has a 'confidence' in [0, 1] derived via sigmoid."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.0]  # sigmoid(0) == 0.5 exactly
        monkeypatch.setattr("app.services.reranker._get_cross_encoder", lambda: mock_model)

        from app.services.reranker import async_rerank

        result = await async_rerank(query="test", candidates=_make_candidates(1), top_k=1)

        assert "confidence" in result[0]
        assert 0.0 <= result[0]["confidence"] <= 1.0
        assert result[0]["confidence"] == 0.5

    async def test_async_rerank_empty_candidates_returns_empty_list(self):
        """async_rerank short-circuits to [] with no candidates (no model load)."""
        from app.services.reranker import async_rerank

        result = await async_rerank(query="test", candidates=[], top_k=5)

        assert result == []

    async def test_async_rerank_respects_top_k_limit(self, monkeypatch):
        """async_rerank trims output to at most top_k items."""
        mock_model = MagicMock()
        mock_model.predict.return_value = list(range(10))
        monkeypatch.setattr("app.services.reranker._get_cross_encoder", lambda: mock_model)

        from app.services.reranker import async_rerank

        result = await async_rerank(query="test", candidates=_make_candidates(10), top_k=3)

        assert len(result) == 3

    async def test_async_rerank_attaches_rerank_score_to_each_item(self, monkeypatch):
        """Every returned item exposes the raw rerank_score float."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [1.5, 0.3]
        monkeypatch.setattr("app.services.reranker._get_cross_encoder", lambda: mock_model)

        from app.services.reranker import async_rerank

        result = await async_rerank(query="test", candidates=_make_candidates(2), top_k=2)

        for item in result:
            assert "rerank_score" in item
            assert isinstance(item["rerank_score"], float)

    async def test_async_rerank_runs_predict_in_worker_thread(self, monkeypatch):
        """predict() must execute in a ThreadPoolExecutor thread, not the event-loop thread.

        If rerank() were called without asyncio.to_thread the thread id captured
        inside predict() would match the event-loop thread — this test catches that.
        """
        event_loop_thread_id = threading.current_thread().ident
        predict_thread_ids: list[int] = []

        def capturing_predict(pairs):
            predict_thread_ids.append(threading.current_thread().ident)
            return [0.5] * len(pairs)

        mock_model = MagicMock()
        mock_model.predict.side_effect = capturing_predict
        monkeypatch.setattr("app.services.reranker._get_cross_encoder", lambda: mock_model)

        from app.services.reranker import async_rerank

        await async_rerank(query="blocking test", candidates=_make_candidates(2), top_k=2)

        assert predict_thread_ids, "predict() was never called"
        for tid in predict_thread_ids:
            assert tid != event_loop_thread_id, (
                "rerank() ran on the event-loop thread — asyncio.to_thread offloading is broken"
            )

    async def test_async_rerank_event_loop_remains_free_during_inference(self, monkeypatch):
        """Concurrent coroutines can tick while async_rerank is in the executor.

        Simulates a 50ms inference delay; a counter coroutine must reach 10
        ticks during that window, proving the loop was never frozen.
        """
        def slow_predict(pairs):
            time.sleep(0.05)  # simulate 50 ms PyTorch forward pass
            return [0.5] * len(pairs)

        mock_model = MagicMock()
        mock_model.predict.side_effect = slow_predict
        monkeypatch.setattr("app.services.reranker._get_cross_encoder", lambda: mock_model)

        tick_count = {"value": 0}

        async def tick_counter():
            for _ in range(10):
                tick_count["value"] += 1
                await asyncio.sleep(0)

        from app.services.reranker import async_rerank

        await asyncio.gather(
            async_rerank(query="concurrent test", candidates=_make_candidates(2), top_k=2),
            tick_counter(),
        )

        assert tick_count["value"] == 10, (
            f"Event loop was blocked: only {tick_count['value']}/10 ticks completed "
            "during async_rerank — thread offloading is not working"
        )


class TestRunQueryUsesAsyncRerank:
    """Integration tests verifying run_query() delegates to async_rerank()."""

    async def test_run_query_calls_async_rerank_not_sync_rerank(self, monkeypatch):
        """run_query() must await async_rerank, not call the blocking rerank() directly."""
        async_rerank_called = {"value": False}

        async def mock_async_rerank(query, candidates, top_k):
            async_rerank_called["value"] = True
            return [{
                "text": "mock memory",
                "metadata": {},
                "rerank_score": 0.9,
                "confidence": 0.71,
            }]

        async def mock_search_memories(user_id, query, limit, intent_filter, min_importance):
            return [{"text": "test memory", "metadata": {}}]

        async def mock_generate_response(prompt):
            return "mocked answer"

        monkeypatch.setattr("app.services.query_engine.async_rerank", mock_async_rerank)
        monkeypatch.setattr("app.services.query_engine.search_memories", mock_search_memories)
        monkeypatch.setattr("app.services.query_engine.generate_response", mock_generate_response)

        from app.services.query_engine import run_query

        result = await run_query(user_id="user1", query="test query")

        assert async_rerank_called["value"] is True
        assert result["answer"] == "mocked answer"

    async def test_run_query_output_shape_unchanged_after_executor_change(self, monkeypatch):
        """run_query() still returns answer, context, sources, confidence_score."""
        async def mock_async_rerank(query, candidates, top_k):
            return [{
                "text": "test text",
                "metadata": {
                    "speaker": "alice",
                    "intent": "meeting",
                    "timestamp": "2024-01-01",
                    "importance": 0.8,
                },
                "rerank_score": 1.2,
                "confidence": 0.77,
            }]

        async def mock_search_memories(user_id, query, limit, intent_filter, min_importance):
            return [{"text": "test text", "metadata": {}}]

        async def mock_generate_response(prompt):
            return "Here is the answer"

        monkeypatch.setattr("app.services.query_engine.async_rerank", mock_async_rerank)
        monkeypatch.setattr("app.services.query_engine.search_memories", mock_search_memories)
        monkeypatch.setattr("app.services.query_engine.generate_response", mock_generate_response)

        from app.services.query_engine import run_query

        result = await run_query(user_id="user1", query="test query")

        assert "answer" in result
        assert "context" in result
        assert "sources" in result
        assert "confidence_score" in result
        assert result["confidence_score"] == 0.77
        assert result["context"] == ["test text"]