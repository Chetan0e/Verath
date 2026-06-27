import re
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from app.services.groq_service import generate_response
from app.core.exceptions import LLMError

logger = logging.getLogger("Verath")


class MemoryExtractor:
    """Intelligent memory extraction with conflict resolution."""
    
    def __init__(self):
        self.correction_patterns = [
            r'(?:no|wait|actually|sorry|correction|ignore|scratch that|never mind)',
            r'(?:change|update|modify|replace)',
            r'(?:instead of|rather than)',
        ]
        
        self.intent_patterns = {
            'meeting': r'(?:meet|meeting|schedule|appointment|call|discuss|talk)',
            'deadline': r'(?:deadline|due|due date|submit|finish by|complete by)',
            'task': r'(?:task|todo|need to|have to|must|should)',
            'commitment': r'(?:promise|commit|agree|will|going to)',
            'reminder': r'(?:remind|remember|don\'t forget)',
        }
        
        self.date_patterns = [
            r'(?:today|tomorrow|yesterday)',
            r'(?:day after tomorrow|in \d+ days|next week)',
            r'(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* \d{1,2}(?:st|nd|rd|th)?',
        ]
        
        self.person_patterns = [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Proper names
            r'(?:with|from|to|by) [A-Z][a-z]+',  # Names with prepositions
        ]
    
    def detect_corrections(self, text: str) -> Tuple[bool, str]:
        """
        Detect if text contains corrections and return the corrected version.
        Example: "let's meet tomorrow... no no day after tomorrow"
        Returns: (has_correction, corrected_text)
        """
        # 1. Split into sentences/segments for more granular analysis
        # Using a slightly more robust split that keeps common abbreviations in mind
        segments = re.split(r'(?<=[.!?])\s+|(?<=\.\.\.)\s*', text)
        segments = [s.strip() for s in segments if s.strip()]
        
        if not segments:
            return False, text

        # 2. Handle "no no" or "no wait" patterns at the start of a segment
        # This is a common pattern for immediate speech correction
        correction_start_pattern = r'^(?:no\s*,?\s*|wait(?!\s+for)\s*,?\s*|actually\s*,?\s*|sorry\s*,?\s*|correction\s*,?\s*|correction\s*:?\s*)+(.*)$'
        
        corrected_segments = []
        has_correction = False
        
        for i, segment in enumerate(segments):
            match = re.match(correction_start_pattern, segment, re.IGNORECASE)
            if match and i > 0:
                # This segment looks like a correction of the PREVIOUS one
                # If the previous segment was short or very similar, we discard it
                content = match.group(1).strip()
                if content:
                    # Replace the last added segment with this one
                    logger.info(f"Correction detected: Discarding '{segments[i-1]}' for '{content}'")
                    if corrected_segments:
                        corrected_segments.pop()
                    corrected_segments.append(content)
                    has_correction = True
                else:
                    # It's just a filler like "No, wait." - we just ignore it and keep going
                    # but we'll flag it so the NEXT segment might be seen as the correction
                    has_correction = True
            elif match and i == 0:
                # Correction pattern at the very beginning of the transcript
                content = match.group(1).strip()
                if content:
                    corrected_segments.append(content)
                    has_correction = True
                # if empty content, just skip it (it's a filler at start)
            else:
                # Normal segment
                corrected_segments.append(segment)
        
        if has_correction:
            return True, ' '.join(corrected_segments)
            
        # 3. Fallback to middle-of-sentence "no no" patterns if not handled above
        # But be VERY conservative - only if "no no" or "wait no" is present
        mid_correction_pattern = r'(.+?)(?:\s+(?:no\s+no|wait\s+no|actually\s+no|sorry\s+no)\s+)(.+)'
        mid_match = re.search(mid_correction_pattern, text, re.IGNORECASE)
        if mid_match:
            # Only treat as correction if the second part is substantial
            if len(mid_match.group(2)) > 5:
                logger.info(f"Mid-sentence correction detected: '{text}'")
                return True, mid_match.group(2).strip()
        
        return False, text
    
    def extract_intent(self, text: str) -> Optional[str]:
        """Extract the primary intent from text."""
        intent_scores = {}
        
        for intent, pattern in self.intent_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            intent_scores[intent] = len(matches)
        
        if not intent_scores or sum(intent_scores.values()) == 0:
            return None
        
        # Return intent with highest score
        return max(intent_scores, key=intent_scores.get)
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract entities like dates, people, locations."""
        entities = {
            'dates': [],
            'people': [],
            'locations': [],
            'organizations': []
        }
        
        # Extract dates
        for pattern in self.date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities['dates'].extend(matches)
        
        # Extract people
        for pattern in self.person_patterns:
            matches = re.findall(pattern, text)
            entities['people'].extend(matches)
        
        # Remove duplicates
        for key in entities:
            entities[key] = list(set(entities[key]))
        
        return entities
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove filler words and hesitations
        filler_words = ['um', 'uh', 'like', 'you know', 'actually', 'basically']
        for filler in filler_words:
            text = re.sub(rf'\b{filler}\b', '', text, flags=re.IGNORECASE)
        
        # Remove repeated words (e.g., "meet tomorrow, meet tomorrow" -> "meet tomorrow")
        text = re.sub(r'\b(\w+)(\s+\1)+\b', r'\1', text, flags=re.IGNORECASE)
        
        # Remove repeated phrases (e.g., "let's meet tomorrow, let's meet tomorrow" -> "let's meet tomorrow")
        text = re.sub(r'(.{4,})\s+\1', r'\1', text, flags=re.IGNORECASE)
        
        # Remove consecutive duplicates like "no no" -> "no"
        text = re.sub(r'\b(\w+)\s+\1\b', r'\1', text, flags=re.IGNORECASE)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    async def _combined_llm_call(self, text: str, intent: Optional[str] = None) -> Dict:
        """Single LLM call returning both summary and importance score."""
        intent_context = f" The text intent is: {intent}." if intent else ""
        prompt = f"""Analyze this text and return ONLY a valid JSON object:{intent_context}
    Text: "{text}"
    Return exactly this structure:
    {{
      "summary": "<one clear sentence capturing the key information>",
      "importance": <float between 0.0 and 1.0>
    }}
    For importance consider: deadlines, appointments, action items, commitments, emotional significance, key insights, contact information."""
        try:
            response = await generate_response(prompt, response_format={"type": "json_object"})
            cleaned = re.sub(r'```(?:json)?\s*|\s*```', '', response).strip()
            parsed = json.loads(cleaned)
            summary = str(parsed.get("summary", "")).strip()
            importance = min(max(float(parsed.get("importance", 0.5)), 0.0), 1.0)
            if not summary:
                raise ValueError("Empty summary returned by LLM")
            return {"summary": summary, "importance": importance}
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            logger.warning(f"Combined LLM call parsing failed ({e}), using fallbacks")
            sentences = re.split(r'[.!?]+', text)
            fallback_summary = sentences[0].strip() if sentences else text
            return {"summary": fallback_summary, "importance": 0.5}
    
    def resolve_conflicts(self, new_text: str, existing_memories: List[Dict]) -> Tuple[bool, Optional[str]]:
        """
        Resolve conflicts with existing memories.
        Returns: (should_update, memory_id_to_update)
        """
        for memory in existing_memories:
            existing_text = memory.get('text', '')
            similarity = self._calculate_similarity(new_text, existing_text)
            
            # If high similarity and new text contains corrections, update existing
            if similarity > 0.7:
                has_correction, _ = self.detect_corrections(new_text)
                if has_correction:
                    return True, memory.get('_id')
        
        return False, None
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Simple similarity calculation based on word overlap."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    async def extract_memory(self, text: str) -> Dict:
        """
        Extract structured memory from raw text.
        Returns: {
            'cleaned_text': str,
            'intent': Optional[str],
            'entities': Dict[str, List[str]],
            'summary': str,
            'has_correction': bool,
            'importance_boost': float
        }
        """
        logger.info(f"Extracting memory from text: {text[:100]}...")
        
        # Detect corrections
        has_correction, corrected_text = self.detect_corrections(text)
        final_text = corrected_text if has_correction else text
        
        # Clean text
        cleaned_text = self.clean_text(final_text)
        
        # Extract intent
        intent = self.extract_intent(cleaned_text)
        
        # Extract entities
        entities = self.extract_entities(cleaned_text)
        
        # Generate summary
        combined = await self._combined_llm_call(cleaned_text, intent)
        summary = combined["summary"]
        llm_importance = combined["importance"]
        
        # Calculate importance boost based on intent and entities
        importance_boost = self._calculate_importance_boost(intent, entities)
        
        logger.info(f"Memory extracted - Intent: {intent}, Summary: {summary}, LLM Importance: {llm_importance:.2f}")
        
        return {
            'cleaned_text': cleaned_text,
            'intent': intent,
            'entities': entities,
            'summary': summary,
            'importance': llm_importance,
            'has_correction': has_correction,
            'importance_boost': importance_boost
        }
    
    def _calculate_importance_boost(self, intent: Optional[str], entities: Dict) -> float:
        """Calculate importance boost based on intent and entities."""
        boost = 0.0
        
        # Intent-based boost
        intent_boosts = {
            'deadline': 0.3,
            'meeting': 0.25,
            'commitment': 0.2,
            'task': 0.15,
            'reminder': 0.1,
        }
        
        if intent and intent in intent_boosts:
            boost += intent_boosts[intent]
        
        # Entity-based boost
        if entities.get('dates'):
            boost += 0.1
        if entities.get('people'):
            boost += 0.05
        
        return min(boost, 0.5)  # Cap at 0.5


# Global instance
memory_extractor = MemoryExtractor()
