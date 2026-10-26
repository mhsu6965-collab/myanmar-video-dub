import os
import re
import json
import time
import asyncio
import subprocess
import tempfile
from io import BytesIO
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import streamlit as st
from groq import Groq
from google import genai
from google.genai import types
import edge_tts

st.set_page_config(
    page_title="RecapMM Studio",
    page_icon="🍊",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==================== RECAPMM DARK & ORANGE THEME CSS ====================
st.markdown("""
<style>
    .stApp {
        background-color: #0d0d0d;
        color: #f5f5f5;
    }
    .block-container {
        padding-top: 0.8rem;
        padding-bottom: 3rem;
        max-width: 520px;
    }
    .recap-topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.65rem 1rem;
        background: #141414;
        border-bottom: 1px solid #2a2a2a;
        border-radius: 12px;
        margin-bottom: 0.8rem;
    }
    .recap-logo {
        font-size: 1.35rem;
        font-weight: 800;
        color: #f97316;
        letter-spacing: -0.5px;
    }
    .recap-logo span {
        color: #ffffff;
    }
    .recap-badge {
        background: #1f1f1f;
        color: #d4d4d8;
        padding: 0.25rem 0.65rem;
        border-radius: 8px;
        font-size: 0.8rem;
        border: 1px solid #333;
    }
    .step-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 0.5rem 0 0.8rem 0;
    }
    .step-circle {
        background: #f97316;
        color: #000000;
        font-weight: 800;
        width: 26px;
        height: 26px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 0.85rem;
    }
    .step-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #ffffff;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #151210 !important;
        border: 1px solid #2e241d !important;
        border-radius: 16px !important;
        padding: 0.85rem !important;
        margin-bottom: 0.9rem !important;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #f97316 0%, #fb923c 100%) !important;
        color: #0f0f0f !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.65rem 1rem !important;
        box-shadow: 0 4px 14px rgba(249, 115, 22, 0.3) !important;
    }
    div.stButton > button[kind="secondary"] {
        background-color: #1f1b18 !important;
        color: #f3f4f6 !important;
        border: 1px solid #3d322c !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
    }
    div.stDownloadButton > button {
        background: linear-gradient(90deg, #f97316 0%, #fb923c 100%) !important;
        color: #0f0f0f !important;
        font-weight: 800 !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 1rem !important;
    }
</style>
""", unsafe_allow_html=True)

USER_FONT_DIR = os.path.expanduser("~/.local/share/fonts")
os.makedirs(USER_FONT_DIR, exist_ok=True)

# ဗီဒီယိုထဲကအတိုင်း အသံ (၆) မျိုး (မိန်းကလေး ၃၊ ယောက်ျားလေး ၃)
VOICE_PRESETS = {
    "မိန်းကလေး ၁ - တည်ငြိမ်": {"voice": "my-MM-NilarNeural", "rate": 0, "pitch": -2},
    "မိန်းကလေး ၂ - ပေါ့ပါး": {"voice": "my-MM-NilarNeural", "rate": 8, "pitch": 2},
    "မိန်းကလေး ၃ - နုပျို": {"voice": "my-MM-NilarNeural", "rate": 4, "pitch": 6},
    "ယောက်ျား ၁ - တက်ကြွ": {"voice": "my-MM-ThihaNeural", "rate": 10, "pitch": 2},
    "ယောက်ျား ၂ - လေးနက်": {"voice": "my-MM-ThihaNeural", "rate": 0, "pitch": -4},
    "ယောက်ျား ၃ - စိတ်လှုပ်ရှား": {"voice": "my-MM-ThihaNeural", "rate": 14, "pitch": 4}
}

NARRATION_STYLES = {
    "Direct Translation (မူရင်း POV နှင့် အဓိပ္ပာယ်ကို မပြောင်းဘဲ ဘာသာပြန်မယ်)": "direct",
    "Third Person (ပြင်ပဇာတ်ကြောင်းပြောသူအနေနဲ့ ဖြစ်စဉ်ကို ပြောမယ်)": "third_person",
    "First Person (အဓိကဇာတ်ကောင် ကိုယ်တိုင်ပြောသလို ပြောမယ်)": "first_person"
}

COLOR_PRESETS = {
    "⚪ အဖြူ": "#FFFFFF",
    "🟡 အဝါ": "#FFE600",
    "🔵 အပြာနု": "#38BDF8",
    "🌸 ပန်းရောင်": "#F472B6"
}

FONT_CHOICES = [
    "Noto Sans (မင်္ဂလာပါ)",
    "Padauk (မင်္ဂလာပါ)",
    "AJ 02 / Masterpiece (Custom .ttf)"
]

def hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16), alpha)
    return (255, 255, 255, alpha)

def clean_text_for_myanmar_font(text: str) -> str:
    """လေးထောင့်ကွက် (Tofu □) လုံးဝမပေါ်စေရန် စာလုံးပိုများ သန့်စင်ခြင်း"""
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

def register_uploaded_font(uploaded_file) -> str:
    if uploaded_file is None:
        return None
    dest_path = os.path.join(USER_FONT_DIR, uploaded_file.name)
    with open(dest_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    subprocess.run(["fc-cache", "-f", USER_FONT_DIR], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return dest_path

def find_font_path(font_choice: str, custom_font_path: str = None) -> str:
    if custom_font_path and os.path.exists(custom_font_path):
        return custom_font_path
    if "Padauk" in font_choice:
        res = subprocess.run(["fc-match", "-f", "%{file}", "Padauk"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.stdout.strip() and os.path.exists(res.stdout.strip()):
            return res.stdout.strip()
    res = subprocess.run(["fc-match", "-f", "%{file}", "Noto Sans Myanmar"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    fpath = res.stdout.strip()
    if fpath and os.path.exists(fpath):
        return fpath
    return "/usr/share/fonts/truetype/noto/NotoSansMyanmar-Bold.ttf"

def align_to_8(val: int) -> int:
    return max(16, int(round(val / 8.0)) * 8)

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
        return align_to_8(w), align_to_8(h), fps, dur
    except Exception:
        return 720, 1280, 30.0, 0.0

def calculate_target_resolution(orig_w: int, orig_h: int, res_choice: str) -> tuple:
    if "1080p" in res_choice:
        target_short = 1080
    elif "720p" in res_choice:
        target_short = 720
    else:
        return align_to_8(orig_w), align_to_8(orig_h)

    if orig_w <= orig_h:
        new_w = target_short
        new_h = int(round(orig_h * (target_short / float(orig_w))))
    else:
        new_h = target_short
        new_w = int(round(orig_w * (target_short / float(orig_h))))
    return align_to_8(new_w), align_to_8(new_h)

def get_media_duration(file_path: str) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(res.stdout.strip())
    except Exception:
        return 0.0

def format_mm_ss(seconds: float) -> str:
    seconds = max(0.0, seconds)
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"

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

@st.cache_data(show_spinner=False)
def extract_frame_bytes(video_path: str, time_sec: float, file_size: int) -> bytes:
    frame_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg").name
    subprocess.run(["ffmpeg", "-y", "-ss", f"{time_sec:.2f}", "-i", video_path, "-frames:v", "1", "-q:v", "2", frame_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(frame_file) and os.path.getsize(frame_file) > 0:
        with open(frame_file, "rb") as f:
            data = f.read()
        os.remove(frame_file)
        return data
    return b""

def render_myanmar_subtitle_rgba(
    text: str, font_path: str, size_scale_pct: int, vid_w: int,
    text_hex: str = "#38BDF8", pill_bg: bool = True
) -> Image.Image:
    """RecapMM စတိုင် အမည်းရောင် Pill ဘောင်အကြည်လေးနှင့် မြန်မာစာတန်းထိုး ပုံဖော်ခြင်း"""
    clean_txt = clean_text_for_myanmar_font(text) or " "
    base_pt = 20 * (size_scale_pct / 100.0)
    scaled_px = max(14, int(base_pt * (vid_w / 540.0)))
    try:
        font = ImageFont.truetype(font_path, scaled_px)
    except Exception:
        font = ImageFont.load_default()

    dummy_img = Image.new("RGBA", (10, 10))
    d_draw = ImageDraw.Draw(dummy_img)
    try:
        bbox = d_draw.textbbox((0, 0), clean_txt, font=font)
        tw, th = max(10, bbox[2] - bbox[0]), max(10, bbox[3] - bbox[1])
        offset_x, offset_y = -bbox[0], -bbox[1]
    except Exception:
        tw, th, offset_x, offset_y = 300, 40, 0, 0

    sp = max(2, int(round(2.2 * (vid_w / 720.0))))
    pad_x = int(18 * (vid_w / 720.0))
    pad_y = int(10 * (vid_w / 720.0))
    img_w = tw + (sp * 2) + (pad_x * 2)
    img_h = th + (sp * 2) + (pad_y * 2)

    canvas = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    if pill_bg:
        draw.rounded_rectangle(
            [2, 2, img_w - 2, img_h - 2],
            radius=int(img_h * 0.35),
            fill=(15, 15, 15, 165)
        )

    x_pos = pad_x + sp + offset_x
    y_pos = pad_y + sp + offset_y
    text_rgba = hex_to_rgba(text_hex, 255)

    for ox in range(-sp, sp + 1):
        for oy in range(-sp, sp + 1):
            if ox != 0 or oy != 0:
                draw.text((x_pos + ox, y_pos + oy), clean_txt, font=font, fill=(0, 0, 0, 255))

    draw.text((x_pos, y_pos), clean_txt, font=font, fill=text_rgba)

    max_allowed_w = int(vid_w * 0.94)
    if canvas.width > max_allowed_w:
        ratio = max_allowed_w / float(canvas.width)
        canvas = canvas.resize((max_allowed_w, max(12, int(canvas.height * ratio))), Image.LANCZOS)
    return canvas

def render_watermark_rgba(wm_text: str, font_path: str, wm_opacity_pct: int, wm_size_pct: int, vid_w: int) -> Image.Image:
    clean_wm = wm_text.strip()
    if not clean_wm:
        return None
    scaled_px = max(12, int(16 * (wm_size_pct / 100.0) * (vid_w / 540.0)))
    try:
        font = ImageFont.truetype(font_path, scaled_px)
    except Exception:
        font = ImageFont.load_default()

    dummy = Image.new("RGBA", (10, 10))
    d_draw = ImageDraw.Draw(dummy)
    bbox = d_draw.textbbox((0, 0), clean_wm, font=font)
    tw, th = max(10, bbox[2] - bbox[0]), max(10, bbox[3] - bbox[1])
    alpha_val = int(255 * (wm_opacity_pct / 100.0))

    canvas = Image.new("RGBA", (tw + 16, th + 12), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.text((8 - bbox[0], 6 - bbox[1]), clean_wm, font=font, fill=(255, 255, 255, alpha_val))
    return canvas

def generate_recapmm_preview(
    frame_bytes: bytes,
    enable_blur: bool,
    blur_y_pct: int,
    blur_h_pct: int,
    blur_w_pct: int,
    blur_opacity_pct: int,
    show_sub: bool,
    sub_y_pct: int,
    sample_text: str,
    font_path: str,
    sub_size_pct: int,
    sub_color_hex: str,
    enable_wm: bool,
    wm_text: str,
    wm_x_pct: int,
    wm_y_pct: int,
    wm_opacity_pct: int,
    wm_size_pct: int,
    mirror_vid: bool
):
    img = Image.open(BytesIO(frame_bytes)).convert("RGBA")
    if mirror_vid:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    iw, ih = img.size

    bx_w = max(16, int(iw * (blur_w_pct / 100.0)))
    bx_h = max(16, int(ih * (blur_h_pct / 100.0)))
    bx_x = (iw - bx_w) // 2
    bx_y = min(max(0, int(ih * (blur_y_pct / 100.0))), ih - bx_h)

    if enable_blur and blur_opacity_pct > 0:
        crop = img.crop((bx_x, bx_y, bx_x + bx_w, bx_y + bx_h))
        blurred = crop.filter(ImageFilter.GaussianBlur(radius=max(4, int(18 * (blur_opacity_pct / 100.0)))))
        # Blur ပေါ်တွင် မူရင်းစာသား လုံးဝမမြင်ရစေရန် Dark Tint နှင့် ပေါင်းစပ်ခြင်း
        dark_overlay = Image.new("RGBA", (bx_w, bx_h), (25, 25, 25, int(160 * (blur_opacity_pct / 100.0))))
        blurred = Image.alpha_composite(blurred.convert("RGBA"), dark_overlay)
        img.paste(blurred, (bx_x, bx_y))

        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle(
            [bx_x, bx_y, bx_x + bx_w, bx_y + bx_h],
            radius=10,
            outline=(249, 115, 22, 230),
            width=max(2, iw // 180)
        )

    if enable_wm and wm_text.strip():
        wm_rgba = render_watermark_rgba(wm_text, font_path, wm_opacity_pct, wm_size_pct, iw)
        if wm_rgba:
            wx = min(max(6, int((iw - wm_rgba.width) * (wm_x_pct / 100.0))), iw - wm_rgba.width - 6)
            wy = min(max(6, int((ih - wm_rgba.height) * (wm_y_pct / 100.0))), ih - wm_rgba.height - 6)
            img.alpha_composite(wm_rgba, (wx, wy))

    if show_sub:
        sub_rgba = render_myanmar_subtitle_rgba(sample_text, font_path, sub_size_pct, iw, sub_color_hex, pill_bg=True)
        sx = max(0, (iw - sub_rgba.width) // 2)
        sy = min(max(4, int(ih * (sub_y_pct / 100.0)) - (sub_rgba.height // 2)), ih - sub_rgba.height - 4)
        img.alpha_composite(sub_rgba, (sx, sy))

    return img.convert("RGB"), (bx_x, bx_y, bx_w, bx_h)

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
        style_instr = (
            "Rewrite and translate into natural Burmese (Myanmar) as a THIRD-PERSON movie recap narrator "
            "(ပြင်ပဇာတ်ကြောင်းပြောသူအနေဖြင့် ဖြစ်စဉ်ကို ပြောပြသည့်ပုံစံ). Keep each line concise."
        )
    elif style_mode == "first_person":
        style_instr = (
            "Rewrite and translate into natural Burmese (Myanmar) from a FIRST-PERSON perspective "
            "(အဓိကဇာတ်ကောင် ကိုယ်တိုင် 'ကျွန်တော်/ကျွန်မ' ဟု ပြောပြသည့်ပုံစံ). Keep each line concise."
        )
    else:
        style_instr = (
            "Translate directly and naturally into spoken Burmese (Myanmar) keeping the original POV and meaning "
            "(မူရင်း POV နှင့် အဓိပ္ပာယ် မပြောင်းဘဲ တိုက်ရိုက်ဘာသာပြန်ရန်). Keep each line concise."
        )

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

def render_recapmm_final_video(
    video_path: str,
    tts_audio_path: str,
    timeline: list,
    sub_overlays: list,
    vid_w: int,
    vid_h: int,
    vid_fps: float,
    enable_blur: bool,
    blur_box_norm: tuple,
    blur_opacity_pct: int,
    show_sub: bool,
    sub_y_pct: int,
    wm_rgba: Image.Image,
    wm_x_pct: int,
    wm_y_pct: int,
    mirror_vid: bool,
    zoom_pct: int,
    brightness_val: float,
    contrast_val: float,
    saturation_val: float,
    orig_vol_pct: int,
    vo_vol_pct: int,
    progress_bar
) -> str:
    """
    Resolution အကြည်လင်ဆုံးနှင့် MB ဖိုင်ဆိုဒ် အနည်းဆုံးဖြစ်စေမည့်
    Smart CRF-24 + Maxrate 2.2Mbps Bitrate-Constrained H.264 Engine
    """
    raw_out_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    web_ready_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name

    vf_chain = [f"fps={vid_fps:.2f}"]
    if mirror_vid:
        vf_chain.append("hflip")

    if zoom_pct > 100:
        zf = zoom_pct / 100.0
        vf_chain.append(f"scale=iw*{zf:.3f}:ih*{zf:.3f},crop=iw/{zf:.3f}:ih/{zf:.3f}")

    vf_chain.append(f"scale={vid_w}:{vid_h}:flags=bicubic,setsar=1")

    if abs(brightness_val) > 0.01 or abs(contrast_val - 1.0) > 0.01 or abs(saturation_val - 1.0) > 0.01:
        vf_chain.append(f"eq=brightness={brightness_val:.2f}:contrast={contrast_val:.2f}:saturation={saturation_val:.2f}")

    vf_chain.append("format=rgb24")
    base_vf_str = ",".join(vf_chain)

    bx_x, bx_y, bx_w, bx_h = blur_box_norm
    if enable_blur and blur_opacity_pct > 0 and bx_w >= 8 and bx_h >= 8:
        sigma_val = max(3.0, 22.0 * (blur_opacity_pct / 100.0))
        decode_vf = (
            f"{base_vf_str},split=2[vm][vc];"
            f"[vc]crop={bx_w}:{bx_h}:{bx_x}:{bx_y},gblur=sigma={sigma_val:.1f},"
            f" eq=brightness=-0.18:contrast=0.9[vb];"
            f"[vm][vb]overlay={bx_x}:{bx_y}"
        )
    else:
        decode_vf = base_vf_str

    sub_center_y = int(vid_h * (sub_y_pct / 100.0))

    decoder_cmd = ["ffmpeg", "-v", "error", "-i", video_path, "-vf", decode_vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]
    # MB ဖိုင်ဆိုဒ် အနည်းဆုံးနှင့် ရုပ်ထွက် အကြည်လင်ဆုံး ဖြစ်စေမည့် -preset veryfast -crf 24 -maxrate 2200k
    encoder_cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{vid_w}x{vid_h}", "-pix_fmt", "rgb24", "-r", f"{vid_fps:.2f}",
        "-i", "pipe:0",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
        "-maxrate", "2200k", "-bufsize", "4400k",
        "-profile:v", "main", "-pix_fmt", "yuv420p", "-threads", "2",
        raw_out_video
    ]

    dec_proc = subprocess.Popen(decoder_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    enc_proc = subprocess.Popen(encoder_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    frame_bytes_len = vid_w * vid_h * 3
    total_out_dur = sum(item["target_dur"] for item in timeline)
    total_out_frames = max(1, int(round(total_out_dur * vid_fps)))

    out_cursor = 0.0
    time_segments = []
    for item in timeline:
        td = max(0.02, item["target_dur"])
        time_segments.append({"out_start": out_cursor, "out_end": out_cursor + td, "in_start": item["v_start"], "in_end": item["v_end"]})
        out_cursor += td

    curr_in_frame_idx = -1
    curr_in_frame_bytes = None
    eof_reached = False
    seg_ptr = 0
    sub_ptr = 0
    num_subs = len(sub_overlays)
    frames_written = 0

    wx, wy = 0, 0
    if wm_rgba is not None:
        wx = min(max(6, int((vid_w - wm_rgba.width) * (wm_x_pct / 100.0))), vid_w - wm_rgba.width - 6)
        wy = min(max(6, int((vid_h - wm_rgba.height) * (wm_y_pct / 100.0))), vid_h - wm_rgba.height - 6)

    for out_idx in range(total_out_frames):
        t_out = out_idx / float(vid_fps)
        while seg_ptr < len(time_segments) - 1 and t_out >= time_segments[seg_ptr]["out_end"]:
            seg_ptr += 1
        seg = time_segments[seg_ptr]

        seg_out_dur = max(0.001, seg["out_end"] - seg["out_start"])
        ratio = min(1.0, max(0.0, (t_out - seg["out_start"]) / seg_out_dur))
        t_in = seg["in_start"] + ratio * (seg["in_end"] - seg["in_start"])
        target_in_idx = max(0, int(round(t_in * vid_fps)))

        while not eof_reached and curr_in_frame_idx < target_in_idx:
            raw = dec_proc.stdout.read(frame_bytes_len)
            if len(raw) < frame_bytes_len:
                eof_reached = True
                break
            curr_in_frame_bytes = raw
            curr_in_frame_idx += 1

        if curr_in_frame_bytes is None:
            break

        active_sub = None
        if show_sub:
            while sub_ptr < num_subs and sub_overlays[sub_ptr]["end"] < t_out:
                sub_ptr += 1
            if sub_ptr < num_subs and sub_overlays[sub_ptr]["start"] <= t_out <= sub_overlays[sub_ptr]["end"]:
                active_sub = sub_overlays[sub_ptr]

        if active_sub is not None or wm_rgba is not None:
            frame_img = Image.frombytes("RGB", (vid_w, vid_h), curr_in_frame_bytes)
            if wm_rgba is not None:
                frame_img.paste(wm_rgba, (wx, wy), wm_rgba)
            if active_sub is not None:
                sub_rgba = active_sub["img"]
                ox = max(0, (vid_w - sub_rgba.width) // 2)
                oy = min(max(4, sub_center_y - (sub_rgba.height // 2)), vid_h - sub_rgba.height - 4)
                frame_img.paste(sub_rgba, (ox, oy), sub_rgba)
            frame_to_write = frame_img.tobytes()
        else:
            frame_to_write = curr_in_frame_bytes

        try:
            enc_proc.stdin.write(frame_to_write)
            frames_written += 1
        except BrokenPipeError:
            break

        if out_idx % 25 == 0:
            progress_bar.progress(min(0.95, out_idx / float(total_out_frames)))

    try:
        if enc_proc.stdin:
            enc_proc.stdin.close()
    except Exception:
        pass
    try:
        if dec_proc.stdout:
            dec_proc.stdout.close()
    except Exception:
        pass

    dec_err = dec_proc.stderr.read().decode("utf-8", errors="ignore") if dec_proc.stderr else ""
    enc_err = enc_proc.stderr.read().decode("utf-8", errors="ignore") if enc_proc.stderr else ""
    dec_proc.wait()
    enc_proc.wait()

    if frames_written == 0 or not os.path.exists(raw_out_video) or os.path.getsize(raw_out_video) < 1000:
        raise RuntimeError(f"Video Render မအောင်မြင်ပါ:\nDecoder: {dec_err}\nEncoder: {enc_err}")

    # မူရင်း Video အသံနှင့် Voiceover အသံ ရောစပ်ခြင်း (128k AAC ဖြင့် ဖိုင်ဆိုဒ်ချုံ့သည်)
    vo_gain = max(0.1, vo_vol_pct / 100.0)
    if orig_vol_pct > 0:
        orig_gain = orig_vol_pct / 100.0
        af_mix = f"[1:a]volume={vo_gain:.2f}[vo];[2:a]volume={orig_gain:.2f}[oa];[vo][oa]amix=inputs=2:duration=first:normalize=0[aout]"
        mux_cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-i", raw_out_video, "-i", tts_audio_path, "-i", video_path,
            "-filter_complex", af_mix,
            "-map", "0:v:0", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart", "-shortest", web_ready_video
        ]
        res = subprocess.run(mux_cmd)
        if res.returncode != 0:
            subprocess.run([
                "ffmpeg", "-y", "-v", "error",
                "-i", raw_out_video, "-i", tts_audio_path,
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart", "-shortest", web_ready_video
            ], check=True)
    else:
        subprocess.run([
            "ffmpeg", "-y", "-v", "error",
            "-i", raw_out_video, "-i", tts_audio_path,
            "-af", f"volume={vo_gain:.2f}",
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart", "-shortest", web_ready_video
        ], check=True)

    if os.path.exists(raw_out_video):
        os.remove(raw_out_video)
    progress_bar.progress(1.0)
    return web_ready_video

# ==================== SIDEBAR (API KEYS) ====================
with st.sidebar:
    st.markdown("### 🔑 API Keys Settings")
    default_groq = st.secrets.get("GROQ_API_KEY", "") if "GROQ_API_KEY" in st.secrets else ""
    default_gemini = st.secrets.get("GEMINI_API_KEY", "") if "GEMINI_API_KEY" in st.secrets else ""
    groq_key = st.text_input("Groq API Key", value=default_groq, type="password")
    gemini_key = st.text_input("Gemini API Key", value=default_gemini, type="password")
    gemini_model = st.selectbox("Gemini Model", ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-3.1-flash-lite-preview", "gemini-2.5-flash"])
    res_choice = st.selectbox("Video Resolution", ["720p HD (ဖိုင်ဆိုဒ်သေး & အကြည်လင်ဆုံး)", "Original Resolution", "1080p Full HD"])
    uploaded_font = st.file_uploader("Custom Font (.ttf) တင်ရန်", type=["ttf", "otf"])
    custom_font_path = register_uploaded_font(uploaded_font)

# ==================== TOP BAR & VIDEO UPLOAD ====================
uploaded_video = st.file_uploader("📁 Recap ပြုလုပ်မည့် Video ဖိုင်ရွေးပါ", type=["mp4", "mov", "mkv", "webm"])

if "enable_blur" not in st.session_state:
    st.session_state["enable_blur"] = True
if "script_segments" not in st.session_state:
    st.session_state["script_segments"] = []

video_temp_path = None
orig_w, orig_h, vid_fps, vid_dur = 720, 1280, 30.0, 0.0

if uploaded_video:
    video_temp_path = os.path.join(tempfile.gettempdir(), "input_source_video.mp4")
    with open(video_temp_path, "wb") as f:
        f.write(uploaded_video.getbuffer())
    orig_w, orig_h, vid_fps, vid_dur = get_video_info(video_temp_path)

st.markdown(f"""
<div class="recap-topbar">
    <div class="recap-logo">Recap<span>MM</span></div>
    <div class="recap-badge">ကြာချိန် {format_mm_ss(vid_dur)}</div>
</div>
""", unsafe_allow_html=True)

if not default_groq or not default_gemini:
    with st.expander("🔑 API Keys ထည့်သွင်းရန် (နှိပ်၍ဖွင့်ပါ)", expanded=not (groq_key and gemini_key)):
        groq_key = st.text_input("Groq API Key (gsk_...)", value=groq_key, type="password", key="main_groq")
        gemini_key = st.text_input("Gemini API Key (AIzaSy...)", value=gemini_key, type="password", key="main_gemini")

# ==================== TOP PREVIEW & BLUR BOX CARD ====================
if video_temp_path:
    with st.container(border=True):
        preview_placeholder = st.empty()
        preview_sec = st.slider("⏱️ Video အချိန်ရွှေ့ကြည့်ရန်", 0.0, max(1.0, float(vid_dur)), min(2.0, float(vid_dur)), 0.5)

        b_col1, b_col2 = st.columns(2)
        if b_col1.button("＋ စာတန်း Blur ထည့်မယ်", use_container_width=True):
            st.session_state["enable_blur"] = True
        if b_col2.button("🗑️ Blur အားလုံးဖျက်", use_container_width=True):
            st.session_state["enable_blur"] = False

        blur_opacity_pct = st.slider("Blur အထူ (Opacity %)", 0, 100, 100 if st.session_state["enable_blur"] else 0, 5)
        with st.expander("📐 Blur အကွက် နှင့် စာတန်းနေရာ အသေးစိတ်ရွှေ့ရန်", expanded=False):
            c_b1, c_b2, c_b3 = st.columns(3)
            blur_y_pct = c_b1.slider("Blur အပေါ်/အောက်", 5, 95, 76, 1)
            blur_h_pct = c_b2.slider("Blur အမြင့်", 4, 30, 11, 1)
            blur_w_pct = c_b3.slider("Blur အကျယ်", 30, 100, 90, 2)
            sub_y_pct = st.slider("မြန်မာစာတန်း အပေါ်/အောက် နေရာ (%)", 10, 95, 76, 1)
else:
    blur_opacity_pct, blur_y_pct, blur_h_pct, blur_w_pct, sub_y_pct = 100, 76, 11, 90, 76

# ==================== CARD 1: မြန်မာဘာသာပြန် SCRIPT ====================
with st.container(border=True):
    st.markdown("""
    <div class="step-header">
        <div class="step-circle">1</div>
        <div class="step-title">မြန်မာဘာသာပြန် Script</div>
    </div>
    """, unsafe_allow_html=True)

    narration_label = st.radio("ဇာတ်ကြောင်းပုံစံ", list(NARRATION_STYLES.keys()), index=0)
    style_mode = NARRATION_STYLES[narration_label]

    if st.button("🪄 Script ပြန်ထုတ်မယ်", type="primary", use_container_width=True):
        if not video_temp_path:
            st.error("Video အရင်တင်ပေးပါ။")
        elif not groq_key or not gemini_key:
            st.error("Groq နှင့် Gemini API Key နှစ်ခုလုံး ထည့်ပေးပါ။")
        else:
            with st.spinner("Groq Whisper + Gemini 3.5 ဖြင့် မြန်မာ Script ထုတ်နေပါသည်..."):
                try:
                    extracted_audio = extract_compressed_audio(video_temp_path)
                    groq_client = Groq(api_key=groq_key.strip())
                    with open(extracted_audio, "rb") as f:
                        trans = groq_client.audio.transcriptions.create(
                            file=(extracted_audio, f.read()),
                            model="whisper-large-v3-turbo",
                            response_format="verbose_json"
                        )
                    raw_segs = getattr(trans, "segments", None) or (trans.get("segments", []) if isinstance(trans, dict) else [])
                    segs = merge_close_whisper_segments(raw_segs)
                    gemini_client = genai.Client(api_key=gemini_key.strip())
                    translate_segments_recap_style(gemini_client, groq_client, gemini_model, segs, style_mode)
                    st.session_state["script_segments"] = segs
                    st.rerun()
                except Exception as e:
                    st.error(f"Script ထုတ်ရာတွင် Error ဖြစ်ပွားပါသည်: {e}")

    segs_list = st.session_state.get("script_segments", [])
    if segs_list:
        h_c1, h_c2 = st.columns([1.4, 1])
        h_c1.caption(f"စာကြောင်း {len(segs_list)} | ပြင်ချင်တာ ပြင်နိုင်ပါတယ်")
        if h_c2.button("＋ စာကြောင်းထည့်", use_container_width=True):
            last_end = segs_list[-1]["end"] if segs_list else 0.0
            segs_list.append({"start": last_end, "end": last_end + 3.0, "text": "", "translated": "စာကြောင်းအသစ်"})
            st.session_state["script_segments"] = segs_list
            st.rerun()

        with st.expander("📝 စာကြောင်းများ ကြည့်ရန် / ပြင်ဆင်ရန် (နှိပ်၍ဖွင့်ပါ)", expanded=True):
            to_delete = None
            for idx, seg in enumerate(segs_list):
                t_label = f"{format_mm_ss(seg['start'])} - {format_mm_ss(seg['end'])}"
                r_c1, r_c2 = st.columns([5, 1])
                new_txt = r_c1.text_area(
                    t_label,
                    value=seg["translated"],
                    height=68,
                    key=f"seg_edit_{idx}"
                )
                st.session_state["script_segments"][idx]["translated"] = new_txt
                if r_c2.button("🗑️", key=f"del_seg_{idx}"):
                    to_delete = idx
            if to_delete is not None:
                st.session_state["script_segments"].pop(to_delete)
                st.rerun()

# ==================== CARD 2: VOICEOVER အသံရွေးပါ ====================
with st.container(border=True):
    st.markdown("""
    <div class="step-header">
        <div class="step-circle">2</div>
        <div class="step-title">Voiceover အသံရွေးပါ</div>
    </div>
    """, unsafe_allow_html=True)

    selected_voice_preset = st.radio("အသံအမျိုးအစား (၆ မျိုး)", list(VOICE_PRESETS.keys()), index=4)
    v_cfg = VOICE_PRESETS[selected_voice_preset]

    with st.expander("🎛️ TTS Speed နှင့် Pitch အသေးစိတ် ထပ်ချိန်ရန်", expanded=False):
        extra_speed = st.slider("အသံ အမြန်/အနှေး (%)", -50, 80, v_cfg["rate"], 5)
        extra_pitch = st.slider("အသံ အမြင့်/အနိမ့် (Hz)", -30, 30, v_cfg["pitch"], 2)

    audio_offset_sec = st.slider(
        "အသံ အစော / အနောက် ချိန် (စက္ကန့်)",
        -2.0, 2.0, 0.0, 0.1,
        help="အသံက ပုံထက်စောနေရင် + ဘက်၊ နောက်ကျနေရင် - ဘက် ရွှေ့ပါ။ စာတန်းလည်း လိုက်ပြောင်းပါမယ်။"
    )

# ==================== CARD 3: VIDEO ချိန်ညှိမှု ====================
with st.container(border=True):
    st.markdown("""
    <div class="step-header">
        <div class="step-circle">3</div>
        <div class="step-title">Video ချိန်ညှိမှု</div>
    </div>
    """, unsafe_allow_html=True)

    mirror_vid = st.toggle("ဘယ်ညာ ပြောင်းပြန်လှည့် (Mirror - Copyright ကာကွယ်ရန်)", value=False)
    show_sub = st.toggle("မြန်မာစာတန်း video ထဲ ထည့်မယ်", value=True)

    font_choice = st.selectbox("ဖောင့် ရွေးချယ်ရန်", FONT_CHOICES, index=0)
    active_font_path = find_font_path(font_choice, custom_font_path)

    color_label = st.radio("စာလုံးအရောင်", list(COLOR_PRESETS.keys()), index=2, horizontal=True)
    sub_color_hex = COLOR_PRESETS[color_label]

    sub_size_pct = st.slider("စာလုံးအရွယ် (%)", 60, 140, 90, 5)

    st.divider()
    enable_wm = st.toggle("Channel Watermark ထည့်မယ်", value=True)
    if enable_wm:
        wm_text = st.text_input("Channel အမည်", value="MY RECAP")
        w_c1, w_c2 = st.columns(2)
        wm_opacity_pct = w_c1.slider("Watermark Opacity (%)", 10, 100, 50, 5)
        wm_size_pct = w_c2.slider("Watermark စာလုံးအရွယ် (%)", 50, 150, 95, 5)
        w_p1, w_p2 = st.columns(2)
        wm_x_pct = w_p1.slider("Watermark ဘယ်/ညာ (%)", 2, 98, 88, 2)
        wm_y_pct = w_p2.slider("Watermark အပေါ်/အောက် (%)", 2, 95, 6, 2)
    else:
        wm_text, wm_opacity_pct, wm_size_pct, wm_x_pct, wm_y_pct = "", 50, 95, 88, 6

    st.divider()
    with st.expander("🎨 Copyright ကာကွယ်ရေး (Zoom / အလင်း / Contrast / အသံ)", expanded=False):
        zoom_pct = st.slider("Zoom (%)", 100, 130, 100, 2)
        brightness_val = st.slider("အလင်း (Brightness)", -0.3, 0.3, 0.0, 0.02)
        contrast_val = st.slider("Contrast", 0.7, 1.4, 1.0, 0.05)
        saturation_val = st.slider("အရောင် (Saturation)", 0.5, 1.5, 1.0, 0.05)
        orig_vol_pct = st.slider("မူရင်းအသံ (%)", 0, 50, 0, 5)
        vo_vol_pct = st.slider("Voiceover အသံ (%)", 50, 200, 120, 10)

# Live Preview ပုံကို အပေါ်ဆုံး Card ထဲသို့ ပြန်ထည့်ပေးခြင်း
if video_temp_path:
    frame_bytes = extract_frame_bytes(video_temp_path, preview_sec, os.path.getsize(video_temp_path))
    if frame_bytes:
        sample_sub_txt = st.session_state["script_segments"][0]["translated"] if st.session_state.get("script_segments") else "ပြန်စရာအိမ်မရှိတော့တဲ့"
        prev_img, norm_blur_box = generate_recapmm_preview(
            frame_bytes=frame_bytes,
            enable_blur=st.session_state["enable_blur"],
            blur_y_pct=blur_y_pct,
            blur_h_pct=blur_h_pct,
            blur_w_pct=blur_w_pct,
            blur_opacity_pct=blur_opacity_pct,
            show_sub=show_sub,
            sub_y_pct=sub_y_pct,
            sample_text=sample_sub_txt,
            font_path=active_font_path,
            sub_size_pct=sub_size_pct,
            sub_color_hex=sub_color_hex,
            enable_wm=enable_wm,
            wm_text=wm_text,
            wm_x_pct=wm_x_pct,
            wm_y_pct=wm_y_pct,
            wm_opacity_pct=wm_opacity_pct,
            wm_size_pct=wm_size_pct,
            mirror_vid=mirror_vid
        )
        preview_placeholder.image(prev_img, use_container_width=True)

# ==================== CARD 4: ထုတ်ယူမယ် ====================
with st.container(border=True):
    st.markdown("""
    <div class="step-header">
        <div class="step-circle">4</div>
        <div class="step-title">ထုတ်ယူမယ်</div>
    </div>
    """, unsafe_allow_html=True)

    render_btn = st.button("📥 Recap Video ထုတ်မယ်", type="primary", use_container_width=True)

    if render_btn:
        if not video_temp_path:
            st.error("ကျေးဇူးပြု၍ Video ဖိုင် အရင် Upload တင်ပေးပါ။")
        elif not groq_key or not gemini_key:
            st.error("Groq နှင့် Gemini API Key နှစ်ခုလုံး ထည့်ပေးပါ။")
        else:
            status = st.status("⏳ Recap Video စတင်ထုတ်လုပ်နေပါသည်...", expanded=True)
            try:
                vid_w, vid_h = calculate_target_resolution(orig_w, orig_h, res_choice)

                # အကယ်၍ Script မထုတ်ရသေးဘဲ တိုက်ရိုက်နှိပ်ပါက အလိုအလျောက် Script အရင်ထုတ်ပေးမည်
                if not st.session_state.get("script_segments"):
                    status.write("🎧 ၁/၄ - Groq Whisper + Gemini 3.5 ဖြင့် Script ထုတ်ယူနေပါသည်...")
                    extracted_audio = extract_compressed_audio(video_temp_path)
                    groq_client = Groq(api_key=groq_key.strip())
                    with open(extracted_audio, "rb") as f:
                        trans = groq_client.audio.transcriptions.create(
                            file=(extracted_audio, f.read()),
                            model="whisper-large-v3-turbo",
                            response_format="verbose_json"
                        )
                    raw_segs = getattr(trans, "segments", None) or (trans.get("segments", []) if isinstance(trans, dict) else [])
                    segs = merge_close_whisper_segments(raw_segs)
                    gemini_client = genai.Client(api_key=gemini_key.strip())
                    translate_segments_recap_style(gemini_client, groq_client, gemini_model, segs, style_mode)
                    st.session_state["script_segments"] = segs

                segments = st.session_state["script_segments"]

                status.write("🗣️ ၂/၄ - Voiceover အသံများ ထုတ်ယူနေပါသည်...")
                tts_res = asyncio.run(
                    synthesize_all_tts(segments, v_cfg["voice"], f"{int(extra_speed):+d}%", f"{int(extra_pitch):+d}Hz")
                )
                for idx, wav_p, tdur in tts_res:
                    segments[idx]["wav"] = wav_p
                    segments[idx]["tts_dur"] = tdur

                status.write("📝 ၃/၄ - မြန်မာစာတန်းထိုးနှင့် အသံ Timing ချိန်ညှိနေပါသည်...")
                timeline, cursor = [], 0.0
                for seg in segments:
                    s_start = max(cursor, seg["start"] + audio_offset_sec)
                    s_end = max(s_start + 0.1, seg["end"] + audio_offset_sec)
                    if s_start - cursor > 0.08:
                        timeline.append({"type": "gap", "v_start": cursor, "v_end": s_start, "target_dur": s_start - cursor})
                    timeline.append({
                        "type": "speech", "v_start": s_start, "v_end": s_end,
                        "target_dur": max(0.25, seg["tts_dur"]), "wav": seg["wav"], "text": seg["translated"]
                    })
                    cursor = s_end
                if vid_dur - cursor > 0.08:
                    timeline.append({"type": "gap", "v_start": cursor, "v_end": vid_dur, "target_dur": vid_dur - cursor})

                srt_blocks, sub_overlays, srt_counter, new_time_cursor = [], [], 1, 0.0
                audio_list_file = tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".txt").name
                with open(audio_list_file, "w", encoding="utf-8") as af:
                    for item in timeline:
                        dur = item["target_dur"]
                        if item["type"] == "gap":
                            sil = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
                            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{dur:.3f}", sil], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            af.write(f"file '{sil}'\n")
                        else:
                            af.write(f"file '{item['wav']}'\n")
                            short_lines = split_into_short_lines(item["text"], 22)
                            tot_c = sum(len(c) for c in short_lines) or 1
                            loc_c = 0.0
                            for c_idx, c_str in enumerate(short_lines):
                                c_dur = dur * (len(c_str) / tot_c) if c_idx < len(short_lines) - 1 else (dur - loc_c)
                                st_time = new_time_cursor + loc_c
                                et_time = st_time + c_dur
                                srt_blocks.append(f"{srt_counter}\n{format_srt_time(st_time)} --> {format_srt_time(et_time)}\n{c_str}\n")
                                srt_counter += 1
                                sub_rgba = render_myanmar_subtitle_rgba(
                                    c_str, active_font_path, int(sub_size_pct), vid_w, sub_color_hex, pill_bg=True
                                )
                                sub_overlays.append({"img": sub_rgba, "start": st_time, "end": et_time})
                                loc_c += c_dur
                        new_time_cursor += dur

                srt_content = "\n".join(srt_blocks)
                combined_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
                final_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
                subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", audio_list_file, "-c", "copy", combined_wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run([
                    "ffmpeg", "-y", "-i", combined_wav,
                    "-af", "loudnorm=I=-14:TP=-1.0:LRA=11,volume=5dB",
                    "-ar", "44100", "-b:a", "128k", final_audio
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

                status.write(f"🎞️ ၄/၄ - HD Video ({vid_w}x{vid_h}) ကို MB ဖိုင်ဆိုဒ်အနည်းဆုံးဖြင့် ပေါင်းစပ်နေပါသည်...")
                p_bar = st.progress(0.0)

                bx_w = max(16, int(vid_w * (blur_w_pct / 100.0)))
                bx_h = max(16, int(vid_h * (blur_h_pct / 100.0)))
                bx_x = (vid_w - bx_w) // 2
                bx_y = min(max(0, int(vid_h * (blur_y_pct / 100.0))), vid_h - bx_h)

                wm_rgba = render_watermark_rgba(wm_text, active_font_path, wm_opacity_pct, wm_size_pct, vid_w) if enable_wm else None

                out_video_path = render_recapmm_final_video(
                    video_path=video_temp_path,
                    tts_audio_path=final_audio,
                    timeline=timeline,
                    sub_overlays=sub_overlays,
                    vid_w=vid_w,
                    vid_h=vid_h,
                    vid_fps=vid_fps,
                    enable_blur=st.session_state["enable_blur"],
                    blur_box_norm=(bx_x, bx_y, bx_w, bx_h),
                    blur_opacity_pct=blur_opacity_pct,
                    show_sub=show_sub,
                    sub_y_pct=sub_y_pct,
                    wm_rgba=wm_rgba,
                    wm_x_pct=wm_x_pct,
                    wm_y_pct=wm_y_pct,
                    mirror_vid=mirror_vid,
                    zoom_pct=zoom_pct,
                    brightness_val=brightness_val,
                    contrast_val=contrast_val,
                    saturation_val=saturation_val,
                    orig_vol_pct=orig_vol_pct,
                    vo_vol_pct=vo_vol_pct,
                    progress_bar=p_bar
                )

                with open(out_video_path, "rb") as vf:
                    v_bytes = vf.read()
                st.session_state["final_video_bytes"] = v_bytes
                st.session_state["final_srt_content"] = srt_content
                st.session_state["final_mb_size"] = len(v_bytes) / (1024 * 1024)

                status.update(label="✅ Recap Video အောင်မြင်စွာ ထုတ်ပြီးပါပြီ!", state="complete", expanded=False)

            except Exception as e:
                status.update(label="❌ Error ဖြစ်ပွားပါသည်", state="error")
                st.error(f"Error အသေးစိတ်: {e}")

    if "final_srt_content" in st.session_state and st.session_state["final_srt_content"]:
        st.download_button(
            "📄 မြန်မာ SRT Download",
            data=st.session_state["final_srt_content"],
            file_name="recap_myanmar.srt",
            mime="text/plain",
            use_container_width=True
        )

    if "final_video_bytes" in st.session_state and st.session_state["final_video_bytes"]:
        mb_val = st.session_state.get("final_mb_size", 0.0)
        st.video(st.session_state["final_video_bytes"], format="video/mp4")
        st.download_button(
            f"📥 MP4 Download ({mb_val:.1f} MB)",
            data=st.session_state["final_video_bytes"],
            file_name="RecapMM_Video.mp4",
            mime="video/mp4",
            use_container_width=True
    )
