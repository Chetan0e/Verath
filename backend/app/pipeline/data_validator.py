import logging
from typing import Dict, Any, Optional
from datetime import datetime
from app.core.logging_config import logger

class DataValidator:
    """Validates and filters incoming data to prevent noise and duplicates."""
    
    MIN_TEXT_LENGTH = 10  # Minimum characters for valid text
    MAX_TEXT_LENGTH = 10000  # Maximum characters
    SIMILARITY_THRESHOLD = 0.85  # Threshold for duplicate detection
    
    def __init__(self):
        self.noise_patterns = [
            r'^\s*$',
            r'^(um|uh|ah|mm)+\s*$',
            r'^[\s\.\,]+$',
            r'\b(test|testing|hello|hi there)\b\s*$'
        ]
    
    async def validate_memory(self, text: str, existing_memories: list = None) -> Dict[str, Any]:
        """
        Validate memory text for:
        - Minimum length
        - Noise filtering
        - Duplicate detection
        """
        try:
            # Check 1: Length validation
            if not self._is_valid_length(text):
                return {
                    "valid": False,
                    "reason": "invalid_length",
                    "message": f"Text must be between {self.MIN_TEXT_LENGTH} and {self.MAX_TEXT_LENGTH} characters"
                }
            
            # Check 2: Noise filtering
            if self._is_noise(text):
                return {
                    "valid": False,
                    "reason": "noise",
                    "message": "Text appears to be noise or filler"
                }
            
            # Check 3: Duplicate detection
            if existing_memories:
                duplicate_check = await self._check_duplicate(text, existing_memories)
                if duplicate_check["is_duplicate"]:
                    return {
                        "valid": False,
                        "reason": "duplicate",
                        "message": "Similar memory already exists",
                        "duplicate_of": duplicate_check["duplicate_id"]
                    }
            
            return {
                "valid": True,
                "reason": "valid",
                "message": "Memory passed validation"
            }
            
        except Exception as e:
            logger.error(f"Error validating memory: {e}", exc_info=True)
            return {
                "valid": False,
                "reason": "validation_error",
                "message": str(e)
            }
    
    def _is_valid_length(self, text: str) -> bool:
        """Check if text meets length requirements."""
        text_length = len(text.strip())
        return self.MIN_TEXT_LENGTH <= text_length <= self.MAX_TEXT_LENGTH
    
    def _is_noise(self, text: str) -> bool:
        """Check if text is noise or filler."""
        import re
        
        text_lower = text.lower().strip()
        
        # Check against noise patterns
        for pattern in self.noise_patterns:
            if re.match(pattern, text_lower):
                return True
        
        # Check for excessive repetition
        words = text.split()
        if len(words) > 0:
            unique_words = set(words)
            if len(unique_words) / len(words) < 0.3:
                return True
        
        # Check for excessive punctuation
        if sum(1 for c in text if c in '.,!?') / len(text) > 0.5:
            return True
        
        return False
    
    async def _check_duplicate(self, text: str, existing_memories: list) -> Dict[str, Any]:
        """Check for duplicate or similar memories."""
        # Simple similarity check using word overlap
        # In production, use embeddings for better similarity detection
        
        text_words = set(text.lower().split())
        
        for memory in existing_memories:
            mem_text = memory.get('cleaned_text') or memory.get('text', '')
            mem_words = set(mem_text.lower().split())
            
            # Calculate Jaccard similarity
            if text_words and mem_words:
                intersection = text_words & mem_words
                union = text_words | mem_words
                similarity = len(intersection) / len(union) if union else 0
                
                if similarity >= self.SIMILARITY_THRESHOLD:
                    return {
                        "is_duplicate": True,
                        "similarity": similarity,
                        "duplicate_id": memory.get('_id')
                    }
        
        return {
            "is_duplicate": False,
            "similarity": 0.0
        }
    
    def sanitize_input(self, text: str) -> str:
        """Sanitize input text to prevent injection attacks."""
        import re
        
        # Remove potentially dangerous patterns
        text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        
        # Limit length
        text = text[:self.MAX_TEXT_LENGTH]
        
        return text.strip()

data_validator = DataValidator()


def validate_text(text: str):
    """
    Backward-compatible validation helper expected by legacy tests.
    """

    sanitized = data_validator.sanitize_input(text)

    is_valid = (
        data_validator._is_valid_length(sanitized)
        and not data_validator._is_noise(sanitized)
    )

    reason = "valid" if is_valid else "invalid"

    return is_valid, reason