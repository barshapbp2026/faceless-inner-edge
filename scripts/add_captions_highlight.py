
from faster_whisper import WhisperModel

import os, subprocess
from faster_whisper import WhisperModel

VOICE_FILE = "output/voice.mp3"
ASS_FILE = "output/captions.ass"
VIDEO_IN = "output/final_video.mp4"
VIDEO_OUT = "output/final_video_subbed.mp4"

# === STYLE SETTINGS ===
FONT = "Arial"
FONT_SIZE = 22                     # big but fits well
MARGIN_V = 320                     # well above bottom (safe zone)
WORDS_PER_CHUNK = 4                # 3-4 words at a time (TikTok style)
NORMAL_COLOR = "&H00FFFFFF"        # white
HIGHLIGHT_COLOR = "&H0000FFFF"     # yellow (BGR)
# ======================

def ass_time(s):
    h = int(s // 3600); m = int((s % 3600) // 60); sec = int(s % 60)
    cs = int(round((s - int(s)) * 100))
    if cs == 100: sec += 1; cs = 0
    return f"{h}:{m:02d}:{sec:02d}.{cs:02d}"

print("Loading Whisper model (base, CPU)...")
model = WhisperModel("base", device="cpu", compute_type="int8")
print("Transcribing with word timestamps...")
segments, _ = model.transcribe(VOICE_FILE, word_timestamps=True)

# Flatten all words across segments
all_words = []
for seg in segments:
    for w in (seg.words or []):
        if w.word.strip():
            all_words.append({"word": w.word.strip(), "start": w.start, "end": w.end})

print(f"Found {len(all_words)} words total")

ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{FONT},{FONT_SIZE},{NORMAL_COLOR},&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,3,3,0,2,60,60,{MARGIN_V},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

lines = [ass_header]

# Build chunks: every WORDS_PER_CHUNK words, show the chunk with current word highlighted
# Each word becomes its own event so highlight moves smoothly
for i, current in enumerate(all_words):
    # Figure out which chunk this word belongs to
    chunk_start = (i // WORDS_PER_CHUNK) * WORDS_PER_CHUNK
    chunk_end = min(chunk_start + WORDS_PER_CHUNK, len(all_words))
    chunk = all_words[chunk_start:chunk_end]

    # Build display text: highlight current word
    parts = []
    for j, w in enumerate(chunk):
        idx = chunk_start + j
        if idx == i:
            parts.append(f"{{\\c{HIGHLIGHT_COLOR}}}{w['word']}{{\\c{NORMAL_COLOR}}}")
        else:
            parts.append(w["word"])
    text = " ".join(parts)

    lines.append(
        f"Dialogue: 0,{ass_time(current['start'])},{ass_time(current['end'])},Default,,0,0,0,,{text}"
    )

with open(ASS_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Wrote {len(all_words)} caption events to {ASS_FILE}")
print("Burning captions into video...")
subprocess.run([
    "ffmpeg", "-y",
    "-i", VIDEO_IN,
    "-vf", f"subtitles={ASS_FILE}",
    "-c:v", "libx264",
    "-c:a", "copy",
    "-pix_fmt", "yuv420p",
    VIDEO_OUT
])
print(f"\nDONE! Captioned video: {VIDEO_OUT}")
