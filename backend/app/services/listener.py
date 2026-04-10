import queue
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write

q = queue.Queue()


def callback(indata, frames, time_info, status):
    if status:
        print(status)
    q.put(indata.copy())


def is_silent(audio, threshold: float = 0.01) -> bool:
    return float(np.abs(audio).mean()) < threshold


def start_listener(process_audio_callback, fs: int = 16000, chunk_seconds: int = 5):
    with sd.InputStream(callback=callback, channels=1, samplerate=fs):
        print("Listening...")
        buffer = []
        start_time = time.time()

        while True:
            data = q.get()
            buffer.append(data)

            if time.time() - start_time >= chunk_seconds:
                audio_chunk = np.concatenate(buffer)
                buffer = []
                start_time = time.time()

                if is_silent(audio_chunk):
                    continue

                filename = str(Path(f"temp_{int(time.time())}.wav").resolve())
                write(filename, fs, audio_chunk)
                process_audio_callback(filename)
