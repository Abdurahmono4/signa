import wave
import numpy as np
from backend.app.speech_audio import decode_speech_audio

def write_wave(path,samples):
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(samples.astype('<i2').tobytes())

def test_actual_silent_wav_is_rejected_before_whisper(tmp_path):
    path=tmp_path/'silence.wav';write_wave(path,np.zeros(16000))
    assert decode_speech_audio(path) is None

def test_faint_nonzero_audio_is_preserved_without_vad_gating(tmp_path):
    path=tmp_path/'faint.wav';samples=np.zeros(16000);samples[8000]=1
    write_wave(path,samples);decoded=decode_speech_audio(path)
    assert decoded is not None and len(decoded)==16000
    assert np.count_nonzero(decoded)==1 and decoded[8000]>0
