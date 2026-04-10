from typing import List, Dict
import torch

try:
    from pyannote.audio import Pipeline  # type: ignore
except Exception:
    Pipeline = None


_pipeline = None


def _get_pipeline():
    global _pipeline
    if Pipeline is None:
        return None
    if _pipeline is None:
        try:
            _pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization")
            if torch.cuda.is_available():
                _pipeline.to(torch.device("cuda"))
        except Exception as e:
            print(f"Warning: Could not load speaker diarization pipeline: {e}")
            _pipeline = None
    return _pipeline


def identify_speakers(audio_file: str) -> List[Dict]:
    """Identify speakers in audio file using diarization."""
    pipeline = _get_pipeline()
    if pipeline is None:
        return [{"speaker": "unknown", "start": 0.0, "end": 10.0}]

    try:
        diarization = pipeline(audio_file)
        speakers = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speakers.append({"speaker": speaker, "start": turn.start, "end": turn.end})
        return speakers or [{"speaker": "unknown", "start": 0.0, "end": 10.0}]
    except Exception as e:
        print(f"Error in speaker identification: {e}")
        return [{"speaker": "unknown", "start": 0.0, "end": 10.0}]

def get_primary_speaker(speakers: List[Dict]) -> str:
    """Get the speaker who spoke the most."""
    if not speakers:
        return "unknown"
    
    # Calculate total speaking time for each speaker
    speaker_times = {}
    for spk in speakers:
        speaker = spk["speaker"]
        duration = spk["end"] - spk["start"]
        speaker_times[speaker] = speaker_times.get(speaker, 0) + duration
    
    # Return speaker with most speaking time
    return max(speaker_times.items(), key=lambda x: x[1])[0]
