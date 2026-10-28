import os
import re
import json
import time
import base64
import asyncio
import subprocess
import tempfile
from io import BytesIO
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
from google import genai
from google.genai import types
import edge_tts

st.set_page_config(
    page_title="Studio99 Recap",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==================== STUDIO99 CLEAN MODERN UI CSS ====================
st.markdown("""
<style>
    .stApp {
        background-color: #EEF2F6 !important;
        color: #0F172A !important;
    }
    .block-container {
        padding-top: 0.6rem;
        padding-bottom: 4rem;
        max-width: 500px;
    }
    p, span, label, div[data-testid="stMarkdownContainer"] p {
        color: #1E293B !important;
    }
    .s99-topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 1.1rem;
        background: #131B2E;
        color: #FFFFFF !important;
        border-radius: 14px;
        margin-bottom: 0.75rem;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12);
    }
    .s99-title {
        font-size: 1.25rem;
        font-weight: 800;
        color: #38BDF8 !important;
        letter-spacing: 0.3px;
    }
    .s99-badge {
        background: rgba(56, 189, 248, 0.15);
        color: #38BDF8 !important;
        padding: 0.25rem 0.65rem;
        border-radius: 8px;
        font-size: 0.78rem;
        font-weight: 600;
        border: 1px solid rgba(56, 189, 248, 0.3);
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 16px !important;
        padding: 0.9rem !important;
        margin-bottom: 0.85rem !important;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04) !important;
    }
    input, textarea, div[data-baseweb="select"] > div {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
        border-color: #CBD5E1 !important;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #0284C7 0%, #2563EB 100%) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.65rem 1rem !important;
    }
    div.stButton > button[kind="primary"] p {
        color: #FFFFFF !important;
    }
    div.stDownloadButton > button {
        background: linear-gradient(90deg, #059669 0%, #10B981 100%) !important;
        color: #FFFFFF !important;
        font-weight: 800 !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 1rem !important;
    }
    div.stDownloadButton > button p {
        color: #FFFFFF !important;
    }
</style>
""", unsafe_allow_html=True)

USER_FONT_DIR = os.path.expanduser("~/.local/share/fonts")
os.makedirs(USER_FONT_DIR, exist_ok=True)

VOICE_PRESETS = {
    "မိန်းကလေး ၁ - တည်ငြိမ်": {"voice": "my-MM-NilarNeural", "rate": 0, "pitch": -2},
    "မိန်းကလေး ၂ - ပေါ့ပါး": {"voice": "my-MM-NilarNeural", "rate": 8, "pitch": 2},
    "မိန်းကလေး ၃ - နုပျို": {"voice": "my-MM-NilarNeural", "rate": 4, "pitch": 6},
    "ယောက်ျား ၁ - တက်ကြွ": {"voice": "my-MM-ThihaNeural", "rate": 10, "pitch": 2},
    "ယောက်ျား ၂ - လေးနက်": {"voice": "my-MM-ThihaNeural", "rate": 0, "pitch": -4},
    "ယောက်ျား ၃ - စိတ်လှုပ်ရှား": {"voice": "my-MM-ThihaNeural", "rate": 14, "pitch": 4}
}

NARRATION_STYLES = {
    "Direct Translation (မူရင်းအဓိပ္ပာယ်အတိုင်း ဘာသာပြန်မယ်)": "direct",
    "Third Person (ပြင်ပဇာတ်ကြောင်းပြောသူအနေနဲ့ ပြောမယ်)": "third_person",
    "First Person (အဓိကဇာတ်ကောင် ကိုယ်တိုင်ပြောသလို ပြောမယ်)": "first_person"
}

def clean_text_for_myanmar_font(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"[\u200b\u200c\u200d\u200e\u200f\ufeff\u202a-\u202e\u2060-\u206f]", "", text)
    replacements = {
        "“": "", "”": "", "‘": "", "’": "", "\"": "", "'": "",
        "—": " ", "–": " ", "…": "", "•": "", "*": "", "#": "",
        "~": "", "`": "", "^": "", "|": "", "<": "", ">": ""
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    eng_to_mm_digits = str.maketrans("0123456789", "၀၁၂၃၄၅၆၇၈၉")
    text = text.translate(eng_to_mm_digits)
    text = re.sub(r"[^\u1000-\u109F\uAA60-\uAA7F\uA9E0-\uA9FFa-zA-Z\s,\.\!\?\(\)\-\+/\:]", "", text)
    return re.sub(r"\s+", " ", text).strip()

def get_media_duration(file_path: str) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(res.stdout.strip())
    except Exception:
        return 0.0

def get_video_info(file_path: str):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate:stream_tags=rotate:format=duration",
        "-of", "json", file_path
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        data = json.loads(res.stdout)
        stream = data["streams"][0]
        w, h = int(stream["width"]), int(stream["height"])
        rot = int(stream.get("tags", {}).get("rotate", 0))
        if rot in (90, 270, -90, -270):
            w, h = h, w
        fps_parts = stream.get("r_frame_rate", "30/1").split("/")
        fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 and float(fps_parts[1]) != 0 else 30.0
        fps = min(30.0, max(15.0, fps))
        dur = float(data["format"]["duration"])
        return w, h, fps, dur
    except Exception:
        return 720, 1280, 30.0, 0.0

def format_mm_ss(seconds: float) -> str:
    seconds = max(0.0, seconds)
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"

def format_srt_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    msecs = int(round((seconds - int(seconds)) * 1000))
    if msecs >= 1000:
        secs += 1
        msecs -= 1000
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{msecs:03d}"

def extract_compressed_audio(video_path: str) -> str:
    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    subprocess.run(["ffmpeg", "-y", "-i", video_path, "-vn", "-ac", "1", "-ar", "16000", "-b:a", "48k", temp_audio], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return temp_audio

def split_into_short_lines(text: str, max_chars: int = 22) -> list:
    text = clean_text_for_myanmar_font(text)
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    tokens = re.split(r"(?<=[၊။,\.\!\?\s])", text)
    chunks, current = [], ""
    for token in tokens:
        if not token:
            continue
        if len(current) + len(token) <= max_chars:
            current += token
        else:
            if current.strip():
                chunks.append(current.strip())
            while len(token) > max_chars:
                chunks.append(token[:max_chars].strip())
                token = token[max_chars:]
            current = token
    if current.strip():
        chunks.append(current.strip())
    return chunks

def merge_close_whisper_segments(raw_segments: list, max_gap: float = 0.4, max_dur: float = 6.0) -> list:
    merged = []
    for seg in raw_segments:
        text = seg.get("text", "").strip() if isinstance(seg, dict) else getattr(seg, "text", "").strip()
        start = float(seg.get("start", 0.0) if isinstance(seg, dict) else getattr(seg, "start", 0.0))
        end = float(seg.get("end", 0.0) if isinstance(seg, dict) else getattr(seg, "end", 0.0))
        if not text or end <= start:
            continue
        if merged and (start - merged[-1]["end"] <= max_gap) and (end - merged[-1]["start"] <= max_dur):
            merged[-1]["end"] = end
            merged[-1]["text"] += " " + text
        else:
            merged.append({"start": start, "end": end, "text": text})
    return merged

def translate_segments_recap_style(gemini_client, groq_client, preferred_model: str, segments: list, style_mode: str):
    if style_mode == "third_person":
        style_instr = "Rewrite and translate into natural Burmese (Myanmar) as a THIRD-PERSON movie recap narrator. Keep each line concise."
    elif style_mode == "first_person":
        style_instr = "Rewrite and translate into natural Burmese (Myanmar) from a FIRST-PERSON perspective ('ကျွန်တော်/ကျွန်မ'). Keep each line concise."
    else:
        style_instr = "Translate directly and naturally into spoken Burmese (Myanmar) keeping original POV. Keep each line concise."

    fallback_models = [preferred_model.strip(), "gemini-3.8-flash", "gemini-3.1-flash-lite-preview", "gemini-2.5-flash"]
    model_chain = []
    for m in fallback_models:
        if m not in model_chain:
            model_chain.append(m)

    batch_size = 25
    for i in range(0, len(segments), batch_size):
        batch = segments[i:i + batch_size]
        payload = [{"id": idx, "text": s["text"]} for idx, s in enumerate(batch)]
        prompt = (
            f"{style_instr}\nDo not use emojis or special symbols. "
            f"Return ONLY a JSON list of objects with 'id' and 'translation':\n{json.dumps(payload, ensure_ascii=False)}"
        )

        translated_ok = False
        for model_name in model_chain:
            for _ in range(2):
                try:
                    resp = gemini_client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    parsed = json.loads(resp.text.strip())
                    if isinstance(parsed, dict) and "translations" in parsed:
                        parsed = parsed["translations"]
                    t_map = {int(item["id"]): str(item.get("translation", "")).strip() for item in parsed if "id" in item}
                    for idx, s in enumerate(batch):
                        s["translated"] = clean_text_for_myanmar_font(t_map.get(idx, s["text"]))
                    translated_ok = True
                    break
                except Exception as e:
                    if "503" in str(e) or "429" in str(e):
                        time.sleep(1.5)
                        continue
                    break
            if translated_ok:
                break

        if not translated_ok:
            groq_resp = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": f"{style_instr} Output valid JSON only."},
                    {"role": "user", "content": f"Return JSON object with key 'items' containing list of 'id' and 'translation':\n{json.dumps(payload, ensure_ascii=False)}"}
                ],
                response_format={"type": "json_object"}
            )
            g_data = json.loads(groq_resp.choices[0].message.content)
            g_list = g_data.get("items", g_data) if isinstance(g_data, dict) else g_data
            t_map = {int(item["id"]): str(item.get("translation", "")).strip() for item in g_list if isinstance(item, dict) and "id" in item}
            for idx, s in enumerate(batch):
                s["translated"] = clean_text_for_myanmar_font(t_map.get(idx, s["text"]))

async def synthesize_all_tts(segments, voice_id, rate_str, pitch_str):
    sem = asyncio.Semaphore(6)
    async def _one(idx, text):
        async with sem:
            raw_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
            trimmed_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
            comm = edge_tts.Communicate(text=text or " ", voice=voice_id, rate=rate_str, pitch=pitch_str)
            with open(raw_mp3, "wb") as f:
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
            subprocess.run([
                "ffmpeg", "-y", "-i", raw_mp3,
                "-af", "silenceremove=start_periods=1:start_silence=0.03:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_silence=0.05:start_threshold=-45dB,areverse",
                "-ar", "44100", "-ac", "1", trimmed_wav
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            dur = get_media_duration(trimmed_wav)
            if dur <= 0.05:
                subprocess.run(["ffmpeg", "-y", "-i", raw_mp3, "-ar", "44100", "-ac", "1", trimmed_wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                dur = max(0.3, get_media_duration(trimmed_wav))
            if os.path.exists(raw_mp3):
                os.remove(raw_mp3)
            return idx, trimmed_wav, dur

    return await asyncio.gather(*[_one(i, s["translated"]) for i, s in enumerate(segments)])

def build_studio99_local_engine_html(
    subs_json_str: str,
    tts_audio_b64: str,
    custom_font_b64: str
) -> str:
    """
    Studio99 ပုံစံအတိုင်း ဖုန်းထဲတွင် လုံးဝမထစ်ဘဲ 60FPS တိုက်ရိုက် အလုပ်လုပ်မည့်
    HTML5 Canvas + Touch Drag (Blur 1, Blur 2, Subtitle, Ratio, Background, Local Render) Engine
    """
    font_face_css = ""
    if custom_font_b64:
        font_face_css = f"""
        @font-face {{
            font-family: 'CustomMyanmarFont';
            src: url(data:font/ttf;base64,{custom_font_b64}) format('truetype');
        }}
        """

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Myanmar:wght@500;700&family=Padauk:wght@700&display=swap" rel="stylesheet">
<style>
    {font_face_css}
    * {{
        box-sizing: border-box;
        user-select: none;
        -webkit-user-select: none;
    }}
    body {{
        margin: 0;
        padding: 4px;
        background: #EEF2F6;
        font-family: 'Noto Sans Myanmar', sans-serif;
        color: #0F172A;
    }}
    .s99-card {{
        background: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-radius: 16px;
        padding: 14px;
        margin-bottom: 12px;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
    }}
    .gallery-btn {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        width: 100%;
        padding: 12px;
        background: #0F172A;
        color: #FFFFFF;
        border: 1.5px solid #14B8A6;
        border-radius: 12px;
        font-weight: 700;
        font-size: 0.95rem;
        cursor: pointer;
        margin-bottom: 10px;
    }}
    .canvas-container {{
        position: relative;
        width: 100%;
        background: #1E293B;
        border-radius: 14px;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 340px;
        touch-action: none;
    }}
    canvas {{
        max-width: 100%;
        max-height: 440px;
        border-radius: 8px;
        display: block;
        touch-action: none;
    }}
    .ctrl-bar {{
        display: flex;
        align-items: center;
        gap: 10px;
        margin-top: 10px;
        padding: 6px 10px;
        background: #F8FAFC;
        border-radius: 10px;
        border: 1px solid #E2E8F0;
    }}
    .play-btn {{
        background: #0284C7;
        color: white;
        border: none;
        border-radius: 8px;
        width: 36px;
        height: 32px;
        font-size: 1rem;
        cursor: pointer;
        font-weight: bold;
    }}
    .time-slider {{
        flex: 1;
        accent-color: #0284C7;
    }}
    .time-txt {{
        font-size: 0.78rem;
        font-weight: 600;
        color: #475569;
        min-width: 72px;
        text-align: right;
    }}
    .section-title {{
        font-size: 0.92rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 6px;
    }}
    .blur-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid #F1F5F9;
    }}
    .switch {{
        position: relative;
        display: inline-block;
        width: 48px;
        height: 26px;
    }}
    .switch input {{
        opacity: 0;
        width: 0;
        height: 0;
    }}
    .slider-tog {{
        position: absolute;
        cursor: pointer;
        top: 0; left: 0; right: 0; bottom: 0;
        background-color: #CBD5E1;
        transition: .25s;
        border-radius: 26px;
    }}
    .slider-tog:before {{
        position: absolute;
        content: "";
        height: 20px;
        width: 20px;
        left: 3px;
        bottom: 3px;
        background-color: white;
        transition: .25s;
        border-radius: 50%;
    }}
    input:checked + .slider-tog {{
        background-color: #0EA5E9;
    }}
    input:checked + .slider-tog.pink {{
        background-color: #D946EF;
    }}
    input:checked + .slider-tog:before {{
        transform: translateX(22px);
    }}
    .ratio-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
        margin-bottom: 12px;
    }}
    .ratio-btn {{
        padding: 9px 4px;
        background: #F8FAFC;
        border: 1.5px solid #CBD5E1;
        border-radius: 10px;
        font-weight: 700;
        color: #334155;
        cursor: pointer;
        text-align: center;
        font-size: 0.85rem;
    }}
    .ratio-btn.active {{
        border-color: #EAB308;
        background: #FEF9C3;
        color: #854D0E;
    }}
    .bg-upload-btn {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        width: 100%;
        padding: 10px;
        background: #F8FAFC;
        border: 1px dashed #94A3B8;
        border-radius: 10px;
        color: #1E293B;
        font-size: 0.85rem;
        font-weight: 600;
        cursor: pointer;
    }}
    .color-dots {{
        display: flex;
        gap: 12px;
        margin: 8px 0;
    }}
    .c-dot {{
        width: 30px;
        height: 30px;
        border-radius: 50%;
        cursor: pointer;
        border: 2px solid #94A3B8;
    }}
    .c-dot.active {{
        border: 3px solid #0284C7;
        transform: scale(1.12);
    }}
    .render-btn {{
        width: 100%;
        padding: 13px;
        background: linear-gradient(90deg, #059669 0%, #10B981 100%);
        color: white;
        border: none;
        border-radius: 12px;
        font-weight: 800;
        font-size: 0.96rem;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        margin-top: 6px;
    }}
    .hint-badge {{
        font-size: 0.76rem;
        color: #64748B;
        text-align: center;
        margin-top: 6px;
    }}
</style>
</head>
<body>

<div class="s99-card">
    <label class="gallery-btn">
        <span>🖼️ Gallery မှ ဗီဒီယို ရွေးမည် (Instant Local Preview)</span>
        <input type="file" id="localVidInput" accept="video/*" style="display:none">
    </label>

    <div class="canvas-container" id="canvasWrap">
        <canvas id="studioCanvas" width="360" height="640"></canvas>
    </div>

    <div class="ctrl-bar">
        <button class="play-btn" id="playBtn">▶</button>
        <input type="range" class="time-slider" id="seekSlider" min="0" max="100" step="0.05" value="0">
        <span class="time-txt" id="timeDisplay">0:00 / 0:00</span>
    </div>
    <div class="hint-badge">💡 Video ပေါ်ရှိ <b>Blur 1</b>, <b>Blur 2</b> နှင့် <b>မြန်မာစာတန်း</b> ကို လက်ဖြင့် တိုက်ရိုက် ဖိဆွဲရွှေ့နိုင်ပါသည် (ထောင့်စက်လေးမှ အကြီးအသေးချဲ့ပါ)</div>
</div>

<!-- BLUR MASK CARD -->
<div class="s99-card">
    <div class="section-title">🏁 Blur Mask (လက်ဖြင့်ဖိဆွဲ၍ နေရာရွှေ့ပါ)</div>
    <div class="blur-row">
        <div style="display:flex;align-items:center;gap:10px;">
            <label class="switch">
                <input type="checkbox" id="blur1Toggle" checked>
                <span class="slider-tog"></span>
            </label>
            <span style="color:#0284C7;font-weight:700;">Blur 1 (အောက်စာတန်းဖုံးရန်)</span>
        </div>
        <input type="range" id="blur1Power" min="4" max="30" value="16" style="width:90px">
    </div>
    <div class="blur-row" style="border-bottom:none;">
        <div style="display:flex;align-items:center;gap:10px;">
            <label class="switch">
                <input type="checkbox" id="blur2Toggle">
                <span class="slider-tog pink"></span>
            </label>
            <span style="color:#C026D3;font-weight:700;">Blur 2 (အပေါ် Logo ဖုံးရန်)</span>
        </div>
        <input type="range" id="blur2Power" min="4" max="30" value="16" style="width:90px">
    </div>
</div>

<!-- VIDEO RATIO & BACKGROUND CARD -->
<div class="s99-card">
    <div class="section-title">📐 Video Ratio & Background</div>
    <div class="ratio-grid">
        <div class="ratio-btn active" onclick="setRatio('9:16', this)">9:16</div>
        <div class="ratio-btn" onclick="setRatio('16:9', this)">16:9</div>
        <div class="ratio-btn" onclick="setRatio('1:1', this)">1:1</div>
        <div class="ratio-btn" onclick="setRatio('4:3', this)">4:3</div>
    </div>
    <label class="bg-upload-btn">
        <span>🏞️ 9:16 နောက်ခံပုံ (Background) တင်မည်</span>
        <input type="file" id="bgImgInput" accept="image/*" style="display:none">
    </label>
    <div style="display:flex;gap:12px;margin-top:10px;align-items:center;justify-content:space-between;">
        <label style="font-size:0.84rem;font-weight:600;">🪞 ဘယ်ညာလှည့် (Mirror):</label>
        <input type="checkbox" id="mirrorToggle" style="width:18px;height:18px;">
        <label style="font-size:0.84rem;font-weight:600;">🔍 Video Zoom:</label>
        <input type="range" id="vidZoom" min="60" max="140" value="100" style="width:100px;">
    </div>
</div>

<!-- SUBTITLE & WATERMARK STYLE CARD -->
<div class="s99-card">
    <div class="section-title">🎨 မြန်မာစာတန်း နှင့် Watermark (လက်ဖြင့်ရွှေ့နိုင်သည်)</div>
    <div style="display:flex;justify-content:space-between;align-items:center;">
        <span style="font-size:0.84rem;font-weight:600;">စာလုံးအရောင်:</span>
        <div class="color-dots">
            <div class="c-dot" style="background:#FFFFFF;" onclick="setSubColor('#FFFFFF', this)"></div>
            <div class="c-dot" style="background:#FFE600;" onclick="setSubColor('#FFE600', this)"></div>
            <div class="c-dot active" style="background:#38BDF8;" onclick="setSubColor('#38BDF8', this)"></div>
            <div class="c-dot" style="background:#F472B6;" onclick="setSubColor('#F472B6', this)"></div>
        </div>
    </div>
    <div style="display:flex;gap:10px;align-items:center;margin-top:6px;">
        <span style="font-size:0.84rem;font-weight:600;">စာလုံးအရွယ်:</span>
        <input type="range" id="subSizeSlider" min="14" max="34" value="21" style="flex:1;">
        <label style="font-size:0.8rem;font-weight:600;"><input type="checkbox" id="subBgToggle" checked> နောက်ခံဘောင်</label>
    </div>
    <div style="display:flex;gap:8px;align-items:center;margin-top:8px;">
        <input type="text" id="wmTextInput" value="MY RECAP" placeholder="Channel Watermark" style="flex:1;padding:6px 10px;border-radius:8px;border:1px solid #CBD5E1;">
        <input type="range" id="wmOpacitySlider" min="0" max="100" value="55" style="width:90px;" title="Watermark Opacity">
    </div>
</div>

<!-- LOCAL HARDWARE RENDER CARD -->
<div class="s99-card">
    <div class="section-title">⚡ Local Smooth Render (ဖုန်းထဲတွင် တိုက်ရိုက်ထုတ်ယူရန်)</div>
    <button class="render-btn" id="localRenderBtn" onclick="startLocalRecord()">🎬 Local Video Render စတင်မည် (Smooth 30FPS)</button>
    <div id="renderStatus" class="hint-badge">စကားပြောသံ (Voiceover) နှင့် စာတန်းထိုးများကို ဖုန်းထဲတွင် တိုက်ရိုက် ဖမ်းယူပေါင်းစပ်ပေးပါမည်။</div>
    <a id="downloadLink" style="display:none;margin-top:10px;text-align:center;padding:11px;background:#0284C7;color:white;border-radius:10px;text-decoration:none;font-weight:800;display:none;">📥 ပြီးဆုံးသွားသော Video ကို Download ဆွဲရန်</a>
</div>

<script>
const subsData = {subs_json_str};
const ttsAudioB64 = "{tts_audio_b64}";
const hasCustomFont = {str(bool(custom_font_b64)).lower()};

const canvas = document.getElementById('studioCanvas');
const ctx = canvas.getContext('2d');
const playBtn = document.getElementById('playBtn');
const seekSlider = document.getElementById('seekSlider');
const timeDisplay = document.getElementById('timeDisplay');

const video = document.createElement('video');
video.playsInline = true;
video.crossOrigin = "anonymous";

const ttsAudio = new Audio();
if (ttsAudioB64.length > 50) {{
    ttsAudio.src = "data:audio/mp3;base64," + ttsAudioB64;
    video.muted = true; // AI Voiceover ရှိပါက မူရင်းအသံပိတ်ပြီး AI အသံဖွင့်မည်
}}

let bgImage = null;
let currentRatio = '9:16';
let subColor = '#38BDF8';
let isRecording = false;
let mediaRecorder = null;
let recordedChunks = [];

// လက်ဖြင့် တိုက်ရိုက် ဆွဲရွှေ့နိုင်မည့် Interactive Boxes (Normalized 0.0 to 1.0)
let boxes = {{
    blur1: {{ x: 0.08, y: 0.74, w: 0.84, h: 0.11, color: '#00E5FF', label: 'Blur 1' }},
    blur2: {{ x: 0.06, y: 0.06, w: 0.35, h: 0.08, color: '#E879F9', label: 'Blur 2' }},
    sub:   {{ x: 0.50, y: 0.79, w: 0.80, h: 0.08, color: '#FACC15', label: 'Subtitle' }},
    wm:    {{ x: 0.82, y: 0.06, w: 0.24, h: 0.05, color: '#94A3B8', label: 'Watermark' }},
    vid:   {{ x: 0.0,  y: 0.0 }}
}};

let activeDrag = null;
let dragMode = null; // 'move' or 'resize'
let startPt = {{ x: 0, y: 0 }};
let origBox = null;
let showHandlesTimeout = null;
let showHandles = true;

function triggerHandles() {{
    showHandles = true;
    if (showHandlesTimeout) clearTimeout(showHandlesTimeout);
    showHandlesTimeout = setTimeout(() => {{ if (!activeDrag) showHandles = false; }}, 3200);
}}

document.getElementById('localVidInput').addEventListener('change', function(e) {{
    const file = e.target.files[0];
    if (!file) return;
    video.src = URL.createObjectURL(file);
    video.load();
    video.onloadedmetadata = () => {{
        seekSlider.max = video.duration || 100;
        video.currentTime = Math.min(1.0, video.duration * 0.1);
        triggerHandles();
    }};
}});

document.getElementById('bgImgInput').addEventListener('change', function(e) {{
    const file = e.target.files[0];
    if (!file) return;
    const img = new Image();
    img.onload = () => {{ bgImage = img; }};
    img.src = URL.createObjectURL(file);
}});

function setRatio(r, el) {{
    currentRatio = r;
    document.querySelectorAll('.ratio-btn').forEach(b => b.classList.remove('active'));
    el.classList.add('active');
    if (r === '9:16') {{ canvas.width = 540; canvas.height = 960; }}
    else if (r === '16:9') {{ canvas.width = 854; canvas.height = 480; }}
    else if (r === '1:1') {{ canvas.width = 640; canvas.height = 640; }}
    else if (r === '4:3') {{ canvas.width = 640; canvas.height = 480; }}
    triggerHandles();
}}
setRatio('9:16', document.querySelector('.ratio-btn'));

function setSubColor(c, el) {{
    subColor = c;
    document.querySelectorAll('.c-dot').forEach(d => d.classList.remove('active'));
    el.classList.add('active');
}}

playBtn.addEventListener('click', () => {{
    if (video.paused) {{
        video.play();
        if (ttsAudio.src) {{
            ttsAudio.currentTime = video.currentTime;
            ttsAudio.play();
        }}
        playBtn.textContent = '⏸';
    }} else {{
        video.pause();
        if (ttsAudio.src) ttsAudio.pause();
        playBtn.textContent = '▶';
    }}
}});

seekSlider.addEventListener('input', () => {{
    video.currentTime = parseFloat(seekSlider.value);
    if (ttsAudio.src) ttsAudio.currentTime = video.currentTime;
}});

video.addEventListener('timeupdate', () => {{
    if (!seekSlider.matches(':active')) seekSlider.value = video.currentTime;
    const cur = formatSec(video.currentTime);
    const dur = formatSec(video.duration || 0);
    timeDisplay.textContent = `${{cur}} / ${{dur}}`;
}});

function formatSec(s) {{
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${{m}}:${{sec < 10 ? '0' : ''}}${{sec}}`;
}}

// ==================== SMOOTH 60FPS TOUCH DRAG & RESIZE ENGINE ====================
function getCanvasCoords(e) {{
    const rect = canvas.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    return {{
        x: (clientX - rect.left) / rect.width,
        y: (clientY - rect.top) / rect.height
    }};
}}

function hitTest(pt) {{
    const b1On = document.getElementById('blur1Toggle').checked;
    const b2On = document.getElementById('blur2Toggle').checked;

    // ၁။ Subtitle နှင့် Watermark စစ်ဆေးခြင်း
    if (Math.abs(pt.x - boxes.sub.x) < 0.35 && Math.abs(pt.y - boxes.sub.y) < 0.05) {{
        return {{ key: 'sub', mode: 'move' }};
    }}
    if (Math.abs(pt.x - boxes.wm.x) < 0.15 && Math.abs(pt.y - boxes.wm.y) < 0.04) {{
        return {{ key: 'wm', mode: 'move' }};
    }}

    // ၂။ Blur 2 နှင့် Blur 1 စစ်ဆေးခြင်း (ညာအောက်ထောင့် = resize, အတွင်းပိုင်း = move)
    const checkBox = (b) => {{
        const rx = b.x + b.w;
        const ry = b.y + b.h;
        if (Math.abs(pt.x - rx) < 0.06 && Math.abs(pt.y - ry) < 0.05) return 'resize';
        if (pt.x >= b.x && pt.x <= rx && pt.y >= b.y && pt.y <= ry) return 'move';
        return null;
    }};

    if (b2On) {{
        const m2 = checkBox(boxes.blur2);
        if (m2) return {{ key: 'blur2', mode: m2 }};
    }}
    if (b1On) {{
        const m1 = checkBox(boxes.blur1);
        if (m1) return {{ key: 'blur1', mode: m1 }};
    }}
    return {{ key: 'vid', mode: 'move' }};
}}

function onPointerDown(e) {{
    triggerHandles();
    const pt = getCanvasCoords(e);
    const hit = hitTest(pt);
    if (hit) {{
        e.preventDefault();
        activeDrag = hit.key;
        dragMode = hit.mode;
        startPt = pt;
        origBox = {{ ...boxes[activeDrag] }};
    }}
}}

function onPointerMove(e) {{
    if (!activeDrag) return;
    e.preventDefault();
    triggerHandles();
    const pt = getCanvasCoords(e);
    const dx = pt.x - startPt.x;
    const dy = pt.y - startPt.y;

    if (activeDrag === 'sub' || activeDrag === 'wm') {{
        boxes[activeDrag].x = Math.min(0.92, Math.max(0.08, origBox.x + dx));
        boxes[activeDrag].y = Math.min(0.95, Math.max(0.04, origBox.y + dy));
    }} else if (activeDrag === 'vid') {{
        boxes.vid.x = Math.min(0.5, Math.max(-0.5, origBox.x + dx));
        boxes.vid.y = Math.min(0.5, Math.max(-0.5, origBox.y + dy));
    }} else {{
        if (dragMode === 'move') {{
            boxes[activeDrag].x = Math.min(1.0 - origBox.w, Math.max(0.0, origBox.x + dx));
            boxes[activeDrag].y = Math.min(1.0 - origBox.h, Math.max(0.0, origBox.y + dy));
        }} else {{
            boxes[activeDrag].w = Math.min(1.0 - origBox.x, Math.max(0.10, origBox.w + dx));
            boxes[activeDrag].h = Math.min(1.0 - origBox.y, Math.max(0.04, origBox.h + dy));
        }}
    }}
}}

function onPointerUp() {{
    activeDrag = null;
    dragMode = null;
}}

canvas.addEventListener('mousedown', onPointerDown);
window.addEventListener('mousemove', onPointerMove);
window.addEventListener('mouseup', onPointerUp);
canvas.addEventListener('touchstart', onPointerDown, {{ passive: false }});
window.addEventListener('touchmove', onPointerMove, {{ passive: false }});
window.addEventListener('touchend', onPointerUp);

// ==================== 60FPS HARDWARE ACCELERATED RENDER LOOP ====================
function renderLoop() {{
    const cw = canvas.width;
    const ch = canvas.height;
    ctx.clearRect(0, 0, cw, ch);

    // ၁။ နောက်ခံပုံ (သို့မဟုတ်) အမည်းရောင် ဆွဲခြင်း
    if (bgImage) {{
        ctx.drawImage(bgImage, 0, 0, cw, ch);
    }} else {{
        ctx.fillStyle = '#0F172A';
        ctx.fillRect(0, 0, cw, ch);
    }}

    // ၂။ မူရင်း Video ဆွဲခြင်း
    if (video.readyState >= 2) {{
        const vw = video.videoWidth || 720;
        const vh = video.videoHeight || 1280;
        const zoom = parseFloat(document.getElementById('vidZoom').value) / 100.0;
        const scale = Math.min(cw / vw, ch / vh) * zoom;
        const dw = vw * scale;
        const dh = vh * scale;
        const dx = (cw - dw) / 2 + (boxes.vid.x * cw);
        const dy = (ch - dh) / 2 + (boxes.vid.y * ch);

        ctx.save();
        if (document.getElementById('mirrorToggle').checked) {{
            ctx.translate(cw, 0);
            ctx.scale(-1, 1);
            ctx.drawImage(video, cw - dx - dw, dy, dw, dh);
        }} else {{
            ctx.drawImage(video, dx, dy, dw, dh);
        }}
        ctx.restore();
    }} else {{
        ctx.fillStyle = '#64748B';
        ctx.font = '600 18px "Noto Sans Myanmar", sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('▶ Preview မြင်ရရန် အပေါ်မှ ဗီဒီယိုရွေးပါ', cw / 2, ch / 2);
    }}

    // ၃။ Blur Mask 1 နှင့် Blur 2 ဆွဲခြင်း
    const drawBlurRegion = (b, powerId, isEnabled) => {{
        if (!isEnabled) return;
        const bx = b.x * cw;
        const by = b.y * ch;
        const bw = b.w * cw;
        const bh = b.h * ch;
        const blurPx = parseInt(document.getElementById(powerId).value);

        ctx.save();
        ctx.beginPath();
        ctx.roundRect(bx, by, bw, bh, 8);
        ctx.clip();
        ctx.filter = `blur(${{blurPx}}px)`;
        ctx.drawImage(canvas, 0, 0);
        ctx.filter = 'none';
        ctx.fillStyle = 'rgba(15, 23, 42, 0.32)';
        ctx.fillRect(bx, by, bw, bh);
        ctx.restore();

        if (showHandles && !isRecording) {{
            ctx.save();
            ctx.strokeStyle = b.color;
            ctx.lineWidth = 2.5;
            ctx.beginPath();
            ctx.roundRect(bx, by, bw, bh, 8);
            ctx.stroke();
            // Resize Handle
            ctx.fillStyle = b.color;
            ctx.beginPath();
            ctx.arc(bx + bw, by + bh, 9, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        }}
    }};

    drawBlurRegion(boxes.blur1, 'blur1Power', document.getElementById('blur1Toggle').checked);
    drawBlurRegion(boxes.blur2, 'blur2Power', document.getElementById('blur2Toggle').checked);

    // ၄။ Channel Watermark ဆွဲခြင်း
    const wmTxt = document.getElementById('wmTextInput').value.trim();
    const wmOp = parseInt(document.getElementById('wmOpacitySlider').value) / 100.0;
    if (wmTxt && wmOp > 0) {{
        ctx.save();
        ctx.font = '700 20px "Noto Sans Myanmar", sans-serif';
        ctx.fillStyle = `rgba(255, 255, 255, ${{wmOp}})`;
        ctx.textAlign = 'center';
        ctx.fillText(wmTxt, boxes.wm.x * cw, boxes.wm.y * ch);
        ctx.restore();
    }}

    // ၅။ မြန်မာစာတန်းထိုး (Active Subtitle) ဆွဲခြင်း
    const curTime = video.currentTime || 0;
    let activeText = "ပြန်စရာအိမ်မရှိတော့တဲ့ (စာတန်းနမူနာ)";
    if (subsData.length > 0) {{
        activeText = "";
        for (let i = 0; i < subsData.length; i++) {{
            if (curTime >= subsData[i].start && curTime <= subsData[i].end) {{
                activeText = subsData[i].text;
                break;
            }}
        }}
        if (!activeText && video.paused) activeText = subsData[0].text;
    }}

    if (activeText) {{
        const fSize = parseInt(document.getElementById('subSizeSlider').value) * (cw / 420.0);
        const fontFam = hasCustomFont ? '"CustomMyanmarFont", "Noto Sans Myanmar"' : '"Noto Sans Myanmar", "Padauk"';
        ctx.save();
        ctx.font = `700 ${{fSize}}px ${{fontFam}}`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        const sx = boxes.sub.x * cw;
        const sy = boxes.sub.y * ch;
        const metrics = ctx.measureText(activeText);
        const tw = metrics.width;
        const th = fSize * 1.35;

        if (document.getElementById('subBgToggle').checked) {{
            ctx.fillStyle = 'rgba(15, 15, 15, 0.68)';
            ctx.beginPath();
            ctx.roundRect(sx - tw / 2 - 16, sy - th / 2 - 4, tw + 32, th + 8, 10);
            ctx.fill();
        }}

        ctx.lineWidth = Math.max(3, fSize * 0.16);
        ctx.strokeStyle = '#000000';
        ctx.strokeText(activeText, sx, sy);
        ctx.fillStyle = subColor;
        ctx.fillText(activeText, sx, sy);
        ctx.restore();
    }}

    requestAnimationFrame(renderLoop);
}}
requestAnimationFrame(renderLoop);

// ==================== LOCAL MEDIA RECORDER ENGINE ====================
function startLocalRecord() {{
    if (!video.src) {{
        alert("ကျေးဇူးပြု၍ အပေါ်ဆုံးမှ Gallery ဗီဒီယို အရင်ရွေးပေးပါ။");
        return;
    }}
    const statusEl = document.getElementById('renderStatus');
    const dlLink = document.getElementById('downloadLink');
    const btn = document.getElementById('localRenderBtn');

    dlLink.style.display = 'none';
    isRecording = true;
    showHandles = false;
    recordedChunks = [];

    const canvasStream = canvas.captureStream(30);
    // Audio ပေါင်းထည့်ခြင်း
    try {{
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const dest = audioCtx.createMediaStreamDestination();
        if (ttsAudio.src) {{
            const srcNode = audioCtx.createMediaElementSource(ttsAudio);
            srcNode.connect(dest);
            srcNode.connect(audioCtx.destination);
        }} else {{
            video.muted = false;
            const vNode = audioCtx.createMediaElementSource(video);
            vNode.connect(dest);
            vNode.connect(audioCtx.destination);
        }}
        dest.stream.getAudioTracks().forEach(t => canvasStream.addTrack(t));
    }} catch (err) {{
        console.log("Audio mux note:", err);
    }}

    const mime = MediaRecorder.isTypeSupported('video/mp4') ? 'video/mp4' : 'video/webm;codecs=vp9';
    mediaRecorder = new MediaRecorder(canvasStream, {{ mimeType: mime, videoBitsPerSecond: 2200000 }});

    mediaRecorder.ondataavailable = (e) => {{
        if (e.data && e.data.size > 0) recordedChunks.push(e.data);
    }};

    mediaRecorder.onstop = () => {{
        isRecording = false;
        btn.textContent = "🎬 Local Video Render စတင်မည် (Smooth 30FPS)";
        statusEl.textContent = "✅ Local Render အောင်မြင်စွာ ပြီးဆုံးပါပြီ!";
        const blob = new Blob(recordedChunks, {{ type: mime }});
        dlLink.href = URL.createObjectURL(blob);
        dlLink.download = mime.includes('mp4') ? "Studio99_Recap.mp4" : "Studio99_Recap.webm";
        dlLink.style.display = 'block';
    }};

    video.currentTime = 0;
    if (ttsAudio.src) ttsAudio.currentTime = 0;
    video.play();
    if (ttsAudio.src) ttsAudio.play();
    mediaRecorder.start(200);
    btn.textContent = "⏳ Local Rendering လုပ်နေပါသည် (ပြီးသည်အထိ ခဏစောင့်ပါ)...";

    video.onended = () => {{
        if (mediaRecorder && mediaRecorder.state === 'recording') {{
            mediaRecorder.stop();
        }}
    }};
}}
</script>
</body>
</html>
"""

# ==================== TOP HEADER ====================
st.markdown("""
<div class="s99-topbar">
    <div class="s99-title">Studio99</div>
    <div class="s99-badge">⚡ Smooth Local Canvas</div>
</div>
""", unsafe_allow_html=True)

if "script_segments" not in st.session_state:
    st.session_state["script_segments"] = []
if "tts_b64" not in st.session_state:
    st.session_state["tts_b64"] = ""
if "subs_timeline" not in st.session_state:
    st.session_state["subs_timeline"] = []

# ==================== SIDEBAR / API KEYS ====================
default_groq = st.secrets.get("GROQ_API_KEY", "") if "GROQ_API_KEY" in st.secrets else ""
default_gemini = st.secrets.get("GEMINI_API_KEY", "") if "GEMINI_API_KEY" in st.secrets else ""

with st.expander("🔑 API Keys နှင့် Custom Font (.ttf) ထည့်သွင်းရန်", expanded=not (default_groq and default_gemini)):
    groq_key = st.text_input("Groq API Key (gsk_...)", value=default_groq, type="password")
    gemini_key = st.text_input("Gemini API Key (AIzaSy...)", value=default_gemini, type="password")
    gemini_model = st.selectbox("Gemini Model", ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-3.1-flash-lite-preview", "gemini-2.5-flash"])
    uploaded_font = st.file_uploader("📁 မြန်မာ Custom Font (.ttf) တင်ရန် (ဥပမာ AJ 02)", type=["ttf", "otf"])
    custom_font_b64 = base64.b64encode(uploaded_font.getvalue()).decode("utf-8") if uploaded_font else ""

# ==================== STEP 1: AI SCRIPT & VOICEOVER GENERATOR ====================
with st.container(border=True):
    st.markdown("##### 🤖 ၁။ AI မြန်မာဘာသာပြန် Script နှင့် Voiceover ထုတ်ရန် (Optional)")
    st.caption("အောက်က Local Canvas မှာ Video တိုက်ရိုက်ရွေးပြီး Blur ဖုံးရုံသာမက AI အသံနှင့် မြန်မာစာတန်းပါ ထည့်လိုပါက ဒီနေရာမှ Video တင်ပြီး Script ထုတ်နိုင်ပါသည်။")

    ai_video_file = st.file_uploader("AI ဖြင့် အသံနှင့်စာတန်းထုတ်ရန် Video ရွေးပါ", type=["mp4", "mov", "mkv", "webm"], label_visibility="collapsed")
    narration_label = st.selectbox("ဇာတ်ကြောင်းပုံစံ", list(NARRATION_STYLES.keys()))
    voice_label = st.selectbox("Voiceover အသံ", list(VOICE_PRESETS.keys()), index=4)

    if st.button("🪄 AI မြန်မာ Script + Voiceover အသံ ထုတ်မည်", type="primary", use_container_width=True):
        if not ai_video_file:
            st.error("AI Script ထုတ်ရန် Video ဖိုင် အရင်ရွေးပေးပါ။")
        elif not groq_key or not gemini_key:
            st.error("Groq နှင့် Gemini API Key ထည့်ပေးပါ။")
        else:
            with st.spinner("Groq Whisper + Gemini 3.5 + Edge-TTS ဖြင့် ဘာသာပြန်ပြီး အသံထုတ်နေပါသည်..."):
                try:
                    v_temp = os.path.join(tempfile.gettempdir(), "s99_input.mp4")
                    with open(v_temp, "wb") as f:
                        f.write(ai_video_file.getbuffer())
                    _, _, _, vid_dur = get_video_info(v_temp)

                    ext_aud = extract_compressed_audio(v_temp)
                    groq_client = Groq(api_key=groq_key.strip())
                    with open(ext_aud, "rb") as f:
                        trans = groq_client.audio.transcriptions.create(
                            file=(ext_aud, f.read()),
                            model="whisper-large-v3-turbo",
                            response_format="verbose_json"
                        )
                    raw_segs = getattr(trans, "segments", None) or (trans.get("segments", []) if isinstance(trans, dict) else [])
                    segs = merge_close_whisper_segments(raw_segs)

                    gemini_client = genai.Client(api_key=gemini_key.strip())
                    translate_segments_recap_style(gemini_client, groq_client, gemini_model, segs, NARRATION_STYLES[narration_label])

                    v_cfg = VOICE_PRESETS[voice_label]
                    tts_res = asyncio.run(synthesize_all_tts(segs, v_cfg["voice"], f"{v_cfg['rate']:+d}%", f"{v_cfg['pitch']:+d}Hz"))
                    for idx, wav_p, tdur in tts_res:
                        segs[idx]["wav"] = wav_p
                        segs[idx]["tts_dur"] = tdur

                    # အသံနှင့် စာတန်းအချိန် တွက်ချက်ခြင်း
                    subs_list = []
                    audio_list_file = tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".txt").name
                    cursor = 0.0
                    with open(audio_list_file, "w", encoding="utf-8") as af:
                        for seg in segs:
                            s_start = max(cursor, seg["start"])
                            if s_start - cursor > 0.08:
                                sil = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
                                subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{s_start - cursor:.3f}", sil], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                af.write(f"file '{sil}'\n")
                                cursor = s_start

                            af.write(f"file '{seg['wav']}'\n")
                            dur = max(0.25, seg["tts_dur"])
                            short_lines = split_into_short_lines(seg["translated"], 22)
                            tot_c = sum(len(c) for c in short_lines) or 1
                            loc_c = 0.0
                            for c_idx, c_str in enumerate(short_lines):
                                c_dur = dur * (len(c_str) / tot_c) if c_idx < len(short_lines) - 1 else (dur - loc_c)
                                subs_list.append({"start": round(cursor + loc_c, 2), "end": round(cursor + loc_c + c_dur, 2), "text": c_str})
                                loc_c += c_dur
                            cursor += dur

                    combined_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
                    final_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
                    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", audio_list_file, "-c", "copy", combined_wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.run(["ffmpeg", "-y", "-i", combined_wav, "-af", "loudnorm=I=-14:TP=-1.0:LRA=11,volume=5dB", "-ar", "44100", "-b:a", "128k", final_mp3], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

                    with open(final_mp3, "rb") as mf:
                        st.session_state["tts_b64"] = base64.b64encode(mf.read()).decode("utf-8")
                    st.session_state["subs_timeline"] = subs_list
                    st.success(f"✅ မြန်မာစာတန်း ({len(subs_list)}) ကြောင်းနှင့် Voiceover အသံ အသင့်ဖြစ်ပါပြီ! အောက်က Local Studio တွင် တိုက်ရိုက် ချိန်ညှိနိုင်ပါပြီ။")
                except Exception as e:
                    st.error(f"Error: {e}")

# ==================== STEP 2: STUDIO99 INTERACTIVE LOCAL CANVAS ENGINE ====================
subs_json_str = json.dumps(st.session_state.get("subs_timeline", []), ensure_ascii=False)
local_html = build_studio99_local_engine_html(
    subs_json_str=subs_json_str,
    tts_audio_b64=st.session_state.get("tts_b64", ""),
    custom_font_b64=custom_font_b64
)
components.html(local_html, height=1180, scrolling=False)
