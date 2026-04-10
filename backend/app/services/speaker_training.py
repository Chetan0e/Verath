import os
import pickle
from typing import Dict, List

import numpy as np

from app.config import VOICE_DB_PATH
from app.services.embedding import get_embedding

os.makedirs(os.path.dirname(VOICE_DB_PATH), exist_ok=True)

if os.path.exists(VOICE_DB_PATH):
    with open(VOICE_DB_PATH, "rb") as file:
        voice_profiles: Dict[str, np.ndarray] = pickle.load(file)
else:
    voice_profiles = {}


def save():
    """Save voice profiles to disk."""
    with open(VOICE_DB_PATH, "wb") as file:
        pickle.dump(voice_profiles, file)


def add_voice(name: str, embedding: List[float]) -> bool:
    """Add a new voice profile."""
    try:
        voice_profiles[name.lower()] = np.array(embedding, dtype="float32")
        save()
        print(f"✅ Added voice profile for '{name}'")
        return True
    except Exception as e:
        print(f"❌ Error adding voice profile: {e}")
        return False


def add_voice_from_text(name: str, text_sample: str) -> bool:
    """Add voice profile from text sample."""
    try:
        embedding = get_embedding(text_sample)
        return add_voice(name, embedding)
    except Exception as e:
        print(f"❌ Error processing voice sample: {e}")
        return False


def identify_voice(embedding: List[float], threshold: float = 0.8) -> str:
    """Identify voice from embedding."""
    if not voice_profiles:
        return "unknown"

    best_match = "unknown"
    best_score = -1.0
    query = np.array(embedding, dtype="float32")

    for name, stored_embedding in voice_profiles.items():
        # Calculate cosine similarity
        similarity = np.dot(query, stored_embedding) / (
            np.linalg.norm(query) * np.linalg.norm(stored_embedding)
        )
        
        if similarity > best_score and similarity >= threshold:
            best_score = similarity
            best_match = name

    return best_match


def get_voice_profiles() -> List[str]:
    """Get list of all trained voice names."""
    return list(voice_profiles.keys())


def remove_voice_profile(name: str) -> bool:
    """Remove a voice profile."""
    name_lower = name.lower()
    if name_lower in voice_profiles:
        del voice_profiles[name_lower]
        save()
        print(f"✅ Removed voice profile for '{name}'")
        return True
    return False


def update_voice_profile(name: str, text_sample: str) -> bool:
    """Update existing voice profile."""
    return add_voice_from_text(name, text_sample)  # Same logic, just overwrites
