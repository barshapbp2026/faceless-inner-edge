import os, asyncio, requests, subprocess, re, json, random
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
import edge_tts

load_dotenv()

GROQ_KEYS = [os.getenv(f"GROQ_API_KEY_{i}") for i in range(1, 10) if os.getenv(f"GROQ_API_KEY_{i}")]
PEXELS_KEYS = [os.getenv(f"PEXELS_API_KEY_{i}") for i in range(1, 10) if os.getenv(f"PEXELS_API_KEY_{i}")]
GEMINI_KEYS = [os.getenv(f"GEMINI_API_KEY_{i}") for i in range(1, 10) if os.getenv(f"GEMINI_API_KEY_{i}")]
PIXABAY_KEY = os.getenv("PIXABAY_API_KEY")
UNSPLASH_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

if os.path.exists("output/topic.json"):
    with open("output/topic.json") as f: TOPIC = json.load(f)["topic"]
else: TOPIC = "The Mystery of Dark Matter"
print(f"Topic: {TOPIC}")

DAY = datetime.now().strftime("%A")
MEDIA_MODE = {
    "Monday": ["video", "video", "video", "video"],
    "Tuesday": ["video", "image", "video", "image"],
    "Wednesday": ["image", "video", "image", "video"],
    "Thursday": ["video", "video", "image", "image"],
    "Friday": ["image", "image", "video", "video"],
    "Saturday": ["video", "image", "image", "video"],
    "Sunday": ["image", "image", "image", "image"],
}.get(DAY, ["video", "video", "video", "video"])
print(f"Today: {DAY} -> {MEDIA_MODE}")

def llm(prompt, temp=0.7):
    for key in GROQ_KEYS:
        try:
            c = Groq(api_key=key)
            r = c.chat.completions.create(messages=[{"role": "user", "content": prompt}], model="openai/gpt-oss-20b", temperature=temp)
            return r.choices[0].message.content
        except Exception: continue
    import google.generativeai as genai
    for gkey in GEMINI_KEYS:
        try:
            genai.configure(api_key=gkey)
            return genai.GenerativeModel("gemini-2.0-flash").generate_content(prompt).text
        except Exception: continue
    raise Exception("All LLM keys failed.")

print("Generating Master Short script...")
master_short_prompt = f"""
You are a master viral storyteller. Write a 60-second script about {TOPIC}.
You must use EXACTLY 4 sentences following this arc:
1. Hook: A shocking question or mind-bending statement.
2. Context: The strange reality or mystery.
3. Twist: The most mind-blowing revelation.
4. Outro: A lingering philosophical question.
Output ONLY the 4 sentences.
"""
script = llm(master_short_prompt, temp=0.7).strip()
sentences = [s.strip() for s in re.split(r'(?<=[.!?]) +', script) if s.strip()]
print(f"Script:\n{script}\n")

print("Extracting visual keywords...")
kw = llm("For each sentence, output 2-3 visual keywords.\n\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(sentences)) + '\n\nReturn ONLY a JSON array: ["kw1","kw2","kw3","kw4"]', temp=0.4)
kw = re.sub(r"^```(?:json)?", "", kw).strip(); kw = re.sub(r"```$", "", kw).strip()
m = re.search(r"\[[\s\S]*\]", kw); keywords = json.loads(m.group()) if m else ["space"] * len(sentences)
while len(keywords) < len(sentences): keywords.append("space")

print("Generating voiceovers...")
async def make_voices():
    for i, s in enumerate(sentences):
        if not s.strip(): continue
        success = False
        for attempt in range(3):
            try:
                await edge_tts.Communicate(s, "en-US-GuyNeural").save(f"output/voice_{i}.mp3")
                success = True
                break
            except Exception as e:
                print(f"      [Edge-TTS Error: {e}] Retrying {attempt+1}/3...")
                await asyncio.sleep(2)
        
        if not success:
            print(f"      [Edge-TTS blocked] -> gTTS fallback for sentence {i+1}")
            from gtts import gTTS
            tts = gTTS(text=s, lang='en', slow=False)
            tts.save(f"output/voice_{i}.mp3")

asyncio.run(make_voices())

def dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path], stdout=subprocess.PIPE, text=True)
    return float(r.stdout.strip())

def pexels_video(q, out):
    for key in PEXELS_KEYS:
        try:
            r = requests.get(f"https://api.pexels.com/videos/search?query={requests.utils.quote(q)}&orientation=portrait&per_page=5", headers={"Authorization": key}, timeout=15)
            v = r.json().get("videos", [])
            if v:
                pick = random.choice(v[:5]); files = sorted(pick["video_files"], key=lambda x: x.get("width", 0), reverse=True)
                with open(out, "wb") as f: f.write(requests.get(files[0]["link"], timeout=40).content)
                return True
        except Exception: continue
    return False

def pixabay_video(q, out):
    try:
        r = requests.get(f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q={requests.utils.quote(q)}&per_page=5", timeout=15)
        h = r.json().get("hits", [])
        if h:
            pick = random.choice(h[:5]); url = (pick["videos"].get("medium", {}).get("url") or pick["videos"]["small"]["url"])
            with open(out, "wb") as f: f.write(requests.get(url, timeout=40).content)
            return True
    except Exception: return False
    return False

def unsplash_image(q, out):
    try:
        r = requests.get("https://api.unsplash.com/search/photos", params={"query": q, "orientation": "portrait", "per_page": 5}, headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"}, timeout=15)
        results = r.json().get("results", [])
        if results:
            pick = random.choice(results[:5])
            with open(out, "wb") as f: f.write(requests.get(pick["urls"]["full"], timeout=40).content)
            return True
    except Exception: return False
    return False

def video_to_duration(src, dst, d):
    subprocess.run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", src, "-t", str(d), "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1", "-c:v", "libx264", "-an", dst], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def image_to_kenburns(src, dst, d, direction="in"):
    frames = max(int(d * 30), 30)
    z = ("min(zoom+0.0015,1.5)" if direction == "in" else "if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))")
    vf = (f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='{z}':d={frames}:s=1080x1920:fps=30,setsar=1")
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", src, "-vf", vf, "-t", str(d), "-c:v", "libx264", "-pix_fmt", "yuv420p", dst], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

segs = []
for i, sentence in enumerate(sentences):
    q = keywords[i]; v = f"output/voice_{i}.mp3"; d = dur(v); out = f"assets/seg_{i}.mp4"
    mode = MEDIA_MODE[i % len(MEDIA_MODE)]
    print(f"  [{i+1}/4] {mode.upper():5} | '{q}' | {d:.1f}s")
    
    ok = False
    if mode == "video":
        if pexels_video(q, f"assets/raw_{i}.mp4"): video_to_duration(f"assets/raw_{i}.mp4", out, d); ok = True
        elif pixabay_video(q, f"assets/raw_{i}.mp4"): video_to_duration(f"assets/raw_{i}.mp4", out, d); ok = True
        elif unsplash_image(q, f"assets/raw_{i}.jpg"): image_to_kenburns(f"assets/raw_{i}.jpg", out, d, "in"); ok = True
    else:
        if unsplash_image(q, f"assets/raw_{i}.jpg"): image_to_kenburns(f"assets/raw_{i}.jpg", out, d, "in"); ok = True
        elif pexels_video(q, f"assets/raw_{i}.mp4"): video_to_duration(f"assets/raw_{i}.mp4", out, d); ok = True
        elif pixabay_video(q, f"assets/raw_{i}.mp4"): video_to_duration(f"assets/raw_{i}.mp4", out, d); ok = True

    if not ok:
        pexels_video("space", f"assets/raw_{i}.mp4")
        video_to_duration(f"assets/raw_{i}.mp4", out, d)
    segs.append((out, v))

finals = []
for i, (sv, av) in enumerate(segs):
    out = f"assets/final_{i}.mp4"
    subprocess.run(["ffmpeg", "-y", "-i", sv, "-i", av, "-c:v", "copy", "-c:a", "aac", "-shortest", "-pix_fmt", "yuv420p", out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finals.append(out)

with open("assets/final_segments.txt", "w") as f:
    for s in finals: f.write(f"file '{os.path.abspath(s)}'\n")
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "assets/final_segments.txt", "-c", "copy", "output/final_video.mp4"])

with open("assets/voices.txt", "w") as f:
    for _, voice in segs: f.write(f"file '{os.path.abspath(voice)}'\n")
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "assets/voices.txt", "-c", "copy", "output/voice.mp3"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("\nDONE: Short generated.")
