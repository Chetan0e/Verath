import os
from pathlib import Path
import time
from typing import Optional

import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write

from app.config import DEFAULT_RECORD_SECONDS


def record_audio(filename: str = "temp.wav", duration: int = None, fs: int = 16000) -> str:
    """Record audio from microphone and save to file."""
    if duration is None:
        duration = DEFAULT_RECORD_SECONDS
    
    path = Path(filename).resolve()
    os.makedirs(path.parent, exist_ok=True)
    
    print(f"Recording for {duration} seconds...")
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')
    sd.wait()
    
    # Convert to int16 for better compatibility
    audio_int16 = (audio * 32767).astype('int16')
    write(str(path), fs, audio_int16)
    print(f"Saved: {path}")
    return str(path)

def is_silent(audio: np.ndarray, threshold: float = 0.01) -> bool:
    """Check if audio is mostly silent."""
    return np.abs(audio).mean() < threshold

def record_until_silence(filename: str = "temp.wav", fs: int = 16000, 
                        silence_threshold: float = 0.01, silence_duration: float = 2.0) -> str:
    """Record until silence is detected."""
    print("Recording... (silence will stop recording)")
    
    buffer = []
    silence_start = None
    
    with sd.InputStream(samplerate=fs, channels=1, dtype='float32') as stream:
        while True:
            data, overflowed = stream.read(1024)
            buffer.extend(data.flatten())
            
            if is_silent(data, silence_threshold):
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start > silence_duration:
                    break
            else:
                silence_start = None
    
    audio = np.array(buffer)
    audio_int16 = (audio * 32767).astype('int16')
    
    path = Path(filename).resolve()
    os.makedirs(path.parent, exist_ok=True)
    write(str(path), fs, audio_int16)
    print(f"Saved: {path}")
    return str(path)
