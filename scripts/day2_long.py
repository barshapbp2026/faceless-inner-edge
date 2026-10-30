import os, asyncio, requests, subprocess, re, json, random, io
from groq import Groq
from dotenv import load_dotenv
from urllib.parse import quote
import edge_tts
from PIL import Image, ImageDraw, ImageFont, ImageOps

load_dotenv()

# --- LOAD KEYS ---
GROQ_KEYS = [os.getenv(f"GROQ_API_KEY_{i}") for i in range(1, 10) if os.getenv(f"GROQ_API_KEY_{i}")]
GEMINI_KEYS = [os.getenv(f"GEMINI_API_KEY_{i}") for i in range(1, 10) if os.getenv(f"GEMINI_API_KEY_{i}")]
PEXELS_KEYS = [os.getenv(f"PEXELS_API_KEY_{i}") for i in range(1, 10) if os.getenv(f"PEXELS_API_KEY_{i}")]
PIXABAY_KEY = os.getenv("PIXABAY_API_KEY")
COVERR_KEY = os.getenv("COVERR_API_KEY")
UNSPLASH_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
POLLINATIONS_KEY = os.getenv("POLLINATIONS_API_KEY")

if os.path.exists("output/topic.json"):
    with open("output/topic.json") as f: TOPIC = json.load(f)["topic"]
else: TOPIC = "The Mystery of Dark Matter"
print(f"Topic: {TOPIC}")

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

# 1. Generate LONG Script (35 sentences for ~5 minutes)
print("Generating 5-minute script (35 sentences)...")
master_long_prompt = f"""
You are a master documentary filmmaker. Write a 5-minute script about {TOPIC}.
You must use EXACTLY 35 sentences following this arc:
- Sentences 1-3: The Hook (Shocking question, setting the scene).
- Sentences 4-15: The Context (Deep dive into the history and strange reality).
- Sentences 16-25: The Escalation (Building tension, uncovering weird facts).
- Sentences 26-32: The Twist (The mind-blowing revelation).
- Sentences 33-35: The Outro (Philosophical implication).
Output ONLY the 35 sentences. Do not number them.
"""
script = llm(master_long_prompt, temp=0.7).strip()
sentences = [s.strip() for s in re.split(r'(?<=[.!?]) +', script) if s.strip()]
print(f"Script generated ({len(sentences)} sentences).")

# 2. Director AI
print("Director AI planning timeline...")
director_prompt = f"""
You are a video director. For these sentences, assign a media type and a unique search prompt.
Choose from: 'ai_video', 'ai_image', 'stock_video', 'coverr', 'unsplash'.
Use 'ai_video' for at most 3 scenes. Use a diverse mix for the rest.
Sentences: {json.dumps(sentences)}
Return ONLY a JSON array: [{{"media": "ai_video", "prompt": "..."}}]
"""
director_raw = llm(director_prompt, temp=0.6)
director_raw = re.sub(r"^```(?:json)?", "", director_raw).strip(); director_raw = re.sub(r"```$", "", director_raw).strip()
m = re.search(r"\[[\s\S]*\]", director_raw); timeline = json.loads(m.group()) if m else [{"media": "stock_video", "prompt": "space"} for _ in sentences]

# --- NEW THUMBNAIL GENERATOR (Exactly like your examples) ---
def generate_thumbnail():
    print("Generating Cinematic Thumbnail...")
    
    # 1. Get Text from AI
    text_prompt = f"""
    Generate a JSON object with two keys for a YouTube thumbnail about {TOPIC}.
    "header": A 2-4 word ALL CAPS question (e.g., "WHY BLUE?", "WHY SO POWERFUL?").
    "subheader": A 4-7 word curious statement ending in "..." (e.g., "It hides a dark secret...", "You'll die in a minute...").
    Return ONLY the JSON.
    """
    text_raw = llm(text_prompt, temp=0.8)
    text_raw = re.sub(r"^```(?:json)?", "", text_raw).strip(); text_raw = re.sub(r"```$", "", text_raw).strip()
    tm = re.search(r"\{[\s\S]*\}", text_raw)
    try:
        text_data = json.loads(tm.group())
        header = text_data.get("header", "MIND BLOWN").upper()
        subheader = text_data.get("subheader", "You won't believe this...")
    except:
        header, subheader = "MIND BLOWN", "You won't believe this..."

    print(f"  Header: {header} | Sub: {subheader}")

    # 2. Get Background Image (Alternate AI and Unsplash)
    bg_img = None
    use_ai = random.choice([True, False])
    
    if use_ai:
        print("  Fetching AI Background...")
        url = f"https://image.pollinations.ai/prompt/{quote(TOPIC + ', cinematic, dramatic lighting, 8k')}?width=1280&height=720&nologo=true&token={POLLINATIONS_KEY}"
        try:
            r = requests.get(url, timeout=45)
            if r.status_code == 200: bg_img = Image.open(io.BytesIO(r.content)).convert("RGB")
        except Exception: pass
        
    if bg_img is None:
        print("  Fetching Unsplash Background...")
        try:
            r = requests.get("https://api.unsplash.com/search/photos", params={"query": TOPIC, "orientation": "landscape", "per_page": 1}, headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"}, timeout=15)
            if r.json().get("results"):
                img_url = r.json()["results"][0]["urls"]["regular"]
                r_img = requests.get(img_url, timeout=15)
                bg_img = Image.open(io.BytesIO(r_img.content)).convert("RGB")
        except Exception: pass

    if bg_img is None:
        bg_img = Image.new("RGB", (1280, 720), color="black")

    # 3. Resize and Create Canvas
    bg_img = ImageOps.fit(bg_img, (1280, 720), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(bg_img)

    # 4. Add slight dark gradient to left side for text readability
    overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    for x in range(700):
        alpha = int(180 * (1 - (x / 700)))  # Fades from 180 to 0
        for y in range(720):
            overlay.putpixel((x, y), (0, 0, 0, alpha))
    bg_img = Image.alpha_composite(bg_img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(bg_img)

    # 5. Load Fonts
    try:
        # Need a bold, impact-style font
        font_header = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 140)
        font_sub = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 50)
    except IOError:
        font_header = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # 6. Draw Header (Yellow, large, left-aligned)
    x_pos, y_pos = 50, 250
    draw.text((x_pos, y_pos), header, font=font_header, fill="yellow", stroke_width=10, stroke_fill="black")

    # 7. Draw Subheader (White, smaller, below header)
    sub_y = y_pos + 170
    draw.text((x_pos, sub_y), subheader, font=font_sub, fill="white", stroke_width=6, stroke_fill="black")

    # 8. Save
    bg_img.save("output/thumbnail.jpg", quality=95)
    print("  ✅ Cinematic Thumbnail generated!")

generate_thumbnail()

# --- VOICEOVERS ---
async def make_voices():
    for i, s in enumerate(sentences):
        if not s.strip(): continue
        success = False
        for attempt in range(3):
            try:
                await edge_tts.Communicate(s, "en-US-GuyNeural").save(f"output/long_voice_{i}.mp3")
                success = True; break
            except Exception: await asyncio.sleep(2)
        if not success:
            print(f"      [Edge-TTS blocked] -> gTTS fallback for sentence {i+1}")
            from gtts import gTTS
            gTTS(text=s, lang='en', slow=False).save(f"output/long_voice_{i}.mp3")

print("Generating voiceovers...")
asyncio.run(make_voices())

def dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path], stdout=subprocess.PIPE, text=True)
    return float(r.stdout.strip())

# --- FETCHERS ---
def fetch_ai_image(prompt, out):
    url = f"https://image.pollinations.ai/prompt/{quote(prompt + ', 8k, cinematic')}?width=1920&height=1080&nologo=true&token={POLLINATIONS_KEY}"
    try:
        r = requests.get(url, timeout=60)
        if r.status_code == 200:
            with open(out, "wb") as f: f.write(r.content)
            return True
    except Exception: return False

def fetch_ai_video(prompt, out):
    url = f"https://video.pollinations.ai/prompt/{quote(prompt + ', 8k')}?nologo=true"
    try:
        r = requests.get(url, timeout=180)
        if r.status_code == 200:
            with open(out, "wb") as f: f.write(r.content)
            return True
    except Exception: return False

def fetch_stock_video(q, out):
    for key in PEXELS_KEYS:
        try:
            r = requests.get(f"https://api.pexels.com/videos/search?query={quote(q)}&orientation=landscape&per_page=5", headers={"Authorization": key}, timeout=15)
            v = r.json().get("videos", [])
            if v:
                with open(out, "wb") as f: f.write(requests.get(sorted(v[0]["video_files"], key=lambda x: x.get("width", 0), reverse=True)[0]["link"], timeout=40).content)
                return True
        except Exception: continue
    try:
        r = requests.get(f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q={quote(q)}&per_page=5", timeout=15)
        h = r.json().get("hits", [])
        if h:
            with open(out, "wb") as f: f.write(requests.get(h[0]["videos"].get("medium", {}).get("url") or h[0]["videos"]["small"]["url"], timeout=40).content)
            return True
    except Exception: return False
    return False

def fetch_unsplash_image(q, out):
    try:
        r = requests.get("https://api.unsplash.com/search/photos", params={"query": q, "orientation": "landscape", "per_page": 5}, headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"}, timeout=15)
        if r.json().get("results"):
            with open(out, "wb") as f: f.write(requests.get(r.json()["results"][0]["urls"]["full"], timeout=40).content)
            return True
    except Exception: return False
    return False

def fetch_coverr(q, out):
    try:
        r = requests.get("https://api.coverr.co/videos", params={"query": q, "per_page": 5, "orientation": "landscape"}, headers={"Authorization": f"Bearer {COVERR_KEY}"}, timeout=15)
        v = r.json().get("hits", []) or r.json().get("videos", [])
        if v:
            url = v[0].get("urls", {}).get("mp4_download") or v[0].get("url")
            if url:
                with open(out, "wb") as f: f.write(requests.get(url, timeout=40).content)
                return True
    except Exception: return False
    return False

# --- PROCESSING ---
CINEMATIC_FILTER = "eq=contrast=1.1:saturation=1.2,vignette=PI/5,drawbox=y=0:color=black@1.0:t=140,drawbox=y=ih-140:color=black@1.0:t=140"

def process_img(img, out, d, dir="in"):
    frames = max(int(d * 30), 30)
    z = "min(zoom+0.0015,1.5)" if dir == "in" else "if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))"
    vf = f"scale=1920:1080,zoompan=z='{z}':d={frames}:s=1920x1080:fps=30,setsar=1,{CINEMATIC_FILTER},fade=t=in:st=0:d=1,fade=t=out:st={d-1}:d=1"
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", img, "-vf", vf, "-t", str(d), "-c:v", "libx264", "-pix_fmt", "yuv420p", out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def process_vid(src, out, d):
    vf = f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,setsar=1,{CINEMATIC_FILTER},fade=t=in:st=0:d=1,fade=t=out:st={d-1}:d=1"
    subprocess.run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", src, "-t", str(d), "-vf", vf, "-c:v", "libx264", "-an", out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# --- BUILD SCENES (With Image Rotation) ---
segs = []
for i, sentence in enumerate(sentences):
    scene = timeline[i] if i < len(timeline) else {"media": "stock_video", "prompt": "space"}
    media = scene.get("media", "stock_video")
    prompt = scene.get("prompt", "space")
    
    # Force rotation if director gets lazy
    if i % 3 == 0: media = "ai_image"
    elif i % 3 == 1: media = "unsplash"
    
    d = dur(f"output/long_voice_{i}.mp3")
    out = f"assets/long_seg_{i}.mp4"
    raw_v = f"assets/raw_{i}.mp4"
    raw_i = f"assets/raw_{i}.jpg"
    
    print(f"  [{i+1}/{len(sentences)}] Assigned: {media.upper()} | '{prompt}' | {d:.1f}s")
    success = False

    if media == "ai_video" and fetch_ai_video(prompt, raw_v): process_vid(raw_v, out, d); success = True
    elif media == "ai_image" and fetch_ai_image(prompt, raw_i): process_img(raw_i, out, d, "in" if i%2==0 else "out"); success = True
    elif media == "unsplash" and fetch_unsplash_image(prompt, raw_i): process_img(raw_i, out, d, "out" if i%2==0 else "in"); success = True
    elif media == "coverr" and fetch_coverr(prompt, raw_v): process_vid(raw_v, out, d); success = True
    elif media == "stock_video" and fetch_stock_video(prompt, raw_v): process_vid(raw_v, out, d); success = True

    # Fallbacks
    if not success:
        print(f"      [Warning] {media} failed. Starting fallback chain...")
        if fetch_ai_image(prompt, raw_i): process_img(raw_i, out, d, "in"); success = True; print("      -> Rescued by AI Image")
        elif fetch_unsplash_image(prompt, raw_i): process_img(raw_i, out, d, "out"); success = True; print("      -> Rescued by Unsplash")
        elif fetch_stock_video(prompt, raw_v): process_vid(raw_v, out, d); success = True; print("      -> Rescued by Pexels/Pixabay")

    if not success:
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s=1920x1080:d={d}", "-c:v", "libx264", "-t", str(d), out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    segs.append((out, f"output/long_voice_{i}.mp3"))

# --- FINAL ASSEMBLY ---
print("Assembling final video...")
finals = []
for i, (sv, av) in enumerate(segs):
    out = f"assets/long_final_{i}.mp4"
    subprocess.run(["ffmpeg", "-y", "-i", sv, "-i", av, "-c:v", "copy", "-c:a", "aac", "-shortest", "-pix_fmt", "yuv420p", out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finals.append(out)

with open("assets/long_segments.txt", "w") as f:
    for s in finals: f.write(f"file '{os.path.abspath(s)}'\n")
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "assets/long_segments.txt", "-c", "copy", "output/video_only.mp4"])

with open("assets/long_voices.txt", "w") as f:
    for _, voice in segs: f.write(f"file '{os.path.abspath(voice)}'\n")
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "assets/long_voices.txt", "-c", "copy", "output/voice.mp3"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# --- MOTION GRAPHICS ---
safe_title = TOPIC.replace("'", "").replace(":", "").replace(",", "")
title_filter = f"drawtext=text='{safe_title}':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=(h-text_h)/2+100:alpha='if(lt(t,1),t,if(lt(t,4),1,if(lt(t,5),(5-t),0)))'"

subprocess.run([
    "ffmpeg", "-y", "-i", "output/video_only.mp4", "-i", "output/voice.mp3",
    "-vf", title_filter, "-c:v", "libx264", "-c:a", "aac", "-shortest", "-pix_fmt", "yuv420p",
    "output/final_video.mp4"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

print("\nDONE: Long video generated successfully.")

