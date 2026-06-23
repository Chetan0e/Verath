"""
Tests for issue #119 - Dual divergent extraction classes.

Verifies that after the fix (services/pipeline.py uses ExtractionPipeline),
both the /extract API endpoint and the audio ingestion path use the same
canonical extractor, producing consistent dates, intent labels, and
entity structures that the reminder system can reliably parse.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime


class TestExtractionPathDivergence:
    """
    Document the pre-fix behavioral differences between the two extractors.
    These tests act as regression guards: if they start failing in unexpected
    ways it signals a deeper architecture change.
    """

    def test_extraction_pipeline_dates_are_iso_dicts(self):
        """ExtractionPipeline stores dates as dicts with an ISO-formatted parsed_date."""
        from app.pipeline.extraction_pipeline import ExtractionPipeline
        pipeline = ExtractionPipeline()
        result = pipeline._parse_temporal_entities("Meeting tomorrow")

        assert len(result["dates"]) > 0, "Expected at least one date entry for 'tomorrow'"
        first = result["dates"][0]
        assert isinstance(first, dict), (
            "ExtractionPipeline must produce dict date entries, not plain strings"
        )
        assert "parsed_date" in first, "Date dict must contain a 'parsed_date' key"
        # Must be a parseable ISO string — the reminder service depends on this
        datetime.fromisoformat(first["parsed_date"])  # raises ValueError if not ISO

    def test_memory_extractor_dates_are_raw_strings(self):
        """MemoryExtractor stores dates as plain matched strings, not ISO."""
        from app.services.memory_extractor import MemoryExtractor
        extractor = MemoryExtractor()
        result = extractor.extract_entities("Meeting tomorrow")

        assert len(result["dates"]) > 0, "Expected at least one date match for 'tomorrow'"
        first = result["dates"][0]
        assert isinstance(first, str), (
            "MemoryExtractor produces raw string dates (e.g. 'tomorrow'), not dicts"
        )

    def test_extraction_pipeline_unmatched_intent_returns_general(self):
        """ExtractionPipeline._detect_intent falls back to 'general', never None."""
        from app.pipeline.extraction_pipeline import ExtractionPipeline
        pipeline = ExtractionPipeline()
        intent = pipeline._detect_intent("The sky is blue today")
        assert intent == "general", (
            f"Expected fallback intent 'general', got {intent!r}"
        )

    def test_memory_extractor_unmatched_intent_returns_none(self):
        """MemoryExtractor.extract_intent returns None when no patterns match."""
        from app.services.memory_extractor import MemoryExtractor
        extractor = MemoryExtractor()
        intent = extractor.extract_intent("The sky is blue today")
        assert intent is None, (
            f"Expected None from MemoryExtractor fallback, got {intent!r}"
        )


class TestAudioPathUsesExtractionPipeline:
    """
    After the fix, services/pipeline.py imports and calls extraction_pipeline,
    not memory_extractor. These tests verify that module-level wiring is correct.
    """

    def test_pipeline_module_exposes_extraction_pipeline(self):
        """services/pipeline.py must import extraction_pipeline after the fix."""
        import app.services.pipeline as pipeline_module
        assert hasattr(pipeline_module, "extraction_pipeline"), (
            "services/pipeline.py does not expose 'extraction_pipeline'. "
            "Ensure the import was changed from memory_extractor to extraction_pipeline."
        )

    def test_pipeline_module_does_not_expose_memory_extractor(self):
        """services/pipeline.py must not import memory_extractor after the fix."""
        import app.services.pipeline as pipeline_module
        assert not hasattr(pipeline_module, "memory_extractor"), (
            "services/pipeline.py still exposes 'memory_extractor'. "
            "The old import was not removed."
        )

    async def test_process_audio_calls_extraction_pipeline_extract(self, monkeypatch):
        """process_audio() delegates extraction to extraction_pipeline.extract()."""
        mock_result = {
            "raw_text": "meeting tomorrow",
            "cleaned_text": "meeting tomorrow",
            "has_correction": False,
            "intent": "meeting",
            "entities": {
                "people": [],
                "dates": [{"phrase": "tomorrow", "parsed_date": "2026-06-14T00:00:00", "is_relative": True}],
                "locations": [],
                "organizations": [],
                "times": [],
            },
            "summary": "Meeting scheduled for tomorrow",
            "importance_boost": 0.2,
        }
        mock_extract = AsyncMock(return_value=mock_result)
        monkeypatch.setattr(
            "app.services.pipeline.extraction_pipeline",
            MagicMock(extract=mock_extract),
        )
        monkeypatch.setattr("app.services.pipeline.is_private", AsyncMock(return_value=False))
        monkeypatch.setattr("app.services.pipeline.transcribe", MagicMock(return_value="meeting tomorrow"))
        monkeypatch.setattr("app.services.pipeline.get_embedding", MagicMock(return_value=[0.1] * 768))
        monkeypatch.setattr("app.services.pipeline.identify_speakers", MagicMock(return_value={}))
        monkeypatch.setattr("app.services.pipeline.get_primary_speaker", MagicMock(return_value="unknown"))
        monkeypatch.setattr("app.services.speaker_training.identify_voice", MagicMock(return_value="unknown"))
        monkeypatch.setattr("app.services.pipeline.score_importance", AsyncMock(return_value=0.5))
        monkeypatch.setattr("app.services.pipeline.categorize_importance", MagicMock(return_value="medium"))
        monkeypatch.setattr("app.services.pipeline.store_memory", AsyncMock(return_value="mem_id_1"))

        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
        try:
            from app.services.pipeline import process_audio
            await process_audio(tmp_path, "test_user")
            mock_extract.assert_called_once_with("meeting tomorrow")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class TestDateFormatConsistency:
    """
    ExtractionPipeline dates are ISO-dict objects; the reminder service's primary
    parse path (datetime.fromisoformat) works correctly with them. This class
    proves both the fix and the root cause of the silent reminder failure.
    """

    def test_extraction_pipeline_date_is_parseable_iso(self):
        """Every date entry from ExtractionPipeline carries a fromisoformat-ready string."""
        from app.pipeline.extraction_pipeline import ExtractionPipeline
        pipeline = ExtractionPipeline()
        result = pipeline._parse_temporal_entities("Submit report by tomorrow")

        for entry in result["dates"]:
            parsed_str = entry.get("parsed_date")
            assert parsed_str is not None, "parsed_date key must exist and be non-None"
            dt = datetime.fromisoformat(parsed_str)
            assert isinstance(dt, datetime), "parsed_date must deserialize to a datetime"

    def test_reminder_service_correctly_processes_extraction_pipeline_date_format(self):
        """
        Simulate reminder_service.check_and_fire_reminders date-parsing logic
        against the ExtractionPipeline date dict format.
        """
        date_entry = {
            "phrase": "tomorrow",
            "parsed_date": "2026-06-14T10:00:00",
            "is_relative": True,
        }
        # Exact logic from reminder_service.py
        if isinstance(date_entry, dict):
            parsed_str = date_entry.get("parsed_date") or date_entry.get("phrase")
        else:
            parsed_str = date_entry

        assert parsed_str == "2026-06-14T10:00:00"
        parsed_date = datetime.fromisoformat(parsed_str.replace("Z", "+00:00"))
        assert isinstance(parsed_date, datetime)

    def test_raw_string_date_fails_fromisoformat(self):
        """
        Documents why audio-recorded reminders silently fail without the fix:
        MemoryExtractor's raw 'tomorrow' string cannot be parsed by fromisoformat.
        The reminder service falls back to dateparser at check-time, not record-time,
        producing wrong timestamps.
        """
        raw_date_from_memory_extractor = "tomorrow"
        with pytest.raises(ValueError):
            datetime.fromisoformat(raw_date_from_memory_extractor)


class TestOutputSchemaConsistency:
    """
    ExtractionPipeline.extract() returns all keys that process_audio() consumes,
    and always returns a string intent — both required for downstream consistency.
    """

    async def test_extract_returns_all_keys_needed_by_process_audio(self, monkeypatch):
        """ExtractionPipeline.extract() output satisfies every key process_audio() reads."""
        monkeypatch.setattr(
            "app.pipeline.extraction_pipeline.generate_response",
            AsyncMock(return_value='{"intent": "meeting", "summary": "Quick note", "entities": {}}'),
        )
        from app.pipeline.extraction_pipeline import ExtractionPipeline
        pipeline = ExtractionPipeline()
        result = await pipeline.extract("Just a quick note")

        required = {"cleaned_text", "intent", "entities", "summary", "has_correction", "importance_boost"}
        missing = required - result.keys()
        assert not missing, (
            f"ExtractionPipeline.extract() is missing keys needed by process_audio(): {missing}"
        )

    async def test_extract_intent_is_always_string_never_none(self, monkeypatch):
        """
        ExtractionPipeline.extract() always returns a string intent.
        MemoryExtractor returns None for unmatched text, causing inconsistent
        metadata across ingestion paths.
        """
        monkeypatch.setattr(
            "app.pipeline.extraction_pipeline.generate_response",
            AsyncMock(return_value='{"intent": "general", "summary": "Unrelated text", "entities": {}}'),
        )
        from app.pipeline.extraction_pipeline import ExtractionPipeline
        pipeline = ExtractionPipeline()
        result = await pipeline.extract("The sky is blue today")

        assert result["intent"] is not None, "intent must never be None"
        assert isinstance(result["intent"], str), (
            f"intent must be a string, got {type(result['intent'])}"
        )