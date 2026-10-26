import os, asyncio, requests, subprocess, re, json
import os, asyncio, requests, subprocess, re, json, random
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
import edge_tts

load_dotenv()

GROQ_API_KEY    = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY_1")
PEXELS_API_KEY  = os.getenv("PEXELS_API_KEY")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")
COVERR_API_KEY  = os.getenv("COVERR_API_KEY")
UNSPLASH_KEY    = os.getenv("UNSPLASH_ACCESS_KEY")

# ---- Read researched topic ----
if os.path.exists("output/topic.json"):
    with open("output/topic.json") as f:
        TOPIC = json.load(f)["topic"]
else:
    TOPIC = "The Mystery of Dark Matter"
print(f"Topic: {TOPIC}")

# ---- Day-based media plan ----
DAY = datetime.now().strftime("%A")
MEDIA_MODE = {
    "Monday":    ["video", "video", "video", "video"],
    "Tuesday":   ["video", "image", "video", "image"],
    "Wednesday": ["image", "video", "image", "video"],
    "Thursday":  ["video", "video", "image", "image"],
    "Friday":    ["image", "image", "video", "video"],
    "Saturday":  ["video", "image", "image", "video"],
    "Sunday":    ["image", "image", "image", "image"],
}.get(DAY, ["video", "video", "video", "video"])
print(f"Today: {DAY} -> {MEDIA_MODE}")

# ---- LLM helper ----
def llm(prompt, temp=0.7):
    try:
        c = Groq(api_key=GROQ_API_KEY)
        r = c.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="openai/gpt-oss-20b", temperature=temp)
        return r.choices[0].message.content
    except Exception as e:
        print(f"   [Groq failed: {e}] -> Gemini fallback")
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        return genai.GenerativeModel("gemini-2.0-flash").generate_content(prompt).text

# ---- Script ----
print("Generating script...")
script = llm(
    f"Write a 60-second script for a faceless YouTube Shorts video about {TOPIC}. "
    f"Split it into exactly 4 distinct sentences. Output ONLY the sentences, nothing else.",
    temp=0.7).strip()
sentences = [s.strip() for s in re.split(r'(?<=[.!?]) +', script) if s.strip()]
print(f"Script:\n{script}\n")

# ---- Visual keywords ----
print("Extracting visual keywords...")
kw = llm(
    "For each sentence below, output 2-3 SHORT visual search keywords (2-4 words) "
    "that would find the best matching stock VIDEO or PHOTO. Think visually.\n\n"
    + "\n".join(f"{i+1}. {s}" for i, s in enumerate(sentences))
    + '\n\nReturn ONLY valid JSON array: ["kw1","kw2","kw3","kw4"]',
    temp=0.4)
kw = re.sub(r"^```(?:json)?", "", kw).strip()
kw = re.sub(r"```$", "", kw).strip()
m = re.search(r"\[[\s\S]*\]", kw)
keywords = json.loads(m.group()) if m else ["space"] * len(sentences)
while len(keywords) < len(sentences):
    keywords.append("space")
print(f"Keywords: {keywords}")

# ---- Voiceovers ----
print("Generating voiceovers...")
async def make_voices():
    for i, s in enumerate(sentences):
        await edge_tts.Communicate(s, "en-US-GuyNeural").save(f"output/voice_{i}.mp3")
asyncio.run(make_voices())

def dur(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        stdout=subprocess.PIPE, text=True)
    return float(r.stdout.strip())

# ---- Media fetchers ----
def pexels_video(q, out):
    try:
        r = requests.get(
            f"https://api.pexels.com/videos/search?query={requests.utils.quote(q)}&orientation=portrait&per_page=5",
            headers={"Authorization": PEXELS_API_KEY}, timeout=15)
        v = r.json().get("videos", [])
        if not v: return False
        pick = random.choice(v[:5])
        files = sorted(pick["video_files"], key=lambda x: x.get("width", 0), reverse=True)
        with open(out, "wb") as f:
            f.write(requests.get(files[0]["link"], timeout=40).content)
        return True
    except Exception as e:
        print(f"      [pexels_video error: {e}]")
        return False

def pixabay_video(q, out):
    try:
        r = requests.get(
            f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={requests.utils.quote(q)}&per_page=5",
            timeout=15)
        h = r.json().get("hits", [])
        if not h: return False
        pick = random.choice(h[:5])
        url = (pick["videos"].get("medium", {}).get("url") or pick["videos"]["small"]["url"])
        with open(out, "wb") as f:
            f.write(requests.get(url, timeout=40).content)
        return True
    except Exception as e:
        print(f"      [pixabay_video error: {e}]")
        return False

def coverr_video(q, out):
    try:
        r = requests.get(
            "https://api.coverr.co/videos",
            params={"query": q, "per_page": 5, "orientation": "portrait"},
            headers={"Authorization": f"Bearer {COVERR_API_KEY}"}, timeout=15)
        v = r.json().get("hits", []) or r.json().get("videos", [])
        if not v: return False
        pick = random.choice(v[:5])
        url = (pick.get("urls", {}).get("mp4_download")
               or pick.get("download_url") or pick.get("url"))
        if not url: return False
        with open(out, "wb") as f:
            f.write(requests.get(url, timeout=40).content)
        return True
    except Exception as e:
        print(f"      [coverr_video error: {e}]")
        return False

def unsplash_image(q, out):
    try:
        r = requests.get(
            "https://api.unsplash.com/search/photos",
            params={"query": q, "orientation": "portrait", "per_page": 5},
            headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"}, timeout=15)
        results = r.json().get("results", [])
        if not results: return False
        pick = random.choice(results[:5])
        with open(out, "wb") as f:
            f.write(requests.get(pick["urls"]["full"], timeout=40).content)
        return True
    except Exception as e:
        print(f"      [unsplash_image error: {e}]")
        return False

def pixabay_image(q, out):
    try:
        r = requests.get(
            f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q={requests.utils.quote(q)}&image_type=photo&orientation=vertical&per_page=5",
            timeout=15)
        h = r.json().get("hits", [])
        if not h: return False
        pick = random.choice(h[:5])
        url = pick.get("largeImageURL") or pick["webformatURL"]
        with open(out, "wb") as f:
            f.write(requests.get(url, timeout=40).content)
        return True
    except Exception as e:
        print(f"      [pixabay_image error: {e}]")
        return False

VIDEO_SOURCES = [("Pexels", pexels_video), ("Pixabay", pixabay_video), ("Coverr", coverr_video)]
IMAGE_SOURCES = [("Unsplash", unsplash_image), ("Pixabay", pixabay_image)]
random.shuffle(VIDEO_SOURCES)
random.shuffle(IMAGE_SOURCES)

# ---- Duration converters ----
def video_to_duration(src, dst, d):
    subprocess.run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", src, "-t", str(d),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1",
        "-c:v", "libx264", "-an", dst
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def image_to_kenburns(src, dst, d, direction="in"):
    frames = max(int(d * 30), 30)
    z = ("min(zoom+0.0015,1.5)" if direction == "in"
         else "if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))")
    vf = (f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
          f"zoompan=z='{z}':d={frames}:s=1080x1920:fps=30,setsar=1")
    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", src, "-vf", vf, "-t", str(d),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", dst
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ---- Build segments ----
segs = []
for i, sentence in enumerate(sentences):
    q = keywords[i]
    v = f"output/voice_{i}.mp3"
    d = dur(v)
    out = f"assets/seg_{i}.mp4"
    mode = MEDIA_MODE[i % len(MEDIA_MODE)]
    print(f"  [{i+1}/4] {mode.upper():5} | '{q}' | {d:.1f}s")

    ok = False
    if mode == "video":
        for name, fn in VIDEO_SOURCES:
            if fn(q, f"assets/raw_{i}.mp4"):
                video_to_duration(f"assets/raw_{i}.mp4", out, d)
                print(f"         src: {name}")
                ok = True
                break
        if not ok:
            for name, fn in IMAGE_SOURCES:
                if fn(q, f"assets/raw_{i}.jpg"):
                    image_to_kenburns(f"assets/raw_{i}.jpg", out, d, "in")
                    print(f"         src: {name} (fallback)")
                    ok = True
                    break
    else:
        for name, fn in IMAGE_SOURCES:
            if fn(q, f"assets/raw_{i}.jpg"):
                direction = "in" if i % 2 == 0 else "out"
                image_to_kenburns(f"assets/raw_{i}.jpg", out, d, direction)
                print(f"         src: {name}")
                ok = True
                break
        if not ok:
            for name, fn in VIDEO_SOURCES:
                if fn(q, f"assets/raw_{i}.mp4"):
                    video_to_duration(f"assets/raw_{i}.mp4", out, d)
                    print(f"         src: {name} (fallback)")
                    ok = True
                    break

    if not ok:
        print(f"         [final fallback: 'space']")
        pexels_video("space", f"assets/raw_{i}.mp4")
        video_to_duration(f"assets/raw_{i}.mp4", out, d)

    segs.append((out, v))

# ---- Combine segments with their voice ----
print("Combining segments...")
finals = []
for i, (sv, av) in enumerate(segs):
    out = f"assets/final_{i}.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-i", sv, "-i", av,
        "-c:v", "copy", "-c:a", "aac", "-shortest",
        "-pix_fmt", "yuv420p", out
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finals.append(out)

# ---- Concat final video ----
with open("assets/final_segments.txt", "w") as f:
    for s in finals:
        f.write(f"file '{os.path.abspath(s)}'\n")
subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
    "-i", "assets/final_segments.txt", "-c", "copy",
    "output/final_video.mp4"
])

# ---- Combined voice.mp3 ----
with open("assets/voices.txt", "w") as f:
    for _, voice in segs:
        f.write(f"file '{os.path.abspath(voice)}'\n")
subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
    "-i", "assets/voices.txt", "-c", "copy", "output/voice.mp3"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

print("\nDONE: output/final_video.mp4")
