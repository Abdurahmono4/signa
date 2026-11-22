from faster_whisper import WhisperModel
from pathlib import Path

print("SignBridge UZ — O'zbekcha nutqni tanish")

audio = Path("audio/test.wav")

if not audio.exists():
    print(f"Audio topilmadi: {audio}")
    raise SystemExit(1)

print("AI modeli yuklanmoqda...")

model = WhisperModel(
    "tiny",
    device="cpu",
    compute_type="int8"
)

print("Nutq tahlil qilinmoqda...")

segments, info = model.transcribe(
    str(audio),
    language="uz",
    beam_size=5
)

print("\nAniqlangan matn:")

for segment in segments:
    print(segment.text.strip())
