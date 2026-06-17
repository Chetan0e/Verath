import logging
import re
import dateparser
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from app.services.groq_service import generate_response
from app.core.logging_config import logger

class ExtractionPipeline:
    """Multi-stage hybrid extraction pipeline with rule-based + LLM refinement."""
    
    # Correction detection patterns
    CORRECTION_PATTERNS = [
        r'\bno no\b',
        r'\bi mean\b',
        r'\bi meant\b',
        r'\bnot that\b',
        r'\bactually\b',
        r'\bwait\b',
        r'\bcorrection\b',
        r'\bsorry\b'
    ]
    
    # Intent detection patterns
    INTENT_PATTERNS = {
        'meeting': [
            r'\bmeet\b', r'\bmeeting\b', r'\bcall\b', r'\bconference\b', 
            r'\bdiscuss\b', r'\bappointment\b', r'\bget together\b'
        ],
        'deadline': [
            r'\bdeadline\b', r'\bdue\b', r'\bsubmit\b', r'\bcomplete by\b',
            r'\bfinish by\b', r'\bneed to\b'
        ],
        'task': [
            r'\btask\b', r'\bto do\b', r'\bneed to\b', r'\bhave to\b',
            r'\bgotta\b', r'\bshould\b'
        ],
        'commitment': [
            r'\bpromise\b', r'\bcommit\b', r'\bagree\b', r'\bwill\b',
            r'\bsure\b', r'\babsolutely\b'
        ],
        'reminder': [
            r'\bremind\b', r'\bdon\'t forget\b', r'\bremember\b',
            r'\bnote\b', r'\bmake sure\b'
        ]
    }
    
    def __init__(self):
        self.correction_regex = re.compile('|'.join(self.CORRECTION_PATTERNS), re.IGNORECASE)
        self.intent_regexes = {
            intent: re.compile('|'.join(patterns), re.IGNORECASE)
            for intent, patterns in self.INTENT_PATTERNS.items()
        }
    
    async def extract(self, raw_text: str) -> Dict[str, Any]:
        """
        Run full extraction pipeline:
        1. Rule-based cleaning
        2. Correction detection
        3. Temporal parsing
        4. Intent detection (rule-based)
        5. Entity extraction (rule-based)
        6. LLM refinement
        """
        try:
            logger.info("Starting extraction pipeline")
            
            # Stage 1: Rule-based cleaning
            cleaned_text = self._clean_text(raw_text)
            
            # Stage 2: Correction detection
            has_correction, corrected_text = self._detect_correction(cleaned_text)
            
            # Stage 3: Temporal parsing
            temporal_entities = self._parse_temporal_entities(corrected_text)
            
            # Stage 4: Intent detection (rule-based)
            intent = self._detect_intent(corrected_text)
            
            # Stage 5: Entity extraction
            entities = self._extract_entities(corrected_text, temporal_entities)
            
            # Stage 6: LLM refinement
            refined_data = await self._llm_refine(corrected_text, intent, entities)
            
            # Combine results
            result = {
                "raw_text": raw_text,
                "cleaned_text": corrected_text,
                "has_correction": has_correction,
                "intent": refined_data.get("intent", intent),
                "entities": {
                    **entities,
                    **refined_data.get("entities", {})
                },
                "summary": refined_data.get("summary", ""),
                "importance": min(max(float(refined_data.get("importance", 0.5)), 0.0), 1.0),
                "importance_boost": self._calculate_importance_boost(intent, entities)
            }
            
            logger.info(f"Extraction complete: intent={result['intent']}, corrections={has_correction}")
            return result
            
        except Exception as e:
            logger.error(f"Error in extraction pipeline: {e}", exc_info=True)
            raise
    
    def _clean_text(self, text: str) -> str:
        """Rule-based text cleaning."""
        # Remove filler words and repetitions
        text = re.sub(r'\b(um|uh|ah|like|you know)\b', '', text, flags=re.IGNORECASE)
        # Fix common transcription errors
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _detect_correction(self, text: str) -> tuple[bool, str]:
        """Detect speech corrections and handle them using segment analysis."""
        # Split into segments
        segments = re.split(r'(?<=[.!?])\s+|(?<=\.\.\.)\s*', text)
        segments = [s.strip() for s in segments if s.strip()]
        
        if not segments:
            return False, text

        # Detection pattern for segment starts
        correction_start_pattern = r'^(?:no\s+no|wait(?!\s+for)|actually|sorry|correction|i\s+mean|not\s+that)+(.*)$'
        
        corrected_segments = []
        has_correction = False
        
        for i, segment in enumerate(segments):
            match = re.match(correction_start_pattern, segment, re.IGNORECASE)
            if match and i > 0:
                content = match.group(1).strip()
                if content:
                    # Replace the last segment
                    if corrected_segments:
                        corrected_segments.pop()
                    corrected_segments.append(content)
                    has_correction = True
                else:
                    # Filler like "Wait." or "Actually." - just skip this segment
                    has_correction = True
            elif match and i == 0:
                content = match.group(1).strip()
                if content:
                    corrected_segments.append(content)
                    has_correction = True
            else:
                corrected_segments.append(segment)
                
        if has_correction:
            return True, ' '.join(corrected_segments)
            
        return False, text
    
    def _parse_temporal_entities(self, text: str) -> Dict[str, Any]:
        """Parse temporal expressions using dateparser."""
        temporal_entities = {
            "dates": [],
            "times": [],
            "relative_times": []
        }
        
        # Find potential temporal expressions
        time_patterns = [
            r'\btomorrow\b',
            r'\byesterday\b',
            r'\btoday\b',
            r'\bday after tomorrow\b',
            r'\bnext week\b',
            r'\bnext month\b',
            r'\bin \d+ days\b',
            r'\bin \d+ hours\b',
            r'\bnext \w+day\b'
        ]
        
        for pattern in time_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                phrase = match.group()
                parsed = dateparser.parse(phrase, settings={
                    'RELATIVE_BASE': datetime.utcnow(),
                    'PREFER_DATES_FROM': 'future'
                })
                
                if parsed:
                    temporal_entities["dates"].append({
                        "phrase": phrase,
                        "parsed_date": parsed.isoformat(),
                        "is_relative": True
                    })
        
        return temporal_entities
    
    def _detect_intent(self, text: str) -> Optional[str]:
        """Rule-based intent detection."""
        for intent, regex in self.intent_regexes.items():
            if regex.search(text):
                return intent
        return "general"
    
    def _extract_entities(self, text: str, temporal_entities: Dict) -> Dict[str, Any]:
        """Extract entities from text."""
        entities = {
            "people": self._extract_people(text),
            "locations": self._extract_locations(text),
            "organizations": self._extract_organizations(text),
            "dates": temporal_entities.get("dates", []),
            "times": temporal_entities.get("times", [])
        }
        return entities
    
    def _extract_people(self, text: str) -> List[str]:
        """Extract person names (simple pattern matching)."""
        # Capitalized words that might be names
        pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        matches = re.findall(pattern, text)
        # Filter out common non-name words
        stop_words = {'The', 'This', 'That', 'It', 'He', 'She', 'They', 'Today', 'Tomorrow'}
        names = [m for m in matches if m not in stop_words and len(m) > 2]
        return list(set(names))[:5]  # Return unique names, max 5
    
    def _extract_locations(self, text: str) -> List[str]:
        """Extract location names."""
        location_patterns = [
            r'\bat \b[A-Z][a-z]+\b',
            r'\bin \b[A-Z][a-z]+\b',
            r'\bto \b[A-Z][a-z]+\b'
        ]
        locations = []
        for pattern in location_patterns:
            matches = re.findall(pattern, text)
            locations.extend([m.strip() for m in matches])
        return list(set(locations))[:3]
    
    def _extract_organizations(self, text: str) -> List[str]:
        """Extract organization names."""
        # Simple pattern: capitalized words that might be org names
        org_patterns = [
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:Inc|Corp|LLC|Company|Org)\b'
        ]
        orgs = []
        for pattern in org_patterns:
            matches = re.findall(pattern, text)
            orgs.extend(matches)
        return list(set(orgs))[:3]
    
    async def _llm_refine(self, text: str, intent: str, entities: Dict) -> Dict[str, Any]:
        """Use LLM to refine extraction results and score importance in a single structured call."""
        prompt = f"""Analyze this text and provide a refined extraction.

    Text: {text}

    Current intent: {intent}
    Current entities: {entities}

    Return a JSON object with exactly this structure:
    {{
        "intent": "one of: meeting, deadline, task, commitment, reminder, general",
        "summary": "1-2 sentence summary capturing the key information",
        "importance": 0.0,
        "entities": {{
            "people": [],
            "locations": [],
            "dates": [],
            "times": []
        }}
    }}

    For importance (float 0.0–1.0) consider: deadlines, appointments, action items, commitments, emotional significance, key insights, contact information."""

        try:
            response = await generate_response(
                prompt,
                response_format={"type": "json_object"},
            )
            return self._parse_llm_response(response)
        except Exception as e:
            logger.error(f"LLM refinement failed: {e}")
            return {
                "intent": intent,
                "summary": text[:100],
                "entities": entities,
                "importance": 0.5,
            }
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        try:
            import json
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                parsed = json.loads(response[start:end])
                if "importance" in parsed:
                    parsed["importance"] = min(max(float(parsed["importance"]), 0.0), 1.0)
                return parsed
        except Exception:
            pass
        return {"intent": "general", "summary": response[:100], "entities": {}, "importance": 0.5}
    
    def _calculate_importance_boost(self, intent: str, entities: Dict) -> float:
        """Calculate importance boost based on intent and entities."""
        boost = 0.0
        
        # Intent-based boost
        intent_boosts = {
            'deadline': 0.3,
            'meeting': 0.2,
            'commitment': 0.25,
            'task': 0.15,
            'reminder': 0.1,
            'general': 0.0
        }
        boost += intent_boosts.get(intent, 0.0)
        
        # Entity-based boost
        if entities.get('dates'):
            boost += 0.1
        if entities.get('people'):
            boost += 0.05
        if entities.get('locations'):
            boost += 0.05
        
        return min(boost, 0.5)  # Cap at 0.5

extraction_pipeline = ExtractionPipeline()

# ── Backward compatibility helper exports ───────────────────────────────────

def detect_correction(text: str) -> bool:
    """
    Backward-compatible correction detection API.
    Returns True if correction speech patterns are detected.
    """
    has_correction, _ = extraction_pipeline._detect_correction(text)
    return has_correction


def parse_temporal_expression(text: str) -> Optional[Dict[str, Any]]:
    """
    Backward-compatible temporal parsing API.
    Returns parsed temporal entities or None.
    """
    result = extraction_pipeline._parse_temporal_entities(text)

    if result.get("dates"):
        return result

    return None


def classify_intent(text: str) -> str:
    """
    Backward-compatible intent classification API.
    """
    return extraction_pipeline._detect_intent(text)


def extract_entities(text: str) -> Dict[str, Any]:
    """
    Backward-compatible entity extraction API.
    """
    temporal_entities = extraction_pipeline._parse_temporal_entities(text)
    return extraction_pipeline._extract_entities(text, temporal_entities)

async def summarize_with_llm(text: str) -> str:
    """
    Backward-compatible summarization helper expected by legacy tests.
    """

    result = await extraction_pipeline._llm_refine(
        text=text,
        intent="general",
        entities={},
    )

    return result.get("summary", text[:100])

async def run_extraction_pipeline(
    raw_text: str | None = None,
    text: str | None = None,
    user_id: str | None = None,
    **kwargs,
):
    """
    Backward-compatible extraction pipeline wrapper.
    """

    input_text = raw_text or text

    if input_text is None:
        raise ValueError("No input text provided")

    return await extraction_pipeline.extract(input_text)