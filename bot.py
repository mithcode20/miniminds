"""MiniMinds auto-bot: trend research -> script -> voice -> video -> Instagram Reel -> stats. All free tools."""
import os, json, time, random, asyncio, subprocess, requests, feedparser
from datetime import datetime, timezone
from pathlib import Path
import edge_tts
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (VideoFileClip, ImageClip, AudioFileClip, ColorClip,
                            CompositeVideoClip, concatenate_videoclips, vfx)

E = os.environ
GEMINI, PEXELS, TOKEN, IG_ID = E["GEMINI_KEY"], E["PEXELS_KEY"], E["IG_TOKEN"], E["IG_USER_ID"]
REPO, BRANCH = E["GITHUB_REPOSITORY"], E.get("GITHUB_REF_NAME", "main")
G = "https://graph.instagram.com/v21.0"
W, H = 1080, 1920
Path("work").mkdir(exist_ok=True); Path("videos").mkdir(exist_ok=True); Path("docs").mkdir(exist_ok=True)
HIST = Path("docs/history.json")
history = json.loads(HIST.read_text()) if HIST.exists() else []

def sh(*a): subprocess.run(a, check=True)
def push(msg):
    sh("git", "config", "user.name", "minibot"); sh("git", "config", "user.email", "bot@users.noreply.github.com")
    sh("git", "add", "-A"); subprocess.run(["git", "commit", "-m", msg])
    sh("git", "pull", "--rebase", "-q"); sh("git", "push")

# 1) TREND RESEARCH (free sources) -------------------------------------------
def trends():
    out = []
    for u in ["https://trends.google.com/trending/rss?geo=US", "https://trends.google.com/trending/rss?geo=IN",
              "https://www.reddit.com/r/todayilearned/top/.rss?t=day", "https://www.reddit.com/r/science/top/.rss?t=day",
              "https://www.reddit.com/r/Futurology/top/.rss?t=day"]:
        try: out += [e.title for e in feedparser.parse(u).entries[:8]]
        except Exception: pass
    return out

# 2) SCRIPT via Gemini free tier ---------------------------------------------
def make_script():
    prompt = f"""You run the Instagram Reels channel "MiniMinds" for kids (8+) AND adults.
Pick ONE fresh, unique idea mixing science / story / fun fact / new idea / learning, inspired by today's trends:
{trends()}
Do NOT repeat these earlier topics: {history[-40:]}.
Safe, positive, accurate, no brands, no politics. 30-40 seconds total.
Return JSON only: {{"topic":str,"hook":str,"scenes":[{{"narration":str(1-2 short sentences),"stock_query":str(2-3 English words for stock footage)}}] (6 scenes),"caption":str,"hashtags":[8 strings without #]}}
First scene narration = a curiosity hook. Last scene = a question asking viewers to comment."""
    r = requests.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        params={"key": GEMINI}, timeout=90,
        json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}})
    return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])

# 3) VOICE (edge-tts, free) + 4) STOCK FOOTAGE (Pexels, free) ----------------
async def tts(text, path):
    await edge_tts.Communicate(text, "en-US-AnaNeural", rate="+5%").save(path)

def pexels(q, i):
    r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": PEXELS},
                     params={"query": q, "orientation": "portrait", "per_page": 8}, timeout=30).json()
    for v in random.sample(r.get("videos", []), len(r.get("videos", []))):
        fs = sorted([f for f in v["video_files"] if f["height"] > f["width"]], key=lambda f: abs(f["height"] - 1280))
        if fs:
            p = f"work/s{i}.mp4"; Path(p).write_bytes(requests.get(fs[0]["link"], timeout=90).content); return p

def caption_img(text, i):
    img = Image.new("RGBA", (W, 500), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 68)
    lines, cur = [], ""
    for w in text.split():
        if d.textlength(cur + " " + w, font=f) > W - 140: lines.append(cur); cur = w
        else: cur = (cur + " " + w).strip()
    lines.append(cur); y = 250 - len(lines) * 45
    for l in lines:
        x = (W - d.textlength(l, font=f)) / 2
        d.text((x, y), l, font=f, fill="white", stroke_width=6, stroke_fill="black"); y += 90
    p = f"work/c{i}.png"; img.save(p); return p

def build(script, name):
    clips = []
    for i, s in enumerate(script["scenes"]):
        a = f"work/a{i}.mp3"; asyncio.run(tts(s["narration"], a))
        audio = AudioFileClip(a); d = audio.duration + 0.3
        p = pexels(s["stock_query"], i)
        if p:
            v = VideoFileClip(p).without_audio().resize(height=H)
            if v.w < W: v = v.resize(width=W)
            v = v.crop(x_center=v.w / 2, y_center=v.h / 2, width=W, height=H).fx(vfx.loop, duration=d)
        else: v = ColorClip((W, H), color=(30, 60, 120), duration=d)
        cap = ImageClip(caption_img(s["narration"], i)).set_duration(d).set_position(("center", 1150))
        clips.append(CompositeVideoClip([v, cap], size=(W, H)).set_audio(audio).set_duration(d))
    out = f"videos/{name}.mp4"
    concatenate_videoclips(clips).write_videofile(out, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None)
    return out

# 5) POST TO INSTAGRAM (official API) ------------------------------------------
def post(video_url, caption):
    r = requests.post(f"{G}/{IG_ID}/media", data={"media_type": "REELS", "video_url": video_url,
                      "caption": caption, "access_token": TOKEN}).json()
    cid = r["id"]
    for _ in range(40):
        s = requests.get(f"{G}/{cid}", params={"fields": "status_code", "access_token": TOKEN}).json()
        if s.get("status_code") == "FINISHED": break
        if s.get("status_code") == "ERROR": raise RuntimeError(s)
        time.sleep(15)
    return requests.post(f"{G}/{IG_ID}/media_publish", data={"creation_id": cid, "access_token": TOKEN}).json()

# 6) STATS for the phone dashboard ---------------------------------------------
def get(path, **p):
    return requests.get(G + path, params={**p, "access_token": TOKEN}, timeout=60).json()

def stats():
    acc = get(f"/{IG_ID}", fields="username,followers_count,media_count,profile_picture_url")
    media = get(f"/{IG_ID}/media", fields="id,caption,permalink,timestamp,like_count,comments_count,thumbnail_url,media_url", limit=30).get("data", [])
    for m in media:
        try: m["insights"] = {i["name"]: i["values"][0]["value"] for i in get(f"/{m['id']}/insights", metric="views,reach,shares,saved").get("data", [])}
        except Exception: m["insights"] = {}
        m["comments"] = get(f"/{m['id']}/comments", fields="username,text", limit=5).get("data", [])
    Path("docs/stats.json").write_text(json.dumps({"updated": datetime.now(timezone.utc).isoformat(), "account": acc, "media": media}))

if __name__ == "__main__":
    sc = make_script(); name = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    build(sc, name); history.append(sc["topic"]); HIST.write_text(json.dumps(history))
    push(f"video {name}"); time.sleep(60)  # let raw.githubusercontent.com serve the file
    cap = sc["caption"] + "\n\n" + " ".join("#" + h.strip("#") for h in sc["hashtags"])
    print(post(f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/videos/{name}.mp4", cap))
    for old in sorted(Path("videos").glob("*.mp4"))[:-3]: old.unlink()  # keep repo small
    time.sleep(30); stats(); push("stats")
