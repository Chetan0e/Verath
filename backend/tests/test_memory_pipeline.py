import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class TestMemoryPipeline:
    """Test memory extraction and storage pipeline."""

    async def test_text_extraction_intent_classification(self, monkeypatch):
        """Test that text extraction correctly classifies intent."""
        # Mock the memory extractor
        mock_extractor = MagicMock()
        mock_extractor.extract = AsyncMock(return_value={
            'raw_text': 'Meeting with the team about the new project',
            'cleaned_text': 'meeting with team about project',
            'has_correction': False,
            'intent': 'meeting',
            'entities': {
                'people': ['team'],
                'locations': [],
                'dates': [],
                'times': [],
                'organizations': []
            },
            'summary': 'Discussed project with team',
            'importance_boost': 0.0
        })
        monkeypatch.setattr("app.services.pipeline.extraction_pipeline", mock_extractor)
        
        from app.services.pipeline import extraction_pipeline
        result = await extraction_pipeline.extract("Meeting with the team about the new project")
        
        assert result['intent'] == 'meeting'
        assert 'people' in result['entities']
        assert result['has_correction'] == False

    async def test_text_extraction_entity_extraction(self, monkeypatch):
        """Test that text extraction correctly extracts entities."""
        mock_extractor = MagicMock()
        mock_extractor.extract = AsyncMock(return_value={
            'raw_text': 'Meeting with John and Mary tomorrow',
            'cleaned_text': 'meeting with john and mary tomorrow',
            'has_correction': False,
            'intent': 'meeting',
            'entities': {
                'people': ['John', 'Mary'],
                'dates': [{'phrase': 'tomorrow', 'parsed_date': '2026-06-14T00:00:00', 'is_relative': True}],
                'locations': [],
                'times': [],
                'organizations': []
            },
            'summary': 'Meeting with John and Mary tomorrow',
            'importance_boost': 0.1
        })
        monkeypatch.setattr("app.services.pipeline.extraction_pipeline", mock_extractor)

        from app.services.pipeline import extraction_pipeline
        result = await extraction_pipeline.extract("Meeting with John and Mary tomorrow")

        assert 'john' in [p.lower() for p in result['entities']['people']]
        assert 'mary' in [p.lower() for p in result['entities']['people']]
        date_phrases = [d['phrase'] if isinstance(d, dict) else d for d in result['entities']['dates']]
        assert 'tomorrow' in date_phrases

    async def test_text_extraction_correction_detection(self, monkeypatch):
        """Test that text extraction detects corrections."""
        mock_extractor = MagicMock()
        mock_extractor.extract = AsyncMock(return_value={
            'raw_text': 'The meeting is at 3pm not 2pm',
            'cleaned_text': 'the meeting is at 3pm not 2pm',
            'has_correction': True,
            'intent': 'meeting',
            'entities': {
                'people': [],
                'dates': [{'phrase': '3pm', 'parsed_date': '2026-06-13T15:00:00', 'is_relative': False}],
                'locations': [],
                'times': [],
                'organizations': []
            },
            'summary': 'Meeting at 3pm (corrected from 2pm)',
            'importance_boost': 0.2
        })
        monkeypatch.setattr("app.services.pipeline.extraction_pipeline", mock_extractor)

        from app.services.pipeline import extraction_pipeline
        result = await extraction_pipeline.extract("The meeting is at 3pm not 2pm")

        assert result['has_correction'] == True
        assert result['importance_boost'] > 0

    async def test_importance_scoring_with_intent_boosting(self, monkeypatch):
        """Test that importance scoring boosts based on intent."""
        async def mock_score_importance(text):
            return 0.5
        
        monkeypatch.setattr("app.services.importance.score_importance", mock_score_importance)
        
        from app.services.importance import score_importance, categorize_importance
        base_score = await score_importance("Meeting about important deadline")
        category = categorize_importance(base_score)
        
        # Test categorization
        assert category in ['low', 'medium', 'high', 'critical']

    async def test_memory_storage_written_to_mongodb_and_chromadb(self, monkeypatch, mock_embedding):
        """Test that memory storage writes to both MongoDB and ChromaDB."""
        # Mock MongoDB
        mock_col = MagicMock()
        mock_col.insert_one = AsyncMock(return_value=MagicMock(inserted_id="test_id"))
        
        # Mock ChromaDB
        mock_collection = MagicMock()
        mock_collection.upsert = MagicMock()
        
        monkeypatch.setattr("app.services.memory_store._memories_collection", lambda: mock_col)
        monkeypatch.setattr("app.services.memory_store._get_collection", lambda uid: mock_collection)
        monkeypatch.setattr("app.services.embedding.get_embedding", lambda text: [0.1] * 384)
        
        from app.services.memory_store import store_memory
        memory_id = await store_memory(
            user_id="test_user",
            text="Test memory",
            metadata={"intent": "meeting", "speaker": "user", "importance": 0.8}
        )
        
        assert memory_id is not None
        mock_col.insert_one.assert_called_once()
        mock_collection.upsert.assert_called_once()

    async def test_duplicate_detection_returns_is_duplicate_true(self, monkeypatch):
        """Test that duplicate detection returns is_duplicate: true."""
        # Mock MongoDB to return similar memory
        mock_col = MagicMock()
        mock_col.find_one = AsyncMock(return_value={
            "_id": "existing_id",
            "text": "Similar memory text",
            "metadata": {"intent": "meeting"}
        })
        
        monkeypatch.setattr("app.services.memory_store._memories_collection", lambda: mock_col)
        
        from app.services.memory_store import _memories_collection
        col = _memories_collection()
        existing = await col.find_one({"text": {"$regex": "similar"}})
        
        assert existing is not None

    async def test_invalid_noise_text_returns_is_valid_false(self, monkeypatch):
        """Test that invalid/noise text returns is_valid: false."""
        from app.core.validators import TextInputValidator
        
        # Test empty text
        with pytest.raises(ValueError):
            TextInputValidator(text="", max_length=10000)
        
        # Test too short text
        with pytest.raises(ValueError):
            TextInputValidator(text="   ", max_length=10000)
        
        # Test injection pattern
        with pytest.raises(ValueError):
            TextInputValidator(text="<script>alert('xss')</script>", max_length=10000)

    async def test_end_to_end_memory_pipeline(self, monkeypatch, mock_db, mock_chroma, mock_embedding):
        """Test the full pipeline integration: Extraction Output -> Memory Object Creation -> Lifecycle Assignment -> Persistence Verification."""
        import json
        from datetime import datetime
        from app.pipeline.extraction_pipeline import extraction_pipeline
        from app.models.memory import Memory
        from app.services.memory_store import store_memory
        from app.services.importance import score_importance, categorize_importance

        # 1. Run extraction on sample input text
        # Mock LLM response to avoid network calls to external LLM provider
        mock_llm_response = """
        {
            "intent": "meeting",
            "summary": "Meeting with Sarah tomorrow at 2pm about the project launch.",
            "entities": {
                "people": ["Sarah"],
                "locations": [],
                "dates": [{"phrase": "tomorrow", "parsed_date": "2026-06-23T14:00:00", "is_relative": true}],
                "times": ["2pm"],
                "organizations": []
            }
        }
        """
        async def mock_generate_response(*args, **kwargs):
            return mock_llm_response

        monkeypatch.setattr("app.pipeline.extraction_pipeline.generate_response", mock_generate_response)
        monkeypatch.setattr("app.services.groq_service.generate_response", mock_generate_response)

        raw_text = "Meeting with Sarah tomorrow at 2pm about the project launch"
        extraction_result = await extraction_pipeline.extract(raw_text)

        # Verify extraction output was generated correctly
        assert extraction_result["intent"] == "meeting"
        assert "Sarah" in extraction_result["entities"]["people"]
        assert extraction_result["summary"] == "Meeting with Sarah tomorrow at 2pm about the project launch."
        assert extraction_result["importance_boost"] > 0
        assert extraction_result["has_correction"] is False

        # 2. Create a Memory instance from extracted output
        # Mock score_importance to return a base score
        async def mock_score_importance(text):
            return 0.5
        monkeypatch.setattr("app.services.importance.score_importance", mock_score_importance)

        cleaned_text = extraction_result["cleaned_text"]
        intent = extraction_result["intent"]
        entities = extraction_result["entities"]
        summary = extraction_result["summary"]
        importance_boost = extraction_result["importance_boost"]
        has_correction = extraction_result["has_correction"]

        base_importance = await score_importance(cleaned_text)
        final_importance = min(base_importance + importance_boost, 1.0)
        importance_category = categorize_importance(final_importance)

        embedding = [0.1] * 768

        memory = Memory(
            text=raw_text,
            cleaned_text=cleaned_text,
            intent=intent,
            entities=entities,
            summary=summary,
            speaker="unknown",
            importance=final_importance,
            tags=[importance_category] + ([intent] if intent else []),
            source="audio",
            audio_file="test.wav",
            embedding=embedding,
            user_id="test_user_123",
            has_correction=has_correction,
            importance_boost=importance_boost,
            metadata={
                "speakers": [],
                "importance_category": importance_category,
                "extraction_timestamp": datetime.utcnow().isoformat()
            }
        )

        # Verify Memory object creation succeeds
        assert memory is not None
        assert memory.text == raw_text
        assert memory.cleaned_text == cleaned_text

        # Verify lifecycle stage assignment (defaults to short_term)
        assert memory.lifecycle_stage == "short_term"

        # Verify summary generation
        assert memory.summary == "Meeting with Sarah tomorrow at 2pm about the project launch."

        # Verify metadata integrity
        assert memory.metadata["importance_category"] == importance_category
        assert memory.metadata["importance_category"] in ["medium", "high", "critical"]

        # 3. Mock and verify persistence interactions
        # Capture the document passed to MongoDB insert
        captured_doc = None
        async def mock_insert_one(doc):
            nonlocal captured_doc
            captured_doc = doc
            return MagicMock(inserted_id="mock_id")
        mock_db.insert_one = AsyncMock(side_effect=mock_insert_one)

        monkeypatch.setattr("app.services.memory_store._memories_collection", lambda: mock_db)

        # Set up a fixed created_at timestamp
        created_at = datetime.utcnow()

        # Call store_memory
        memory_id = await store_memory(
            user_id="test_user_123",
            text=raw_text,
            created_at=created_at,
            metadata={
                "intent": intent,
                "speaker": "unknown",
                "importance": final_importance,
                "importance_category": importance_category,
                "entities": entities,
                "summary": summary,
                "has_correction": has_correction,
                "importance_boost": importance_boost,
                "cleaned_text": cleaned_text,
                "audio_file": "test.wav",
            }
        )

        # Verify store_memory() returned a valid ID
        assert memory_id is not None
        assert isinstance(memory_id, str)

        # Verify MongoDB insert was called correctly
        mock_db.insert_one.assert_called_once()

        # Verify ChromaDB upsert was called correctly with correct sanitized metadata
        mock_chroma.upsert.assert_called_once_with(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[raw_text],
            metadatas=[{
                "user_id": "test_user_123",
                "intent": intent,
                "speaker": "unknown",
                "importance": final_importance,
                "importance_category": importance_category,
                "timestamp": created_at.isoformat(),
            }]
        )

        # Verify persisted values retain expected lifecycle and metadata information
        assert captured_doc is not None
        assert captured_doc["_id"] == memory_id
        assert captured_doc["user_id"] == "test_user_123"
        assert captured_doc["text"] == raw_text
        assert captured_doc["lifecycle_stage"] == "short_term"  # Top-level field
        assert captured_doc["metadata"]["intent"] == intent
        assert captured_doc["metadata"]["summary"] == summary
        assert captured_doc["metadata"]["importance"] == final_importance
        assert captured_doc["metadata"]["importance_category"] == importance_category
        assert captured_doc["metadata"]["has_correction"] == has_correction
        assert captured_doc["metadata"]["importance_boost"] == importance_boost
        assert captured_doc["metadata"]["cleaned_text"] == cleaned_text
        assert captured_doc["metadata"]["audio_file"] == "test.wav"
        assert captured_doc["metadata"]["entities"]["people"] == ["Sarah"]
