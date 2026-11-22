"""Decode once for ASR; reject exact digital silence without gating quiet speech."""
import numpy as np

def decode_speech_audio(path):
    from faster_whisper.audio import decode_audio
    samples=decode_audio(str(path),sampling_rate=16000)
    if not samples.size or not np.any(samples):return None
    return samples
