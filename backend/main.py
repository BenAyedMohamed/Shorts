from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import requests, random, os
from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip, TextClip, CompositeVideoClip
import edge_tts
from mutagen.mp3 import MP3
import traceback
from moviepy.config import change_settings
from pydub import AudioSegment

app = FastAPI()

# -----------------------------
# CORS
# -----------------------------
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# ImageMagick path
# -----------------------------
change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"})

# -----------------------------
# Folders
# -----------------------------
OUTPUT_FOLDER = "shorts/videos"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

TTS_FOLDER = "shorts/audio"
os.makedirs(TTS_FOLDER, exist_ok=True)

# -----------------------------
# Models
# -----------------------------
class ClipData(BaseModel):
    link: str
    keyword: str
    start: float
    end: float
    timelineStart: float

class MergeRequest(BaseModel):
    clips: List[ClipData]
    layout: str = "landscape"
    tts_path: str = None
    subtitles: str = None
    word_timings: list = None  # <-- received from front-end

class TTSRequest(BaseModel):
    text: str
    voice: str

# -----------------------------
# Merge Clips Endpoint
# -----------------------------
@app.post("/merge_clips/")
def merge_clips(req: MergeRequest):
    clips_list = []

    if not req.clips:
        raise HTTPException(status_code=400, detail="No clips provided")

    try:
        # -----------------------------
        # Download and process video clips
        # -----------------------------
        for clip_info in req.clips:
            try:
                local_path = os.path.join(OUTPUT_FOLDER, f"temp_{random.randint(1000,9999)}.mp4")
                r = requests.get(clip_info.link, stream=True, timeout=20)
                r.raise_for_status()
                with open(local_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

                clip = VideoFileClip(local_path).subclip(clip_info.start, clip_info.end)

                if req.layout == "shorts":
                    target_w, target_h = 720, 1280
                else:
                    target_w, target_h = 1280, 720

                clip = clip.resize(height=target_h)
                clip = clip.on_color(
                    size=(target_w, target_h),
                    color=(0, 0, 0),
                    pos=("center", "center")
                )

                clip = clip.set_start(clip_info.timelineStart)
                clips_list.append(clip)
            except Exception as e:
                print(f"Failed processing clip {clip_info.link}: {e}")
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"Clip processing error: {e}")

        final_video = concatenate_videoclips(clips_list, method="compose")

        # -----------------------------
        # Add TTS audio if provided
        # -----------------------------
        if req.tts_path:
            audio_clip = AudioFileClip(req.tts_path)
            if final_video.duration < audio_clip.duration:
                final_video = final_video.loop(duration=audio_clip.duration)
            final_video = final_video.set_audio(audio_clip)

        # -----------------------------
        # Add subtitles using word_timings from front-end
        # -----------------------------
        if req.subtitles and req.tts_path and req.word_timings:
            try:
                txt_clips = []
                words = req.subtitles.split()
                max_words_per_block = 9
                i = 0
                while i < len(words):
                    # Get the next block (up to 9 words)
                    block_words = words[i:i + max_words_per_block]
                    start_time = req.word_timings[i][0] if i < len(req.word_timings) else 0
                    end_time = req.word_timings[i + len(block_words) - 1][1] if (i + len(block_words) - 1) < len(req.word_timings) else start_time + 2
                    block_text = ' '.join(block_words)
                    if not block_text.endswith('.'):
                        block_text += '.'

                    txt = TextClip(
                        block_text,
                        fontsize=60,
                        color='white',
                        font='Arial Black',
                        stroke_color='black',
                        stroke_width=3,
                        method='caption',
                        size=(final_video.w - 100, None)
                    ).set_position('center').set_start(start_time).set_duration(end_time - start_time)
                    txt_clips.append(txt)
                    i += max_words_per_block

                final_video = CompositeVideoClip([final_video, *txt_clips])
            except Exception as e:
                print("=== Subtitle Error ===")
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"Subtitles could not be added: {e}. Check ImageMagick and font.")

        # -----------------------------
        # Write final video
        # -----------------------------
        output_filename = f"merged_{random.randint(1000,9999)}.mp4"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)

        final_video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=os.path.join(OUTPUT_FOLDER, "temp-audio.m4a"),
            remove_temp=True,
            fps=30
        )

        return {"merged_video_path": output_path.replace("\\", "/")}

    except Exception as e:
        print("=== Merge Clips Error ===")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error merging clips: {str(e)}")

# -----------------------------
# Text-to-Speech Endpoint
# -----------------------------
@app.post("/generate_tts/")
async def generate_tts(req: TTSRequest):
    voice_map = {
        "mysterious": "en-US-GuyNeural",
        "dark": "en-US-AriaNeural",
        "cheerful": "en-US-JennyNeural",
        "manly": "en-US-GuyNeural",
        "feminine": "en-US-JennyNeural"
    }
    selected_voice = voice_map.get(req.voice, "en-US-GuyNeural")

    filename = f"tts_{random.randint(1000,9999)}.mp3"
    output_path = os.path.join(TTS_FOLDER, filename)

    communicate = edge_tts.Communicate(req.text, selected_voice)
    await communicate.save(output_path)

    audio = MP3(output_path)
    length_sec = audio.info.length

    # Generate word timings
    timings = []
    words = req.text.split()
    if len(words) > 0:
        approx_duration = length_sec / len(words)
        current_time = 0
        for w in words:
            timings.append([current_time, current_time + approx_duration])
            current_time += approx_duration

    return {"audio_path": output_path.replace("\\","/"), "length": length_sec, "word_timings": timings}
