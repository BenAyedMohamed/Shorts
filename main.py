from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests, os, random, tempfile
from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip
from gtts import gTTS

# -----------------------------
# CONFIG
# -----------------------------
import os

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
HEADERS = {"Authorization": PEXELS_API_KEY}
TEMP_DIR = "temp_videos"
FINAL_DIR = "final_videos"
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(FINAL_DIR, exist_ok=True)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Cache to avoid re-fetching
clips_cache = {}

# -----------------------------
# Fetch Pexels videos
# -----------------------------
def fetch_pexels_videos(keyword: str, count=6):
    if keyword in clips_cache:
        return clips_cache[keyword]

    clips = []
    page = random.randint(1, 50)  # random page to avoid same results
    url = f"https://api.pexels.com/videos/search?query={keyword}&per_page={count}&page={page}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10).json()
        for video in response.get("videos", []):
            video_file = sorted(video["video_files"], key=lambda x: x["width"])[0]["link"]
            filename = os.path.join(TEMP_DIR, f"{keyword}_{random.randint(1000,9999)}.mp4")
            r = requests.get(video_file, stream=True)
            with open(filename, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            clips.append(filename)
    except Exception as e:
        print("Failed to fetch:", e)

    clips_cache[keyword] = clips
    return clips

# -----------------------------
# Proper resize for shorts or normal
# -----------------------------
def resize_clip(clip, target_w, target_h):
    w_ratio, h_ratio = target_w / clip.w, target_h / clip.h
    scale = min(w_ratio, h_ratio)
    new_w, new_h = int(clip.w*scale), int(clip.h*scale)
    clip = clip.resize(newsize=(new_w, new_h))
    # add black bars if needed
    if new_w < target_w or new_h < target_h:
        top = (target_h - new_h)//2
        bottom = target_h - new_h - top
        left = (target_w - new_w)//2
        right = target_w - new_w - left
        clip = clip.margin(top=top, bottom=bottom, left=left, right=right, color=(0,0,0))
    return clip

# -----------------------------
# Home page
# -----------------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# -----------------------------
# Fetch clips API
# -----------------------------
@app.get("/fetch")
def fetch(keyword: str):
    clips = fetch_pexels_videos(keyword)
    return {"clips": [os.path.basename(c) for c in clips]}

# -----------------------------
# Generate final video API
# -----------------------------
@app.post("/generate")
def generate(
    clips: str = Form(...),
    order: str = Form(...),
    start_times: str = Form(...),
    end_times: str = Form(...),
    layout: str = Form(...),
    script: str = Form(...),
    font_size: int = Form(...),
    font_family: str = Form(...),
):
    clips = clips.split(",")
    order = [int(i) for i in order.split(",")]
    start_times = [float(i) for i in start_times.split(",")]
    end_times = [float(i) for i in end_times.split(",")]

    target_w, target_h = (720, 1280) if layout=="shorts" else (1280, 720)
    video_clips = []

    # Process each clip
    for idx, clip_idx in enumerate(order):
        clip = VideoFileClip(os.path.join(TEMP_DIR, clips[clip_idx]))
        clip = clip.subclip(start_times[idx], end_times[idx])
        clip = resize_clip(clip, target_w, target_h)
        video_clips.append(clip)

    final = concatenate_videoclips(video_clips, method="compose")

    # Generate TTS audio
    audio_file = os.path.join(tempfile.gettempdir(), "audio.mp3")
    tts = gTTS(script, lang="en")
    tts.save(audio_file)
    final = final.set_audio(AudioFileClip(audio_file))

    output_path = os.path.join(FINAL_DIR, f"final_{random.randint(1000,9999)}.mp4")
    final.write_videofile(output_path, fps=24)
    return {"video": os.path.basename(output_path)}
