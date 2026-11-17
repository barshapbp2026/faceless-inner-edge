import os, asyncio, requests, subprocess, re, json, random, io, sys
from groq import Groq
from dotenv import load_dotenv
from urllib.parse import quote
import edge_tts
from PIL import Image, ImageDraw, ImageFont, ImageOps

load_dotenv()

GROQ_KEYS = [os.getenv(f"GROQ_API_KEY_{i}") for i in range(1, 10) if os.getenv(f"GROQ_API_KEY_{i}")]
GEMINI_KEYS = [os.getenv(f"GEMINI_API_KEY_{i}") for i in range(1, 10) if os.getenv(f"GEMINI_API_KEY_{i}")]
PEXELS_KEYS = [os.getenv(f"PEXELS_API_KEY_{i}") for i in range(1, 10) if os.getenv(f"PEXELS_API_KEY_{i}")]
PIXABAY_KEY = os.getenv("PIXABAY_API_KEY")
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
            text = r.choices[0].message.content
            if text and len(text.strip()) > 10: return text
        except Exception: continue
    import google.generativeai as genai
    for gkey in GEMINI_KEYS:
        try:
            genai.configure(api_key=gkey)
            text = genai.GenerativeModel("gemini-2.0-flash").generate_content(prompt).text
            if text and len(text.strip()) > 10: return text
        except Exception: continue
    return ""

def clean_text(text):
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'_+', '', text)
    text = re.sub(r'#+', '', text)
    text = re.sub(r'(?i)\b(?:Hook|Context|Escalation|Twist|Outro|Narrator|Scene|Narration|Speaker|Host)\s*:\s*', '', text)
    text = re.sub(r'\b\d+\.\s*', '', text)
    text = text.replace('"', '').replace("'", "")
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

print("Generating 5-minute script...")
master_long_prompt = f"""
You are a master documentary filmmaker. Write a detailed, 700-word script about {TOPIC}.
Follow this arc: Hook, Context, Escalation, Twist, Outro.
CRITICAL RULE: Output ONLY the raw script text. Do NOT include the words Hook, Context, Escalation, Twist, or Outro. Do NOT use any markdown formatting, asterisks, or numbers.
"""
script = llm(master_long_prompt, temp=0.7).strip()
script = clean_text(script)
sentences = [s.strip() for s in re.split(r'(?<=[.!?]) +', script) if s.strip()]

if len(sentences) < 10:
    sentences = [
        f"What if everything you thought you knew about {TOPIC} was wrong?",
        "For centuries, humanity has looked at the stars and wondered about the unknown.",
        "But recently, scientists have uncovered something that defies all explanation.",
        "The data doesn't just challenge our understanding of physics, it shatters it.",
        "It suggests that reality is far stranger and more complex than we ever imagined.",
        "We built our civilization on the idea that the universe follows strict rules.",
        "But at the quantum level, those rules break down entirely.",
        "Particles exist in multiple states at once, until the moment they are observed.",
        "This means that consciousness itself might be the key to reality.",
        "Without a mind to observe it, does the universe even exist?",
        "The truth is still out there, waiting to be discovered."
    ]
    while len(sentences) < 20: sentences.extend(sentences)

print(f"Script generated ({len(sentences)} sentences).")

print("Director AI planning timeline...")
director_prompt = f"""
You are a master video director. For each of the following sentences, assign a media type ('ai_image', 'stock_video', or 'unsplash') and a unique, highly descriptive visual prompt (4-8 words). 
Do NOT use generic words like 'space' or 'galaxy'. Be specific.
CRITICAL RULE: You must generate a UNIQUE visual prompt for every single sentence. Do NOT repeat the same prompt twice.
Return ONLY a valid JSON array: [{{"media": "ai_image", "prompt": "..."}}]
Sentences: {json.dumps(sentences)}
"""
director_raw = llm(director_prompt, temp=0.6)
director_raw = re.sub(r"^```(?:json)?", "", director_raw).strip(); director_raw = re.sub(r"```$", "", director_raw).strip()
m = re.search(r"\[[\s\S]*\]", director_raw)

if m:
    timeline = json.loads(m.group())
else:
    fallback_prompts = ["glowing nebula", "distant galaxy", "black hole accretion", "quantum particles", "ancient star map", "deep space telescope", "cosmic void", "supernova explosion", "astronaut floating", "dark matter simulation"]
    timeline = [{"media": random.choice(["ai_image", "unsplash", "stock_video"]), "prompt": random.choice(fallback_prompts)} for _ in sentences]

def generate_thumbnail():
    print("Generating Catchy Thumbnail...")
    text_prompt = f"Generate JSON with 'header' (2-4 ALL CAPS clickbait words) and 'subheader' (4-7 words) for a video about {TOPIC}. Return ONLY JSON."
    text_raw = llm(text_prompt, temp=0.9)
    text_raw = re.sub(r"^```(?:json)?", "", text_raw).strip(); text_raw = re.sub(r"```$", "", text_raw).strip()
    tm = re.search(r"\{[\s\S]*\}", text_raw)
    try:
        text_data = json.loads(tm.group())
        header = text_data.get("header", "MIND BLOWN").upper()
        subheader = text_data.get("subheader", "You won't believe this...")
    except: header, subheader = "MIND BLOWN", "You won't believe this..."
    
    bg_img = None
    url = f"https://image.pollinations.ai/prompt/{quote(TOPIC + ', cinematic, dramatic lighting, 8k')}?width=1280&height=720&nologo=true&token={POLLINATIONS_KEY}&seed={random.randint(1,999999)}"
    try:
        r = requests.get(url, timeout=45)
        if r.status_code == 200: bg_img = Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception: pass
        
    if bg_img is None:
        try:
            r = requests.get("https://api.unsplash.com/search/photos", params={"query": TOPIC, "orientation": "landscape", "per_page": 1}, headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"}, timeout=15)
            if r.json().get("results"):
                r_img = requests.get(r.json()["results"][0]["urls"]["regular"], timeout=15)
                bg_img = Image.open(io.BytesIO(r_img.content)).convert("RGB")
        except Exception: pass

    if bg_img is None: bg_img = Image.new("RGB", (1280, 720), color="black")
    
    bg_img = ImageOps.fit(bg_img, (1280, 720), Image.Resampling.LANCZOS)
    
    overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    for x in range(900):
        alpha = int(240 * (1 - (x / 900)))
        for y in range(720): overlay.putpixel((x, y), (0, 0, 0, alpha))
    bg_img = Image.alpha_composite(bg_img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(bg_img)

    try:
        f_h = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 130)
        f_s = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 50)
    except IOError: f_h, f_s = ImageFont.load_default(), ImageFont.load_default()

    # Randomize text position slightly so it's never identical
    x_pos = 50
    y_pos = random.choice([350, 380, 410]) 
    
    draw.text((x_pos+5, y_pos+5), header, font=f_h, fill="black", stroke_width=10, stroke_fill="black")
    draw.text((x_pos, y_pos), header, font=f_h, fill="yellow", stroke_width=10, stroke_fill="black")
    
    sub_y = y_pos + 160
    draw.text((x_pos+3, sub_y+3), subheader, font=f_s, fill="black", stroke_width=6, stroke_fill="black")
    draw.text((x_pos, sub_y), subheader, font=f_s, fill="white", stroke_width=6, stroke_fill="black")
    
    bg_img.save("output/thumbnail.jpg", quality=95)
    print("  ✅ Catchy Thumbnail generated!")

generate_thumbnail()

async def make_voices():
    for i, s in enumerate(sentences):
        if not s.strip(): continue
        success = False
        for attempt in range(3):
            try:
                await edge_tts.Communicate(s, "en-US-ChristopherNeural").save(f"output/long_voice_{i}.mp3")
                success = True; break
            except Exception: await asyncio.sleep(2)
        if not success:
            from gtts import gTTS
            gTTS(text=s, lang='en', slow=False).save(f"output/long_voice_{i}.mp3")

print("Generating voiceovers...")
asyncio.run(make_voices())

def dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path], stdout=subprocess.PIPE, text=True)
    return float(r.stdout.strip())

def fetch_ai_image(prompt, out):
    # Guarantee uniqueness with a random seed
    seed = random.randint(1, 999999)
    url = f"https://image.pollinations.ai/prompt/{quote(prompt + ', 8k, cinematic')}?width=1920&height=1080&nologo=true&token={POLLINATIONS_KEY}&seed={seed}"
    try:
        r = requests.get(url, timeout=60)
        if r.status_code == 200:
            with open(out, "wb") as f: f.write(r.content)
            return True
    except Exception: return False

def fetch_stock_video(q, out):
    for key in PEXELS_KEYS:
        try:
            r = requests.get(f"https://api.pexels.com/videos/search?query={quote(q)}&orientation=landscape&per_page=10", headers={"Authorization": key}, timeout=15)
            v = r.json().get("videos", [])
            if v:
                chosen = random.choice(v[:10])
                with open(out, "wb") as f: f.write(requests.get(sorted(chosen["video_files"], key=lambda x: x.get("width", 0), reverse=True)[0]["link"], timeout=40).content)
                return True
        except Exception: continue
    
    try:
        r = requests.get(f"https://pixabay.com/api/videos/?key={PIXABAY_KEY}&q={quote(q)}&per_page=10", timeout=15)
        h = r.json().get("hits", [])
        if h:
            chosen = random.choice(h[:10])
            url = chosen["videos"].get("medium", {}).get("url") or chosen["videos"]["small"]["url"]
            with open(out, "wb") as f: f.write(requests.get(url, timeout=40).content)
            return True
    except Exception: return False
    return False

def fetch_unsplash_image(q, out):
    try:
        r = requests.get("https://api.unsplash.com/search/photos", params={"query": q, "orientation": "landscape", "per_page": 10}, headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"}, timeout=15)
        results = r.json().get("results", [])
        if results:
            chosen = random.choice(results[:10])
            with open(out, "wb") as f: f.write(requests.get(chosen["urls"]["full"], timeout=40).content)
            return True
    except Exception: return False
    return False

CINEMATIC_FILTER = "eq=contrast=1.1:saturation=1.2,vignette=PI/5,drawbox=y=0:color=black@1.0:t=140,drawbox=y=ih-140:color=black@1.0:t=140"

def process_img(img, out, d, dir="in"):
    frames = max(int(d * 30), 30)
    z = "min(zoom+0.0015,1.5)" if dir == "in" else "if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))"
    vf = f"scale=1920:1080,zoompan=z='{z}':d={frames}:s=1920x1080:fps=30,setsar=1,{CINEMATIC_FILTER},fade=t=in:st=0:d=1,fade=t=out:st={d-1}:d=1"
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", img, "-vf", vf, "-t", str(d), "-c:v", "libx264", "-pix_fmt", "yuv420p", out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def process_vid(src, out, d):
    vf = f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,setsar=1,{CINEMATIC_FILTER},fade=t=in:st=0:d=1,fade=t=out:st={d-1}:d=1"
    subprocess.run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", src, "-t", str(d), "-vf", vf, "-c:v", "libx264", "-an", out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

segs = []
for i, sentence in enumerate(sentences):
    scene = timeline[i] if i < len(timeline) else {"media": "stock_video", "prompt": "space"}
    media = scene.get("media", "stock_video")
    prompt = scene.get("prompt", "space")
    if i % 3 == 0: media = "ai_image"
    elif i % 3 == 1: media = "unsplash"
    
    d = dur(f"output/long_voice_{i}.mp3")
    out = f"assets/long_seg_{i}.mp4"
    raw_v = f"assets/raw_{i}.mp4"
    raw_i = f"assets/raw_{i}.jpg"
    
    success = False
    if media == "ai_image" and fetch_ai_image(prompt, raw_i): process_img(raw_i, out, d, "in"); success = True
    elif media == "unsplash" and fetch_unsplash_image(prompt, raw_i): process_img(raw_i, out, d, "out"); success = True
    elif media == "stock_video" and fetch_stock_video(prompt, raw_v): process_vid(raw_v, out, d); success = True

    if not success:
        fallback_query = random.choice(["galaxy", "nebula", "cosmos", "universe", "stars", "astronomy"])
        if fetch_ai_image(prompt, raw_i): process_img(raw_i, out, d, "in"); success = True
        elif fetch_unsplash_image(prompt, raw_i): process_img(raw_i, out, d, "out"); success = True
        elif fetch_stock_video(fallback_query, raw_v): process_vid(raw_v, out, d); success = True

    if not success:
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s=1920x1080:d={d}", "-c:v", "libx264", "-t", str(d), out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    segs.append((out, f"output/long_voice_{i}.mp3"))

print("Assembling final video...")
finals = []
for i, (sv, av) in enumerate(segs):
    out = f"assets/long_final_{i}.mp4"
    subprocess.run(["ffmpeg", "-y", "-i", sv, "-i", av, "-c:v", "copy", "-c:a", "aac", "-shortest", "-pix_fmt", "yuv420p", out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finals.append(out)

if not finals: sys.exit(1)

with open("assets/long_segments.txt", "w") as f:
    for s in finals: f.write(f"file '{os.path.abspath(s)}'\n")
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "assets/long_segments.txt", "-c", "copy", "output/video_only.mp4"], check=True)

with open("assets/long_voices.txt", "w") as f:
    for _, voice in segs: f.write(f"file '{os.path.abspath(voice)}'\n")
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "assets/long_voices.txt", "-c", "copy", "output/voice.mp3"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# --- RANDOMIZED MOTION GRAPHICS TITLE CARD ---
safe_title = TOPIC.replace("'", "").replace(":", "").replace(",", "")
# Pick a random title color and random Y position for uniqueness
title_color = random.choice(["white", "yellow", "cyan", "orange"])
title_y = random.choice([100, 200, 300])
# Randomize the fade animation slightly
title_filter = f"drawtext=text='{safe_title}':fontcolor={title_color}:fontsize=60:x=(w-text_w)/2:y={title_y}:alpha='if(lt(t,1),t,if(lt(t,4),1,if(lt(t,5),(5-t),0)))'"

subprocess.run(["ffmpeg", "-y", "-i", "output/video_only.mp4", "-i", "output/voice.mp3", "-vf", title_filter, "-c:v", "libx264", "-c:a", "aac", "-shortest", "-pix_fmt", "yuv420p", "output/final_video.mp4"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("\nDONE: Long video generated successfully.")
