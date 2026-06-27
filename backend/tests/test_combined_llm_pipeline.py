import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.memory_extractor import MemoryExtractor


class TestCombinedLLMPipeline:
    """Regression tests for the combined LLM call optimization (issue #121)."""


    @pytest.mark.asyncio
    async def test_combined_llm_call_returns_both_fields(self):
        """Happy path: valid JSON from LLM yields summary and importance."""
        extractor = MemoryExtractor()
        mock_response = json.dumps({
            "summary": "Meeting scheduled with team tomorrow.",
            "importance": 0.75
        })

        with patch(
            "app.services.memory_extractor.generate_response",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await extractor._combined_llm_call(
                "Let's meet with the team tomorrow to discuss the project."
            )

        assert result["summary"] == "Meeting scheduled with team tomorrow."
        assert result["importance"] == 0.75

    @pytest.mark.asyncio
    async def test_combined_llm_call_clamps_importance_to_bounds(self):
        """Importance values outside [0, 1] must be clamped."""
        extractor = MemoryExtractor()

        for out_of_range in [-0.5, 1.8, 99]:
            mock_response = json.dumps({"summary": "Some summary.", "importance": out_of_range})
            with patch(
                "app.services.memory_extractor.generate_response",
                new_callable=AsyncMock,
                return_value=mock_response,
            ):
                result = await extractor._combined_llm_call("Some text.")

            assert 0.0 <= result["importance"] <= 1.0, (
                f"importance {result['importance']} not clamped for input {out_of_range}"
            )

    @pytest.mark.asyncio
    async def test_combined_llm_call_falls_back_on_invalid_json(self):
        """Malformed JSON response must fall back to first-sentence + 0.5."""
        extractor = MemoryExtractor()

        with patch(
            "app.services.memory_extractor.generate_response",
            new_callable=AsyncMock,
            return_value="This is not JSON at all.",
        ):
            result = await extractor._combined_llm_call(
                "Remember to call John about the project deadline."
            )

        assert isinstance(result["summary"], str) and len(result["summary"]) > 0
        assert result["importance"] == 0.5

    @pytest.mark.asyncio
    async def test_combined_llm_call_falls_back_on_empty_summary(self):
        """Empty summary in valid JSON must trigger the fallback path."""
        extractor = MemoryExtractor()
        mock_response = json.dumps({"summary": "", "importance": 0.6})

        with patch(
            "app.services.memory_extractor.generate_response",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await extractor._combined_llm_call("Call John tomorrow.")

        assert result["summary"] != ""   # fallback kicks in
        assert result["importance"] == 0.5

    @pytest.mark.asyncio
    async def test_combined_llm_call_strips_markdown_fences(self):
        """Model sometimes wraps JSON in ```json ... ``` — must be stripped."""
        extractor = MemoryExtractor()
        payload = {"summary": "Deadline is Friday.", "importance": 0.9}
        fenced = f"```json\n{json.dumps(payload)}\n```"

        with patch(
            "app.services.memory_extractor.generate_response",
            new_callable=AsyncMock,
            return_value=fenced,
        ):
            result = await extractor._combined_llm_call("The deadline is this Friday.")

        assert result["summary"] == "Deadline is Friday."
        assert result["importance"] == 0.9


    @pytest.mark.asyncio
    async def test_extract_memory_includes_importance_field(self):
        """extract_memory() must now return an 'importance' key."""
        extractor = MemoryExtractor()
        combined_response = json.dumps({
            "summary": "Task assigned to finish report by Friday.",
            "importance": 0.8
        })

        with patch(
            "app.services.memory_extractor.generate_response",
            new_callable=AsyncMock,
            return_value=combined_response,
        ):
            result = await extractor.extract_memory(
                "I need to finish the report by Friday."
            )

        assert "importance" in result, "extract_memory must return 'importance'"
        assert result["importance"] == 0.8
        assert result["summary"] == "Task assigned to finish report by Friday."

    @pytest.mark.asyncio
    async def test_extract_memory_backward_compatible_fields(self):
        """All pre-existing fields must still be present after the refactor."""
        extractor = MemoryExtractor()
        combined_response = json.dumps({
            "summary": "Call John tomorrow morning.",
            "importance": 0.65
        })

        with patch(
            "app.services.memory_extractor.generate_response",
            new_callable=AsyncMock,
            return_value=combined_response,
        ):
            result = await extractor.extract_memory("Call John tomorrow morning.")

        required_fields = {
            "cleaned_text", "intent", "entities",
            "summary", "importance", "has_correction", "importance_boost"
        }
        assert required_fields.issubset(result.keys()), (
            f"Missing fields: {required_fields - result.keys()}"
        )


    @pytest.mark.asyncio
    async def test_pipeline_makes_exactly_one_groq_call_per_recording(self):
        """
        Core regression: process_audio must trigger only ONE generate_response
        call (the combined one), not two.
        """
        combined_response = json.dumps({
            "summary": "Meeting with team about project deadline.",
            "importance": 0.7
        })

        with patch(
            "app.pipeline.extraction_pipeline.generate_response",
            new_callable=AsyncMock,
            return_value=combined_response,
        ) as mock_llm, \
        patch("app.services.pipeline.transcribe", return_value="Meeting with team about project deadline."), \
        patch("app.services.pipeline.get_embedding", return_value=[0.1] * 384), \
        patch("app.services.pipeline.identify_speakers", return_value={}), \
        patch("app.services.pipeline.get_primary_speaker", return_value="user"), \
        patch("app.services.speaker_training.identify_voice", return_value="unknown"), \
        patch("app.services.pipeline.is_private", new_callable=AsyncMock, return_value=False), \
        patch("app.services.pipeline.store_memory", new_callable=AsyncMock, return_value="mem_123"):

            from app.services.pipeline import process_audio
            await process_audio("fake_audio.wav", "user_abc")

        # Exactly one LLM call — not two
        assert mock_llm.call_count == 1, (
            f"Expected 1 Groq API call, got {mock_llm.call_count}. "
            "The pipeline may still be calling score_importance() separately."
        )

    @pytest.mark.asyncio
    async def test_pipeline_importance_is_not_imported_from_score_importance(self):
        """
        score_importance() must NOT be called from the pipeline.
        importance comes from extraction_result['importance'].
        """
        with patch("app.services.importance.score_importance", new_callable=AsyncMock) as mock_score:
            combined_response = json.dumps({"summary": "Test summary.", "importance": 0.6})

            with patch(
                "app.pipeline.extraction_pipeline.generate_response",
                new_callable=AsyncMock,
                return_value=combined_response,
            ), \
            patch("app.services.pipeline.transcribe", return_value="Test audio content here."), \
            patch("app.services.pipeline.get_embedding", return_value=[0.1] * 384), \
            patch("app.services.pipeline.identify_speakers", return_value={}), \
            patch("app.services.pipeline.get_primary_speaker", return_value="user"), \
            patch("app.services.speaker_training.identify_voice", return_value="unknown"), \
            patch("app.services.pipeline.is_private", new_callable=AsyncMock, return_value=False), \
            patch("app.services.pipeline.store_memory", new_callable=AsyncMock, return_value="mem_456"):

                from app.services.pipeline import process_audio
                await process_audio("fake.wav", "user_abc")

        mock_score.assert_not_called()