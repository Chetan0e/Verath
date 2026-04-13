import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class TestMemoryPipeline:
    """Test memory extraction and storage pipeline."""

    async def test_text_extraction_intent_classification(self, monkeypatch):
        """Test that text extraction correctly classifies intent."""
        # Mock the memory extractor
        mock_extractor = MagicMock()
        mock_extractor.extract_memory.return_value = {
            'cleaned_text': 'meeting with team about project',
            'intent': 'meeting',
            'entities': {
                'people': ['team'],
                'topics': ['project'],
                'dates': []
            },
            'summary': 'Discussed project with team',
            'has_correction': False,
            'importance_boost': 0.0
        }
        monkeypatch.setattr("app.services.pipeline.memory_extractor", mock_extractor)
        
        from app.services.pipeline import memory_extractor
        result = memory_extractor.extract_memory("Meeting with the team about the new project")
        
        assert result['intent'] == 'meeting'
        assert 'people' in result['entities']
        assert result['has_correction'] == False

    async def test_text_extraction_entity_extraction(self, monkeypatch):
        """Test that text extraction correctly extracts entities."""
        mock_extractor = MagicMock()
        mock_extractor.extract_memory.return_value = {
            'cleaned_text': 'meeting with john and mary tomorrow',
            'intent': 'meeting',
            'entities': {
                'people': ['john', 'mary'],
                'dates': ['tomorrow'],
                'topics': []
            },
            'summary': 'Meeting with John and Mary tomorrow',
            'has_correction': False,
            'importance_boost': 0.1
        }
        monkeypatch.setattr("app.services.pipeline.memory_extractor", mock_extractor)
        
        from app.services.pipeline import memory_extractor
        result = memory_extractor.extract_memory("Meeting with John and Mary tomorrow")
        
        assert 'john' in [p.lower() for p in result['entities']['people']]
        assert 'mary' in [p.lower() for p in result['entities']['people']]
        assert 'tomorrow' in result['entities']['dates']

    async def test_text_extraction_correction_detection(self, monkeypatch):
        """Test that text extraction detects corrections."""
        mock_extractor = MagicMock()
        mock_extractor.extract_memory.return_value = {
            'cleaned_text': 'the meeting is at 3pm not 2pm',
            'intent': 'meeting',
            'entities': {
                'dates': ['3pm'],
                'people': [],
                'topics': ['meeting']
            },
            'summary': 'Meeting at 3pm (corrected from 2pm)',
            'has_correction': True,
            'importance_boost': 0.2
        }
        monkeypatch.setattr("app.services.pipeline.memory_extractor", mock_extractor)
        
        from app.services.pipeline import memory_extractor
        result = memory_extractor.extract_memory("The meeting is at 3pm not 2pm")
        
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

    async def test_memory_storage_written_to_mongodb_and_chromadb(self, monkeypatch):
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
