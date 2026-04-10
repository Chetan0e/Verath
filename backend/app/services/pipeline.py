import os
from typing import Optional

from app.models.memory import Memory
from app.services.transcription import transcribe
from app.services.embedding import get_embedding
from app.services.memory_store import add_memory
from app.services.importance import score_importance, categorize_importance
from app.services.speaker import identify_speakers, get_primary_speaker
from app.services.privacy import is_private

def process_audio(file_path: str, user_id: str) -> Optional[Memory]:
    """Process audio file through the complete pipeline."""
    try:
        # Check privacy mode
        if is_private():
            print("🔒 Privacy mode enabled - skipping processing")
            return None
        
        # Transcribe audio
        text = transcribe(file_path)
        
        # Skip if transcription is too short
        if len(text.strip()) < 5:
            print("⏭️  Skipping - transcription too short")
            return None
        
        print(f"📝 Transcribed: {text[:100]}...")
        
        # Identify speakers
        speakers = identify_speakers(file_path)
        primary_speaker = get_primary_speaker(speakers)
        
        # Score importance
        importance = score_importance(text)
        importance_category = categorize_importance(importance)
        
        print(f"👤 Speaker: {primary_speaker}")
        print(f"⭐ Importance: {importance:.2f} ({importance_category})")
        
        # Get embedding
        embedding = get_embedding(text)
        
        # Create memory object
        memory = Memory(
            text=text,
            speaker=primary_speaker,
            importance=importance,
            tags=[importance_category],
            source="audio",
            audio_file=file_path,
            metadata={
                "speakers": speakers,
                "importance_category": importance_category
            }
        )
        
        # Store in memory
        stored = add_memory(memory, embedding, user_id)
        
        print(f"✅ Stored memory with importance {importance:.2f}")
        return stored
        
    except Exception as e:
        print(f"❌ Error processing audio: {e}")
        return None
    finally:
        # Clean up temp file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
