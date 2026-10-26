import os, subprocess
from faster_whisper import WhisperModel

VOICE_FILE = "output/voice.mp3"
SRT_FILE = "output/captions.srt"
VIDEO_IN = "output/final_video.mp4"
VIDEO_OUT = "output/final_video_subbed.mp4"

print("Loading Whisper model (base, CPU)...")
model = WhisperModel("base", device="cpu", compute_type="int8")

print("Transcribing voiceover...")
segments, info = model.transcribe(VOICE_FILE, word_timestamps=False)
segments = list(segments)

def fmt(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

with open(SRT_FILE, "w", encoding="utf-8") as f:
    for i, seg in enumerate(segments, 1):
        text = seg.text.strip()
        if not text:
            continue
        f.write(f"{i}\n")
        f.write(f"{fmt(seg.start)} --> {fmt(seg.end)}\n")
        f.write(f"{text}\n\n")

print(f"Wrote {len(segments)} caption segments to {SRT_FILE}")

print("Burning captions into video...")
style = (
    "FontName=Arial,"
    "FontSize=12,"
    "PrimaryColour=&H00FFFFFF,"
    "OutlineColour=&H00000000,"
    "BorderStyle=3,"
    "Outline=2,"
    "Shadow=0,"
    "Bold=1,"
    "Alignment=2,"
    "MarginV=30"
)

subprocess.run([
    "ffmpeg", "-y",
    "-i", VIDEO_IN,
    "-vf", f"subtitles={SRT_FILE}:force_style='{style}'",
    "-c:v", "libx264",
    "-c:a", "copy",
    "-pix_fmt", "yuv420p",
    VIDEO_OUT
])

print(f"\nDONE! Captioned video: {VIDEO_OUT}")
