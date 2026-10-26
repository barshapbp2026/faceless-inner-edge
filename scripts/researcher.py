"""
Researcher Agent — trending, never-repeating topic generator.
Groq primary + Gemini fallback. Fetches live Reddit signals.
Writes output/topic.json for day2_fix.py to consume.
"""
import os, json, re, random, time, requests
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANNED_FILE = os.path.join(PROJECT_ROOT, "banned_topics.txt")
TOPIC_JSON = os.path.join(PROJECT_ROOT, "output", "topic.json")

CHANNEL_DESCRIPTION = (
    "A faceless YouTube Shorts channel about Space Mysteries, Psychology, "
    "Stoicism, AI, and the strange edges of science. Audience: curious 18-40 "
    "year olds who love mind-blowing facts, cosmic scale, and existential ideas."
)

FOCUS_ANGLES = [
    "Theoretical Physics & Time Travel",
    "The Dark Forest Theory & Aliens",
    "Existential Human Psychology & Illusions",
    "Frightening AI Futures & Simulation Theory",
    "Mind-bending Mathematical Paradoxes",
    "The limits of Human Biology & Immortality",
    "Quantum Mechanics & Alternate Realities",
    "Cosmic scale, Black Holes, and the end of the Universe",
    "Neuroscience & the Mystery of Consciousness",
    "Ancient Civilisations & Lost History",
    "Cutting-edge Biotechnology & Genetic Engineering",
    "The Future of Space Colonisation",
]

REDDIT_SOURCES = [
    ("r/space", "https://www.reddit.com/r/space/hot.json?limit=15"),
    ("r/science", "https://www.reddit.com/r/science/hot.json?limit=15"),
    ("r/askscience", "https://www.reddit.com/r/askscience/hot.json?limit=15"),
    ("r/Futurology", "https://www.reddit.com/r/Futurology/hot.json?limit=15"),
]

def load_banned():
    topics = []
    if os.path.exists(BANNED_FILE):
        with open(BANNED_FILE, encoding="utf-8") as f:
            for line in f:
                t = line.strip()
                if t and not t.startswith("#"):
                    topics.append(t)
    return topics

def append_banned(topic):
    with open(BANNED_FILE, "a", encoding="utf-8") as f:
        f.write(topic.strip() + "\n")

def fetch_trending():
    headers = {"User-Agent": "FacelessResearch/1.0"}
    picked = []
    for name, url in REDDIT_SOURCES:
        try:
            r = requests.get(url, headers=headers, timeout=8)
            if r.status_code != 200:
                continue
            posts = r.json().get("data", {}).get("children", [])
            titles = [p["data"]["title"] for p in posts[:6] if p["data"].get("title")]
            if titles:
                picked.append(f"[{name}] " + " | ".join(titles[:4]))
        except Exception:
            continue
    return "\n".join(picked) if picked else "(no live signals)"

def call_groq(prompt):
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    models = ["openai/gpt-oss-20b", "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    last_err = None
    for m in models:
        try:
            r = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=m, temperature=0.9)
            return r.choices[0].message.content
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"All Groq models failed: {last_err}")

_gemini_idx = {"i": 0}

def _gemini_keys():
    keys = []
    for name in sorted(os.environ.keys()):
        if name.startswith("GEMINI_API_KEY"):
            v = os.getenv(name)
            if v and v.strip():
                keys.append(v.strip())
    return keys

def call_gemini(prompt):
    import google.generativeai as genai
    keys = _gemini_keys()
    if not keys:
        raise RuntimeError("No Gemini API keys configured")
    start = _gemini_idx["i"] % len(keys)
    last_err = None
    for offset in range(len(keys)):
        idx = (start + offset) % len(keys)
        try:
            genai.configure(api_key=keys[idx])
            model = genai.GenerativeModel("gemini-2.0-flash")
            result = model.generate_content(prompt).text
            _gemini_idx["i"] = (idx + 1) % len(keys)
            return result
        except Exception as e:
            last_err = e
            print(f"   [Gemini key #{idx+1} failed: {e}]")
            continue
    raise RuntimeError(f"All Gemini keys failed: {last_err}")

def generate(prompt):
    try:
        return call_groq(prompt)
    except Exception as e:
        print(f"   [Groq failed: {e}] -> Gemini fallback")
        return call_gemini(prompt)

def research_topic(topic_override="", focus_angle=""):
    banned = load_banned()
    banned_str = ", ".join(f'"{t}"' for t in banned) if banned else "(none)"
    trending = fetch_trending()

    if focus_angle.strip():
        chosen_angle = focus_angle.strip()
    else:
        chosen_angle = random.choice(FOCUS_ANGLES)

    if topic_override.strip():
        exact = topic_override.strip()
        print(f"   -> Mode: OVERRIDE | Topic: {exact}")
        prompt = f"""You are a YouTube Shorts strategist.

Channel: {CHANNEL_DESCRIPTION}

The user has FORCED this topic: "{exact}"
Do NOT change it. Banned: {banned_str}

Return ONLY valid JSON:
{{
  "topic": "{exact}",
  "video_title": "Punchy Shorts title under 65 chars",
  "description": "One-sentence hook",
  "tags": ["#space","#science","#shorts","#viral","#mindblown"]
}}"""
    else:
        print(f"   -> Mode: AUTO | Angle: {chosen_angle}")
        prompt = f"""You are a YouTube Shorts strategist.

Channel: {CHANNEL_DESCRIPTION}

LIVE TRENDING SIGNALS TODAY:
{trending}

Focus angle: >>> {chosen_angle} <<<

RULES:
1. Pick ONE specific mind-blowing topic within the angle.
2. MUST NOT be: {banned_str}
3. Explainable in a 60-second Short.
4. Prefer surprising, counter-intuitive, existential.
5. Cache-bust: {time.time()}

Return ONLY valid JSON:
{{
  "topic": "The specific topic in 5-12 words",
  "video_title": "Punchy Shorts title under 65 chars",
  "description": "One-sentence hook",
  "tags": ["#space","#science","#shorts","#viral","#mindblown"]
}}"""

    raw = generate(prompt)
    raw = re.sub(r"^```(?:json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        raise ValueError(f"No JSON: {raw[:400]}")
    data = json.loads(match.group())
    for f in ["topic", "video_title", "tags"]:
        if f not in data:
            raise ValueError(f"Missing field: {f}")

    os.makedirs(os.path.dirname(TOPIC_JSON), exist_ok=True)
    with open(TOPIC_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    append_banned(data["topic"])
    return data

if __name__ == "__main__":
    result = research_topic()
    print()
    print("=" * 55)
    print(f"  TOPIC:  {result['topic']}")
    print(f"  TITLE:  {result['video_title']}")
    print(f"  TAGS:   {' '.join(result['tags'])}")
    print("=" * 55)
