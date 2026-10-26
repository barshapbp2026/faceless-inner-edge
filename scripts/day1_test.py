import os, asyncio, requests, subprocess
from dotenv import load_dotenv

load_dotenv()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
TEXT = "This is a test of your automated faceless video pipeline. If you can see and hear this, Day 1 is complete."

async def make_voice():
    import edge_tts
    communicate = edge_tts.Communicate(TEXT, "en-US-GuyNeural")
    await communicate.save("output/voice.mp3")

asyncio.run(make_voice())

headers = {"Authorization": PEXELS_API_KEY}
url = "https://api.pexels.com/videos/search?query=space&orientation=portrait&per_page=1"
r = requests.get(url, headers=headers)
data = r.json()
video_url = data["videos"][0]["video_files"][0]["link"]

with open("assets/clip.mp4", "wb") as f:
    f.write(requests.get(video_url).content)

subprocess.run([
    "ffmpeg", "-y",
    "-stream_loop", "-1", "-i", "assets/clip.mp4",
    "-i", "output/voice.mp3",
    "-shortest",
    "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
    "-c:v", "libx264",
    "-c:a", "aac",
    "-pix_fmt", "yuv420p",
    "output/test_video.mp4"
])

print("Done: output/test_video.mp4")
