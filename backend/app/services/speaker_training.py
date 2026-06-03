import os
import json
from typing import Dict, List

import numpy as np

from app.config import settings
from app.services.gemini_embedding import get_embedding

os.makedirs(os.path.dirname(settings.voice_db_path), exist_ok=True)

# Replace pickle with JSON for security
VOICE_DB_JSON = settings.voice_db_path.replace('.pkl', '.json')

if os.path.exists(VOICE_DB_JSON):
    with open(VOICE_DB_JSON, "r") as file:
        data = json.load(file)
        voice_profiles: Dict[str, Dict[str, List[float]]] = {
    k: v for k, v in data.items()
}
else:
    voice_profiles: Dict[str, Dict[str, List[float]]] = {}


def save():
    """Save voice profiles to disk using JSON instead of pickle."""
    with open(VOICE_DB_JSON, "w") as file:
        json.dump(voice_profiles, file)


def add_voice(
    user_id: str,
    name: str,
    embedding: List[float]
) -> bool:
    """Add a new voice profile."""
    try:
        voice_profiles.setdefault(user_id, {})
        voice_profiles[user_id][name.lower()] = embedding
        save()
        print(f"✅ Added voice profile for '{name}'")
        return True
    except Exception as e:
        print(f"❌ Error adding voice profile: {e}")
        return False


def add_voice_from_text(
    user_id: str,
    name: str,
    text_sample: str
) -> bool:
    """Add voice profile from text sample."""
    try:
        embedding = get_embedding(text_sample)
        return add_voice(user_id, name, embedding)
    except Exception as e:
        print(f"❌ Error processing voice sample: {e}")
        return False


def identify_voice(
    user_id: str,
    embedding: List[float],
    threshold: float = 0.8
) -> str:
    """Identify voice from embedding."""

    user_profiles = voice_profiles.get(user_id, {})

    if not user_profiles:
        return "unknown"

    best_match = "unknown"
    best_score = -1.0
    query = np.array(embedding, dtype="float32")

    for name, stored_embedding in user_profiles.items():
        # Convert stored list back to numpy array
        stored = np.array(stored_embedding, dtype="float32")
        # Calculate cosine similarity
        similarity = np.dot(query, stored) / (
            np.linalg.norm(query) * np.linalg.norm(stored)
        )

        if similarity > best_score and similarity >= threshold:
            best_score = similarity
            best_match = name

    return best_match


def get_voice_profiles(user_id: str) -> List[str]:
    """Get list of all trained voice names."""
    return list(voice_profiles.get(user_id, {}).keys())

def remove_voice_profile(user_id: str, name: str) -> bool:
    """Remove a voice profile."""
    name_lower = name.lower()

    if (
        user_id in voice_profiles
        and name_lower in voice_profiles[user_id]
    ):
        del voice_profiles[user_id][name_lower]
        save()
        print(f"✅ Removed voice profile for '{name}'")
        return True

    return False

def update_voice_profile(
    user_id: str,
    name: str,
    text_sample: str
) -> bool:
    """Update existing voice profile."""
    return add_voice_from_text(
        user_id,
        name,
        text_sample
    )