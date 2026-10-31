import os
import re
import json
import time
import asyncio
import subprocess
import tempfile
import traceback
import urllib.request
from io import BytesIO
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import streamlit as st
from streamlit_cropper import st_cropper
from groq import Groq
from google import genai
from google.genai import types
import edge_tts

st.set_page_config(
    page_title="RecapMM Studio (Light UI)",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==================== SOFT LIGHT PASTEL THEME CSS ====================
st.markdown("""
<style>
    .stApp {
        background-color: #F1F5F9 !important;
        color: #0F172A !important;
    }
    .block-container {
        padding-top: 0.8rem;
        padding-bottom: 3rem;
        max-width: 520px;
    }
    p, span, label, div[data-testid="stMarkdownContainer"] p {
        color: #1E293B !important;
    }
    .recap-topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 1.1rem;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        margin-bottom: 0.9rem;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
    }
    .recap-logo {
        font-size: 1.35rem;
        font-weight: 800;
        color: #EA580C;
        letter-spacing: -0.5px;
    }
    .recap-logo span {
        color: #0F172A;
    }
    .recap-badge {
        background: #FFF7ED;
        color: #C2410C !important;
        font-weight: 600;
        padding: 0.25rem 0.7rem;
        border-radius: 8px;
        font-size: 0.82rem;
        border: 1px solid #FFEDD5;
    }
    .step-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 0.3rem 0 0.7rem 0;
    }
    .step-circle {
        background: #EA580C;
        color: #FFFFFF !important;
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
        font-size: 1.08rem;
        font-weight: 700;
        color: #0F172A !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 16px !important;
        padding: 0.95rem !important;
        margin-bottom: 0.95rem !important;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04) !important;
    }
    input, textarea, div[data-baseweb="select"] > div {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
        border-color: #CBD5E1 !important;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #EA580C 0%, #F97316 100%) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.65rem 1rem !important;
        box-shadow: 0 4px 12px rgba(234, 88, 12, 0.25) !important;
    }
    div.stButton > button[kind="primary"] p {
        color: #FFFFFF !important;
    }
    div.stButton > button[kind="secondary"] {
        background-color: #F1F5F9 !important;
        color: #0F172A !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
    }
    div.stDownloadButton > button {
        background: linear-gradient(90deg, #0284C7 0%, #0EA5E9 100%) !important;
        color: #FFFFFF !important;
        font-weight: 800 !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 1rem !important;
    }
    div.stDownloadButton > button p {
        color: #FFFFFF !important;
    }
    iframe[title="streamlit_cropper.st_cropper"] {
        display: block;
        margin: 0 auto;
        border-radius: 10px;
        border: 2px solid #94A3B8;
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

POSTER_COLOR_PRESETS = {
    "🟡 ရွှေဝါရောင် (Gold Poster)": ("#FFD700", "#FFFBEB"),
    "⚪ အဖြူရောင် (Classic White)": ("#FFFFFF", "#E2E8F0"),
    "🔴 အနီရောင် (Action Crimson)": ("#FF3B30", "#FFFFFF"),
    "🔵 အပြာနုရောင် (Sci-Fi Cyan)": ("#38BDF8", "#FFFFFF")
}

FONT_CHOICES = [
    "Noto Sans (မင်္ဂလာပါ)",
    "Noto Serif (မင်္ဂလာပါ - Movie Poster ဖောင့်)",
    "Padauk (မင်္ဂလာပါ)",
    "AJ 02 / Masterpiece (Custom .ttf)"
]

THUMBNAIL_ASPECT_RATIOS = {
    "📱 TikTok & Reels (9:16 - ဒေါင်လိုက်)": "9:16",
    "📺 YouTube (16:9 - အလျားလိုက်)": "16:9",
    "🎞️ မူရင်း Video အချိုးအတိုင်း": "orig"
}

def hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16), alpha)
    return (255, 255, 255, alpha)

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
    text = re.sub(r"[^\u1000-\u109F\uAA60-\uAA7F\uA9E0-\uA9FFa-zA-Z0-9\s,\.\!\?\(\)\-\+/\:]", "", text)
    return re.sub(r"\s+", " ", text).strip()

def register_uploaded_font(uploaded_file) -> str:
    if uploaded_file is None:
        return None
    dest_path = os.path.join(USER_FONT_DIR, uploaded_file.name)
    with open(dest_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    subprocess.run(["fc-cache", "-f", USER_FONT_DIR], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return dest_path

@st.cache_resource(show_spinner=False)
def ensure_noto_serif_myanmar() -> str:
    system_paths = [
        "/usr/share/fonts/truetype/noto/NotoSerifMyanmar-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSerifMyanmar-Regular.ttf",
        os.path.join(USER_FONT_DIR, "NotoSerifMyanmar-Bold.ttf")
    ]
    for p in system_paths:
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            return p

    res = subprocess.run(["fc-match", "-f", "%{file}", "Noto Serif Myanmar:style=Bold"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    matched = res.stdout.strip()
    if matched and os.path.exists(matched) and "Serif" in matched:
        return matched

    local_dest = os.path.join(USER_FONT_DIR, "NotoSerifMyanmar-Bold.ttf")
    try:
        url = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSerifMyanmar/NotoSerifMyanmar-Bold.ttf"
        urllib.request.urlretrieve(url, local_dest)
        if os.path.exists(local_dest) and os.path.getsize(local_dest) > 1000:
            subprocess.run(["fc-cache", "-f", USER_FONT_DIR], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return local_dest
    except Exception:
        pass
    return "/usr/share/fonts/truetype/noto/NotoSansMyanmar-Bold.ttf"

def find_font_path(font_choice: str, custom_font_path: str = None) -> str:
    if "Custom" in font_choice and custom_font_path and os.path.exists(custom_font_path):
        return custom_font_path
    if "Noto Serif" in font_choice:
        return ensure_noto_serif_myanmar()
    if "Padauk" in font_choice:
        res = subprocess.run(["fc-match", "-f", "%{file}", "Padauk:style=Bold"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.stdout.strip() and os.path.exists(res.stdout.strip()):
            return res.stdout.strip()
    if custom_font_path and os.path.exists(custom_font_path):
        return custom_font_path
    res = subprocess.run(["fc-match", "-f", "%{file}", "Noto Sans Myanmar:style=Bold"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
    res = subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-vn", "-ac", "1", "-ar", "16000", "-b:a", "48k", temp_audio],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if res.returncode != 0 or not os.path.exists(temp_audio) or os.path.getsize(temp_audio) < 100:
        raise RuntimeError(f"Video ထဲမှ အသံထုတ်ယူမရပါ (Video တွင် အသံပါ/မပါ စစ်ဆေးပါ):\n{res.stderr}")
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

def crop_and_resize_to_aspect(img: Image.Image, aspect_code: str) -> Image.Image:
    """ပုံကို YouTube (16:9) သို့မဟုတ် TikTok/Reels (9:16) အချိုးသို့ Smart Center Crop ဖြတ်ပေးခြင်း"""
    w, h = img.size
    if aspect_code == "16:9":
        target_w, target_h = 1280, 720
    elif aspect_code == "9:16":
        target_w, target_h = 720, 1280
    else:
        target_w = 720 if w <= h else 1280
        target_h = int(round(h * (target_w / float(w))))
        return img.resize((target_w, target_h), Image.LANCZOS)

    target_ratio = target_w / float(target_h)
    src_ratio = w / float(h)

    if abs(src_ratio - target_ratio) > 0.02:
        if src_ratio > target_ratio:
            new_w = int(round(h * target_ratio))
            left = (w - new_w) // 2
            img = img.crop((left, 0, left + new_w, h))
        else:
            new_h = int(round(w / target_ratio))
            top = int((h - new_h) * 0.35) # မျက်နှာများ မပြတ်စေရန် အပေါ်ပိုင်း 35% ကို ဦးစားပေးဖြတ်သည်
            img = img.crop((0, top, w, top + new_h))

    return img.resize((target_w, target_h), Image.LANCZOS)

def wrap_poster_title_lines(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
    raw_lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not raw_lines:
        return []
    dummy = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    final_lines = []

    for rline in raw_lines:
        clean_l = clean_text_for_myanmar_font(rline) or rline
        try:
            bbox = dummy.textbbox((0, 0), clean_l, font=font)
            line_w = bbox[2] - bbox[0]
        except Exception:
            line_w = len(clean_l) * 20

        if line_w <= max_width:
            final_lines.append(clean_l)
        else:
            tokens = re.split(r"(\s+|[၊။])", clean_l)
            curr = ""
            for tk in tokens:
                if not tk:
                    continue
                test_str = (curr + tk).strip()
                try:
                    tb = dummy.textbbox((0, 0), test_str, font=font)
                    tw = tb[2] - tb[0]
                except Exception:
                    tw = len(test_str) * 20
                if tw <= max_width:
                    curr = test_str
                else:
                    if curr:
                        final_lines.append(curr)
                    curr = tk.strip()
            if curr:
                final_lines.append(curr)
    return final_lines[:3]

def render_movie_poster_thumbnail(
    frame_bytes: bytes,
    title_text: str,
    subtitle_tag: str,
    font_path: str,
    primary_hex: str,
    secondary_hex: str,
    aspect_code: str = "9:16",
    title_size_pct: int = 100,
    title_y_pct: int = 78,
    mirror_vid: bool = False
) -> bytes:
    img = Image.open(BytesIO(frame_bytes)).convert("RGB")
    if mirror_vid:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)

    img = crop_and_resize_to_aspect(img, aspect_code)
    target_w, target_h = img.size
    ref_scale = min(target_w, target_h) / 720.0

    # 1. Cinematic Color Grading
    img = ImageEnhance.Contrast(img).enhance(1.16)
    img = ImageEnhance.Color(img).enhance(1.18)
    img = ImageEnhance.Sharpness(img).enhance(1.25)

    # 2. Cinematic Dark Gradient & Vignette Overlay
    y_grid = np.linspace(0.0, 1.0, target_h)[:, None]
    x_grid = np.linspace(-1.0, 1.0, target_w)[None, :]

    bottom_grad = np.clip((y_grid - 0.38) / 0.62, 0.0, 1.0) ** 1.45 * 230.0
    top_grad = np.clip((0.24 - y_grid) / 0.24, 0.0, 1.0) ** 1.5 * 150.0
    vignette = np.clip((x_grid ** 2 + (y_grid * 2.0 - 1.0) ** 2) - 0.35, 0.0, 1.0) * 85.0

    alpha_mask = np.clip(np.maximum(bottom_grad, top_grad) + vignette, 0, 242).astype(np.uint8)
    grad_rgba = np.zeros((target_h, target_w, 4), dtype=np.uint8)
    grad_rgba[:, :, 0] = 6
    grad_rgba[:, :, 1] = 9
    grad_rgba[:, :, 2] = 15
    grad_rgba[:, :, 3] = alpha_mask

    poster_rgba = Image.alpha_composite(img.convert("RGBA"), Image.fromarray(grad_rgba, mode="RGBA"))

    # 3. Cinematic Inner Frame
    draw = ImageDraw.Draw(poster_rgba)
    border_pad = int(min(target_w, target_h) * 0.028)
    primary_rgba = hex_to_rgba(primary_hex, 135)
    draw.rectangle(
        [border_pad, border_pad, target_w - border_pad, target_h - border_pad],
        outline=primary_rgba,
        width=max(2, int(2 * ref_scale))
    )

    # 4. Top Movie Tagline
    clean_tag = subtitle_tag.strip()
    if clean_tag:
        tag_px = max(15, int(22 * ref_scale))
        try:
            tag_font = ImageFont.truetype(font_path, tag_px)
        except Exception:
            tag_font = ImageFont.load_default()

        tb = draw.textbbox((0, 0), clean_tag, font=tag_font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        tx = (target_w - tw) // 2
        ty = int(target_h * 0.06)

        pill_pad_x, pill_pad_y = int(18 * ref_scale), int(7 * ref_scale)
        draw.rounded_rectangle(
            [tx - pill_pad_x, ty - pill_pad_y, tx + tw + pill_pad_x, ty + th + pill_pad_y],
            radius=int((th + pill_pad_y * 2) * 0.45),
            fill=(15, 23, 42, 195),
            outline=hex_to_rgba(primary_hex, 220),
            width=2
        )
        draw.text((tx - tb[0], ty - tb[1]), clean_tag, font=tag_font, fill=hex_to_rgba(primary_hex, 255))

    # 5. Main Movie Poster Title
    if title_text.strip():
        base_title_px = max(24, int(50 * (title_size_pct / 100.0) * ref_scale))
        try:
            title_font = ImageFont.truetype(font_path, base_title_px)
        except Exception:
            title_font = ImageFont.load_default()

        max_text_w = int(target_w * 0.86)
        lines = wrap_poster_title_lines(title_text, title_font, max_text_w)

        line_metrics = []
        for ln in lines:
            lb = draw.textbbox((0, 0), ln, font=title_font)
            line_metrics.append((ln, lb[2] - lb[0], lb[3] - lb[1], lb[0], lb[1]))

        line_gap = int(base_title_px * 0.28)
        total_block_h = sum(m[2] for m in line_metrics) + line_gap * max(0, len(line_metrics) - 1)
        start_y = int((target_h * (title_y_pct / 100.0)) - (total_block_h / 2.0))
        start_y = min(max(int(target_h * 0.14), start_y), target_h - total_block_h - border_pad - 16)

        shadow_layer = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shadow_layer)
        stroke_w = max(3, int(round(4.5 * ref_scale)))

        curr_y = start_y
        for idx, (ln, lw, lh, ox_off, oy_off) in enumerate(line_metrics):
            lx = (target_w - lw) // 2 - ox_off
            ly = curr_y - oy_off
            s_draw.text(
                (lx, ly + int(6 * ref_scale)),
                ln,
                font=title_font,
                fill=(0, 0, 0, 230),
                stroke_width=stroke_w + 4,
                stroke_fill=(0, 0, 0, 230)
            )
            curr_y += lh + line_gap

        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=max(3, int(6 * ref_scale))))
        poster_rgba = Image.alpha_composite(poster_rgba, shadow_layer)
        draw = ImageDraw.Draw(poster_rgba)

        curr_y = start_y
        for idx, (ln, lw, lh, ox_off, oy_off) in enumerate(line_metrics):
            lx = (target_w - lw) // 2 - ox_off
            ly = curr_y - oy_off
            fill_hex = primary_hex if idx == 0 else secondary_hex
            draw.text(
                (lx, ly),
                ln,
                font=title_font,
                fill=hex_to_rgba(fill_hex, 255),
                stroke_width=stroke_w,
                stroke_fill=(0, 0, 0, 255)
            )
            curr_y += lh + line_gap

        line_y = min(target_h - border_pad - 8, curr_y + int(10 * ref_scale))
        bar_w = int(target_w * 0.34)
        draw.rounded_rectangle(
            [(target_w - bar_w) // 2, line_y, (target_w + bar_w) // 2, line_y + max(3, int(4 * ref_scale))],
            radius=2,
            fill=hex_to_rgba(primary_hex, 230)
        )

    out_buf = BytesIO()
    poster_rgba.convert("RGB").save(out_buf, format="PNG", optimize=True)
    return out_buf.getvalue()

def render_myanmar_subtitle_rgba(
    text: str, font_path: str, size_scale_pct: int, vid_w: int,
    text_hex: str = "#38BDF8", pill_bg: bool = False
) -> Image.Image:
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

    sp = max(2, int(round(2.3 * (vid_w / 720.0))))
    pad_x = int(16 * (vid_w / 720.0))
    pad_y = int(10 * (vid_w / 720.0))
    img_w = tw + (sp * 2) + (pad_x * 2)
    img_h = th + (sp * 2) + (pad_y * 2)

    canvas = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    if pill_bg:
        draw.rounded_rectangle(
            [2, 2, img_w - 2, img_h - 2],
            radius=int(img_h * 0.35),
            fill=(15, 15, 15, 150)
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

def build_touch_canvas_background(
    frame_bytes: bytes,
    disp_w: int,
    disp_h: int,
    active_mode: str,
    enable_blur: bool,
    blur_box_disp: tuple,
    blur_opacity_pct: int,
    enable_vblur: bool,
    vblur_box_disp: tuple,
    vblur_opacity_pct: int,
    show_sub: bool,
    sub_center_disp: tuple,
    sample_text: str,
    font_path: str,
    sub_size_pct: int,
    sub_color_hex: str,
    mirror_vid: bool
) -> Image.Image:
    img = Image.open(BytesIO(frame_bytes)).convert("RGBA")
    if mirror_vid:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    img = img.resize((disp_w, disp_h), Image.LANCZOS)

    # 1. အလျားလိုက် စာတန်း Blur (မူလ)
    bx_x, bx_y, bx_w, bx_h = blur_box_disp
    bx_x = min(max(0, bx_x), disp_w - 12)
    bx_y = min(max(0, bx_y), disp_h - 12)
    bx_w = min(max(12, bx_w), disp_w - bx_x)
    bx_h = min(max(12, bx_h), disp_h - bx_y)

    if enable_blur and blur_opacity_pct > 0:
        crop = img.crop((bx_x, bx_y, bx_x + bx_w, bx_y + bx_h))
        blurred = crop.filter(ImageFilter.GaussianBlur(radius=max(3, int(12 * (blur_opacity_pct / 100.0)))))
        dark_overlay = Image.new("RGBA", (bx_w, bx_h), (20, 20, 20, int(140 * (blur_opacity_pct / 100.0))))
        blurred = Image.alpha_composite(blurred.convert("RGBA"), dark_overlay)
        img.paste(blurred, (bx_x, bx_y))

        if active_mode != "blur":
            draw = ImageDraw.Draw(img)
            draw.rounded_rectangle([bx_x, bx_y, bx_x + bx_w, bx_y + bx_h], radius=6, outline=(234, 88, 12, 200), width=2)

    # 2. ဒေါင်လိုက် Blur အသစ် (လုံးဝ မမဲစေဘဲ Pure Clean Glass Blur)
    vx_x, vx_y, vx_w, vx_h = vblur_box_disp
    vx_x = min(max(0, vx_x), disp_w - 12)
    vx_y = min(max(0, vx_y), disp_h - 12)
    vx_w = min(max(12, vx_w), disp_w - vx_x)
    vx_h = min(max(12, vx_h), disp_h - vx_y)

    if enable_vblur and vblur_opacity_pct > 0:
        vcrop = img.crop((vx_x, vx_y, vx_x + vx_w, vx_y + vx_h))
        vblurred = vcrop.filter(ImageFilter.GaussianBlur(radius=max(3, int(14 * (vblur_opacity_pct / 100.0)))))
        # မဲမနေစေရန် အနက်ရောင် Overlay လုံးဝမထည့်ဘဲ အလင်းကို မူရင်းအတိုင်း သန့်စင်စွာ ကပ်ပေးသည်
        img.paste(vblurred, (vx_x, vx_y))

        if active_mode != "vblur":
            draw = ImageDraw.Draw(img)
            draw.rounded_rectangle([vx_x, vx_y, vx_x + vx_w, vx_y + vx_h], radius=6, outline=(16, 185, 129, 220), width=2)

    # 3. မြန်မာစာတန်းထိုး
    if show_sub:
        sub_rgba = render_myanmar_subtitle_rgba(sample_text, font_path, sub_size_pct, disp_w, sub_color_hex, pill_bg=False)
        sc_x, sc_y = sub_center_disp
        sx = min(max(2, sc_x - (sub_rgba.width // 2)), disp_w - sub_rgba.width - 2)
        sy = min(max(2, sc_y - (sub_rgba.height // 2)), disp_h - sub_rgba.height - 2)
        img.alpha_composite(sub_rgba, (sx, sy))

    return img.convert("RGB")

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

def discover_available_gemini_models(gemini_client, preferred_model: str) -> list:
    candidates = [
        preferred_model.strip(),
        "gemini-3.8-flash",
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite-preview",
        "gemini-3.0-flash"
    ]
    try:
        for m in gemini_client.models.list():
            name = getattr(m, "name", "") or ""
            if name.startswith("models/"):
                name = name.replace("models/", "", 1)
            lower_n = name.lower()
            if "gemini" in lower_n and ("flash" in lower_n or "pro" in lower_n):
                if not any(x in lower_n for x in ["tts", "image", "vision", "embedding", "veo", "audio", "2.0", "1.5"]):
                    candidates.append(name)
    except Exception:
        pass

    chain = []
    for c in candidates:
        if c and c not in chain:
            chain.append(c)
    return chain

def discover_available_groq_models(groq_client) -> list:
    candidates = []
    try:
        models_resp = groq_client.models.list()
        for m in getattr(models_resp, "data", []):
            mid = getattr(m, "id", "") or ""
            low = mid.lower()
            if any(x in low for x in ["whisper", "tts", "guard", "orpheus", "playai", "embed", "vision"]):
                continue
            candidates.append(mid)
    except Exception:
        pass

    preferred_order = sorted(
        candidates,
        key=lambda x: (0 if "70b" in x.lower() or "llama-4" in x.lower() or "qwen" in x.lower() or "deepseek" in x.lower() else 1)
    )
    fallback_defaults = ["llama-3.3-70b-specdec", "llama-3.1-8b-instant", "gemma2-9b-it"]
    chain = []
    for c in preferred_order + fallback_defaults:
        if c and c not in chain:
            chain.append(c)
    return chain[:5]

def extract_json_from_text(raw_txt: str):
    raw_txt = raw_txt.strip()
    raw_txt = re.sub(r"^```(?:json)?\s*", "", raw_txt)
    raw_txt = re.sub(r"\s*```$", "", raw_txt)
    parsed = json.loads(raw_txt)
    if isinstance(parsed, dict):
        for k in ("translations", "items", "titles", "data", "result", "lines"):
            if k in parsed and isinstance(parsed[k], list):
                return parsed[k]
        for v in parsed.values():
            if isinstance(v, list):
                return v
    if isinstance(parsed, list):
        return parsed
    raise ValueError(f"JSON List ပုံစံ မဟုတ်ပါ: {type(parsed)}")

def generate_ai_poster_titles(gemini_client, groq_client, preferred_model: str, segments: list) -> list:
    """
    Video အကြောင်းအရာကို ဖတ်ပြီး ဆွဲဆောင်မှုရှိသော ရုပ်ရှင်ပိုစတာ ခေါင်းစဉ် (၃) မျိုး အလိုအလျောက် ရေးပေးခြင်း
    """
    summary_lines = [s.get("translated") or s.get("text", "") for s in segments[:35] if s.get("translated") or s.get("text")]
    story_context = "\n".join(summary_lines)[:2500]
    if not story_context.strip():
        return [
            "အတိတ်က လျှို့ဝှက်ချက်နှင့်\nနောက်ဆုံးတိုက်ပွဲ",
            "ကံကြမ္မာကို ပြောင်းလဲခဲ့သူ၏\nအံ့ဖွယ်ဇာတ်လမ်း",
            "ဘယ်သူမှ မထင်မှတ်ထားတဲ့\nအမှန်တရား"
        ]

    prompt = (
        "Based on the following movie recap script in Burmese, generate 3 catchy, dramatic, and click-worthy "
        "Burmese movie poster titles (ရုပ်ရှင်ပိုစတာ ခေါင်းစဉ် ၃ မျိုး). "
        "Each title should be short (4 to 9 words), impactful, and formatted in 1 or 2 lines using '\\n'. "
        "Do not use emojis or English words. Return ONLY a JSON object with key 'titles' containing a list of 3 strings:\n"
        f"{story_context}"
    )

    gemini_chain = discover_available_gemini_models(gemini_client, preferred_model)
    for model_name in gemini_chain:
        try:
            resp = gemini_client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    http_options=types.HttpOptions(timeout=20000)
                )
            )
            raw_list = extract_json_from_text(resp.text or "")
            cleaned_titles = []
            for item in raw_list:
                t_str = item.get("title", "") if isinstance(item, dict) else str(item)
                lines = [clean_text_for_myanmar_font(ln) for ln in t_str.split("\n") if clean_text_for_myanmar_font(ln)]
                if lines:
                    cleaned_titles.append("\n".join(lines[:2]))
            if len(cleaned_titles) >= 3:
                return cleaned_titles[:3]
        except Exception:
            continue

    groq_chain = discover_available_groq_models(groq_client)
    for g_model in groq_chain:
        try:
            g_resp = groq_client.chat.completions.create(
                model=g_model,
                messages=[
                    {"role": "system", "content": "You write dramatic Burmese movie poster titles. Output valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                timeout=20.0
            )
            raw_list = extract_json_from_text(g_resp.choices[0].message.content)
            cleaned_titles = []
            for item in raw_list:
                t_str = item.get("title", "") if isinstance(item, dict) else str(item)
                lines = [clean_text_for_myanmar_font(ln) for ln in t_str.split("\n") if clean_text_for_myanmar_font(ln)]
                if lines:
                    cleaned_titles.append("\n".join(lines[:2]))
            if len(cleaned_titles) >= 3:
                return cleaned_titles[:3]
        except Exception:
            continue

    return [
        segments[0].get("translated", "အတိတ်က လျှို့ဝှက်ချက်နှင့်\nနောက်ဆုံးတိုက်ပွဲ"),
        segments[min(1, len(segments) - 1)].get("translated", "ကံကြမ္မာကို ပြောင်းလဲခဲ့သူ"),
        segments[min(2, len(segments) - 1)].get("translated", "မထင်မှတ်ထားသော အမှန်တရား")
    ]

def translate_segments_recap_style(gemini_client, groq_client, preferred_model: str, segments: list, style_mode: str, log_fn=None):
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

    gemini_chain = discover_available_gemini_models(gemini_client, preferred_model)
    groq_chain = None
    dead_gemini_models = set()

    batch_size = 20
    total_batches = max(1, (len(segments) + batch_size - 1) // batch_size)

    for b_idx, i in enumerate(range(0, len(segments), batch_size), start=1):
        batch = segments[i:i + batch_size]
        payload = [{"id": idx, "text": s["text"]} for idx, s in enumerate(batch)]
        prompt = (
            f"{style_instr}\nDo not use emojis or special symbols. "
            f"Return ONLY a JSON list of objects with 'id' and 'translation':\n{json.dumps(payload, ensure_ascii=False)}"
        )

        translated_ok = False
        last_gemini_err = ""

        for model_name in gemini_chain:
            if model_name in dead_gemini_models:
                continue
            if log_fn:
                log_fn(f"🌐 ဘာသာပြန်နေသည် (အပိုင်း {b_idx}/{total_batches}) - Model: `{model_name}`...")
            try:
                resp = gemini_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        http_options=types.HttpOptions(timeout=25000)
                    )
                )
                raw_txt = (resp.text or "").strip()
                if not raw_txt:
                    raise ValueError("Empty response from Gemini")

                parsed_list = extract_json_from_text(raw_txt)
                t_map = {int(item["id"]): str(item.get("translation", "")).strip() for item in parsed_list if isinstance(item, dict) and "id" in item}
                for idx, s in enumerate(batch):
                    s["translated"] = clean_text_for_myanmar_font(t_map.get(idx, s["text"]))
                translated_ok = True
                break
            except Exception as e:
                err_str = str(e)
                last_gemini_err = f"{model_name}: {err_str[:160]}"
                if "404" in err_str or "NOT_FOUND" in err_str or "no longer available" in err_str:
                    dead_gemini_models.add(model_name)
                if log_fn:
                    log_fn(f"⚠️ `{model_name}` မရပါ ({err_str[:90]}...) အခြား Model သို့ ပြောင်းနေသည်...")
                time.sleep(0.5)

        if not translated_ok:
            if groq_chain is None:
                groq_chain = discover_available_groq_models(groq_client)

            last_groq_err = ""
            for g_model in groq_chain:
                if log_fn:
                    log_fn(f"🔄 Groq Fallback Model (`{g_model}`) ဖြင့် အပိုင်း {b_idx}/{total_batches} ကို ဘာသာပြန်နေသည်...")
                try:
                    groq_resp = groq_client.chat.completions.create(
                        model=g_model,
                        messages=[
                            {"role": "system", "content": f"{style_instr} Output valid JSON only."},
                            {"role": "user", "content": f"Return JSON object with key 'items' containing list of 'id' and 'translation':\n{json.dumps(payload, ensure_ascii=False)}"}
                        ],
                        response_format={"type": "json_object"},
                        timeout=30.0
                    )
                    g_list = extract_json_from_text(groq_resp.choices[0].message.content)
                    t_map = {int(item["id"]): str(item.get("translation", "")).strip() for item in g_list if isinstance(item, dict) and "id" in item}
                    for idx, s in enumerate(batch):
                        s["translated"] = clean_text_for_myanmar_font(t_map.get(idx, s["text"]))
                    translated_ok = True
                    break
                except Exception as ge:
                    last_groq_err = f"{g_model}: {str(ge)[:160]}"
                    continue

            if not translated_ok:
                raise RuntimeError(
                    f"Gemini နှင့် Groq နှစ်ခုလုံးဖြင့် ဘာသာပြန်၍ မရပါ။\n"
                    f"• Gemini Error: {last_gemini_err}\n"
                    f"• Groq Error: {last_groq_err}"
                )

def extract_and_translate_pipeline(video_path: str, groq_key: str, gemini_key: str, gemini_model: str, style_mode: str, log_fn=None) -> tuple:
    if log_fn:
        log_fn("🎵 အဆင့် ၁(က) - Video ထဲမှ အသံဖိုင် (MP3) ထုတ်ယူနေပါသည်...")
    extracted_audio = extract_compressed_audio(video_path)
    audio_mb = os.path.getsize(extracted_audio) / (1024 * 1024)

    if log_fn:
        log_fn(f"🎙️ အဆင့် ၁(ခ) - Groq Whisper ဖြင့် အသံဖမ်းယူနေပါသည် ({audio_mb:.2f} MB)...")

    groq_client = Groq(api_key=groq_key.strip(), timeout=60.0)
    whisper_models = ["whisper-large-v3-turbo", "whisper-large-v3"]
    trans = None
    last_w_err = ""

    for w_model in whisper_models:
        try:
            with open(extracted_audio, "rb") as f:
                trans = groq_client.audio.transcriptions.create(
                    file=(extracted_audio, f.read()),
                    model=w_model,
                    response_format="verbose_json"
                )
            break
        except Exception as e:
            last_w_err = str(e)

    if os.path.exists(extracted_audio):
        os.remove(extracted_audio)

    if trans is None:
        raise RuntimeError(f"Groq Whisper API Error: {last_w_err}")

    raw_segs = getattr(trans, "segments", None) or (trans.get("segments", []) if isinstance(trans, dict) else [])
    segs = merge_close_whisper_segments(raw_segs)

    if not segs:
        raise RuntimeError("Video ထဲတွင် စကားပြောသံ ရှာမတွေ့ပါ (Whisper မှ စာသားထွက်မလာပါ)။")

    if log_fn:
        log_fn(f"📝 စကားပြော စာကြောင်း ({len(segs)}) ကြောင်း ရရှိပါပြီ။ မြန်မာဘာသာသို့ စတင်ပြန်ဆိုနေပါသည်...")

    gemini_client = genai.Client(api_key=gemini_key.strip())
    translate_segments_recap_style(gemini_client, groq_client, gemini_model, segs, style_mode, log_fn=log_fn)

    if log_fn:
        log_fn("🎬 AI ဖြင့် ရုပ်ရှင်ပိုစတာ ခေါင်းစဉ် (၃) မျိုး အလိုအလျောက် ဖန်တီးနေပါသည်...")
    ai_titles = generate_ai_poster_titles(gemini_client, groq_client, gemini_model, segs)

    return segs, ai_titles

async def synthesize_all_tts(segments, voice_id, rate_str, pitch_str):
    sem = asyncio.Semaphore(5)
    async def _one(idx, text):
        async with sem:
            raw_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
            trimmed_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
            clean_t = (text or "").strip() or "အင်း"

            tts_ok = False
            last_err = None
            for attempt in range(3):
                try:
                    comm = edge_tts.Communicate(text=clean_t, voice=voice_id, rate=rate_str, pitch=pitch_str)
                    with open(raw_mp3, "wb") as f:
                        async for chunk in comm.stream():
                            if chunk["type"] == "audio":
                                f.write(chunk["data"])
                    if os.path.exists(raw_mp3) and os.path.getsize(raw_mp3) > 100:
                        tts_ok = True
                        break
                except Exception as e:
                    last_err = e
                    await asyncio.sleep(0.8)

            if not tts_ok:
                raise RuntimeError(f"Edge-TTS မြန်မာအသံထုတ်ရာတွင် Error တက်နေပါသည် (စာကြောင်း {idx+1}): {last_err}")

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
    enable_vblur: bool,
    vblur_box_norm: tuple,
    vblur_opacity_pct: int,
    show_sub: bool,
    sub_center_norm: tuple,
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
    raw_out_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    web_ready_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name

    target_fps = min(24.0, vid_fps)
    vf_chain = [f"fps={target_fps:.2f}"]
    if mirror_vid:
        vf_chain.append("hflip")

    if zoom_pct > 100:
        zf = zoom_pct / 100.0
        vf_chain.append(f"scale=iw*{zf:.3f}:ih*{zf:.3f}:flags=fast_bilinear,crop=iw/{zf:.3f}:ih/{zf:.3f}")

    vf_chain.append(f"scale={vid_w}:{vid_h}:flags=fast_bilinear,setsar=1")

    if abs(brightness_val) > 0.01 or abs(contrast_val - 1.0) > 0.01 or abs(saturation_val - 1.0) > 0.01:
        vf_chain.append(f"eq=brightness={brightness_val:.2f}:contrast={contrast_val:.2f}:saturation={saturation_val:.2f}")

    vf_chain.append("format=rgb24")
    base_vf_str = ",".join(vf_chain)

    bx_x, bx_y, bx_w, bx_h = blur_box_norm
    vx_x, vx_y, vx_w, vx_h = vblur_box_norm

    use_hblur = enable_blur and blur_opacity_pct > 0 and bx_w >= 8 and bx_h >= 8
    use_vblur = enable_vblur and vblur_opacity_pct > 0 and vx_w >= 8 and vx_h >= 8

    # FFmpeg Filter Graph တွင် အလျားလိုက် Blur နှင့် ဒေါင်လိုက် Blur (အမဲမပါ) တို့ကို တည်ဆောက်ခြင်း
    curr_pad = "[v0]"
    filter_parts = [f"{base_vf_str}{curr_pad}"]

    if use_hblur:
        luma_r = max(2, min(int(min(bx_w, bx_h) / 4), int(14 * (blur_opacity_pct / 100.0))))
        filter_parts.append(
            f"{curr_pad}split=2[vm1][vc1];"
            f"[vc1]crop={bx_w}:{bx_h}:{bx_x}:{bx_y},boxblur={luma_r}:1,"
            f"eq=brightness=-0.16:contrast=0.92[vb1];"
            f"[vm1][vb1]overlay={bx_x}:{bx_y}[v1]"
        )
        curr_pad = "[v1]"

    if use_vblur:
        # ဒေါင်လိုက် Blur သည် လုံးဝမဲမနေစေရန် eq darkening မထည့်ဘဲ သန့်စင်သော boxblur သာ သုံးထားသည်
        vluma_r = max(2, min(int(min(vx_w, vx_h) / 4), int(16 * (vblur_opacity_pct / 100.0))))
        filter_parts.append(
            f"{curr_pad}split=2[vm2][vc2];"
            f"[vc2]crop={vx_w}:{vx_h}:{vx_x}:{vx_y},boxblur={vluma_r}:1[vb2];"
            f"[vm2][vb2]overlay={vx_x}:{vx_y}[v2]"
        )
        curr_pad = "[v2]"

    if len(filter_parts) == 1:
        decode_vf = base_vf_str
    else:
        decode_vf = ";".join(filter_parts)
        if decode_vf.endswith(curr_pad):
            decode_vf = decode_vf[:-len(curr_pad)]

    sub_cx, sub_cy = sub_center_norm

    decoder_cmd = ["ffmpeg", "-v", "error", "-threads", "2", "-i", video_path, "-vf", decode_vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]
    encoder_cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{vid_w}x{vid_h}", "-pix_fmt", "rgb24", "-r", f"{target_fps:.2f}",
        "-i", "pipe:0",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "25",
        "-maxrate", "2200k", "-bufsize", "4400k",
        "-profile:v", "main", "-pix_fmt", "yuv420p", "-threads", "0",
        raw_out_video
    ]

    dec_proc = subprocess.Popen(decoder_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    enc_proc = subprocess.Popen(encoder_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    frame_bytes_len = vid_w * vid_h * 3
    total_out_dur = sum(item["target_dur"] for item in timeline)
    total_out_frames = max(1, int(round(total_out_dur * target_fps)))

    out_cursor = 0.0
    time_segments = []
    for item in timeline:
        td = max(0.02, item["target_dur"])
        time_segments.append({"out_start": out_cursor, "out_end": out_cursor + td, "in_start": item["v_start"], "in_end": item["v_end"]})
        out_cursor += td

    wm_np = None
    if wm_rgba is not None:
        wx = min(max(6, int((vid_w - wm_rgba.width) * (wm_x_pct / 100.0))), vid_w - wm_rgba.width - 6)
        wy = min(max(6, int((vid_h - wm_rgba.height) * (wm_y_pct / 100.0))), vid_h - wm_rgba.height - 6)
        wm_arr = np.array(wm_rgba, dtype=np.float32)
        wm_alpha = wm_arr[:, :, 3:4] / 255.0
        wm_rgb = wm_arr[:, :, :3]
        wm_np = (wy, wy + wm_rgba.height, wx, wx + wm_rgba.width, wm_rgb, wm_alpha)

    for sub in sub_overlays:
        s_img = sub["img"]
        ox = min(max(4, sub_cx - (s_img.width // 2)), vid_w - s_img.width - 4)
        oy = min(max(4, sub_cy - (s_img.height // 2)), vid_h - s_img.height - 4)
        s_arr = np.array(s_img, dtype=np.float32)
        s_alpha = s_arr[:, :, 3:4] / 255.0
        s_rgb = s_arr[:, :, :3]
        sub["np_data"] = (oy, oy + s_img.height, ox, ox + s_img.width, s_rgb, s_alpha)

    curr_in_frame_idx = -1
    curr_in_frame_bytes = None
    last_in_idx = -1
    last_active_sub = None
    cached_out_bytes = None

    eof_reached = False
    seg_ptr = 0
    sub_ptr = 0
    num_subs = len(sub_overlays)
    frames_written = 0

    for out_idx in range(total_out_frames):
        t_out = out_idx / float(target_fps)
        while seg_ptr < len(time_segments) - 1 and t_out >= time_segments[seg_ptr]["out_end"]:
            seg_ptr += 1
        seg = time_segments[seg_ptr]

        seg_out_dur = max(0.001, seg["out_end"] - seg["out_start"])
        ratio = min(1.0, max(0.0, (t_out - seg["out_start"]) / seg_out_dur))
        t_in = seg["in_start"] + ratio * (seg["in_end"] - seg["in_start"])
        target_in_idx = max(0, int(round(t_in * target_fps)))

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

        if curr_in_frame_idx == last_in_idx and active_sub is last_active_sub and cached_out_bytes is not None:
            frame_to_write = cached_out_bytes
        else:
            if active_sub is not None or wm_np is not None:
                frame_arr = np.frombuffer(curr_in_frame_bytes, dtype=np.uint8).reshape((vid_h, vid_w, 3)).copy()
                if wm_np is not None:
                    y1, y2, x1, x2, rgb, alpha = wm_np
                    roi = frame_arr[y1:y2, x1:x2].astype(np.float32)
                    frame_arr[y1:y2, x1:x2] = (roi * (1.0 - alpha) + rgb * alpha).astype(np.uint8)
                if active_sub is not None:
                    y1, y2, x1, x2, rgb, alpha = active_sub["np_data"]
                    roi = frame_arr[y1:y2, x1:x2].astype(np.float32)
                    frame_arr[y1:y2, x1:x2] = (roi * (1.0 - alpha) + rgb * alpha).astype(np.uint8)
                frame_to_write = frame_arr.tobytes()
            else:
                frame_to_write = curr_in_frame_bytes

            last_in_idx = curr_in_frame_idx
            last_active_sub = active_sub
            cached_out_bytes = frame_to_write

        try:
            enc_proc.stdin.write(frame_to_write)
            frames_written += 1
        except BrokenPipeError:
            break

        if out_idx % 30 == 0:
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
    st.markdown("### 🔑 API Keys & Resolution")
    default_groq = st.secrets.get("GROQ_API_KEY", "") if "GROQ_API_KEY" in st.secrets else ""
    default_gemini = st.secrets.get("GEMINI_API_KEY", "") if "GEMINI_API_KEY" in st.secrets else ""
    groq_key = st.text_input("Groq API Key", value=default_groq, type="password")
    gemini_key = st.text_input("Gemini API Key", value=default_gemini, type="password")
    gemini_model = st.selectbox("Gemini Model", ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite-preview"])
    res_choice = st.selectbox("Video Resolution", ["720p HD (ဖိုင်ဆိုဒ်သေး & အကြည်လင်ဆုံး)", "Original Resolution", "1080p Full HD"])
    uploaded_font = st.file_uploader("Custom Font (.ttf) တင်ရန်", type=["ttf", "otf"])
    custom_font_path = register_uploaded_font(uploaded_font)

# ==================== SESSION STATE INITIALIZATION ====================
if "enable_blur" not in st.session_state:
    st.session_state["enable_blur"] = True
if "enable_vblur" not in st.session_state:
    st.session_state["enable_vblur"] = False
if "script_segments" not in st.session_state:
    st.session_state["script_segments"] = []
if "blur_box_disp" not in st.session_state:
    st.session_state["blur_box_disp"] = (16, 300, 208, 42)
if "vblur_box_disp" not in st.session_state:
    st.session_state["vblur_box_disp"] = (185, 25, 42, 160)
if "sub_center_disp" not in st.session_state:
    st.session_state["sub_center_disp"] = (120, 321)
if "poster_title_1" not in st.session_state:
    st.session_state["poster_title_1"] = "အတိတ်က လျှို့ဝှက်ချက်နှင့်\nနောက်ဆုံးတိုက်ပွဲ"
if "poster_title_2" not in st.session_state:
    st.session_state["poster_title_2"] = "ကံကြမ္မာကို ပြောင်းလဲခဲ့သူ၏\nအံ့ဖွယ်ဇာတ်လမ်း"
if "poster_title_3" not in st.session_state:
    st.session_state["poster_title_3"] = "ဘယ်သူမှ မထင်မှတ်ထားတဲ့\nအမှန်တရား"

# ==================== TOP BAR & VIDEO UPLOAD ====================
uploaded_video = st.file_uploader("📁 Recap ပြုလုပ်မည့် Video ဖိုင်ရွေးပါ", type=["mp4", "mov", "mkv", "webm"])

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

# ==================== CARD 3 SETTINGS (PRE-LOAD FOR LIVE TOUCH CANVAS) ====================
active_font_path = find_font_path(st.session_state.get("font_choice_state", FONT_CHOICES[0]), custom_font_path)
sub_color_hex = COLOR_PRESETS.get(st.session_state.get("color_label_state", "🔵 အပြာနု"), "#38BDF8")
sub_size_pct = st.session_state.get("sub_size_state", 90)
mirror_vid = st.session_state.get("mirror_state", False)
show_sub = st.session_state.get("show_sub_state", True)

# ==================== TOP INTERACTIVE TOUCH CANVAS (BLUR, VERTICAL BLUR & SUBTITLE DRAG) ====================
disp_w = 240 if orig_w <= orig_h else 320
disp_h = int(round(orig_h * (disp_w / float(orig_w))))

if video_temp_path:
    with st.container(border=True):
        st.markdown("##### 🖐️ Video ပေါ်တွင် Blur (၂) ခုနှင့် မြန်မာစာတန်းကို လက်ဖြင့် ဖိဆွဲ၍ ရွှေ့ပါ")

        touch_target = st.radio(
            "လက်ဖြင့် ဆွဲရွှေ့မည့်အရာ ရွေးချယ်ပါ -",
            [
                "🌫️ အလျားလိုက် Blur ရွှေ့မည်",
                "💧 ဒေါင်လိုက် Blur (အမဲမပါ) ရွှေ့မည်",
                "📝 မြန်မာစာတန်း ရွှေ့မည်"
            ],
            horizontal=True
        )
        if "ဒေါင်လိုက်" in touch_target:
            active_mode = "vblur"
        elif "အလျားလိုက်" in touch_target:
            active_mode = "blur"
        else:
            active_mode = "sub"

        preview_sec = st.slider("⏱️ Video စက္ကန့်ရွှေ့ကြည့်ရန်", 0.0, max(1.0, float(vid_dur)), min(2.0, float(vid_dur)), 0.5)

        b_col1, b_col2, b_col3 = st.columns(3)
        if b_col1.button("＋ စာတန်း Blur", use_container_width=True):
            st.session_state["enable_blur"] = True
        if b_col2.button("＋ ဒေါင်လိုက် Blur", use_container_width=True):
            st.session_state["enable_vblur"] = True
        if b_col3.button("🗑️ Blur အားလုံးဖျက်", use_container_width=True):
            st.session_state["enable_blur"] = False
            st.session_state["enable_vblur"] = False

        sl_c1, sl_c2 = st.columns(2)
        blur_opacity_pct = sl_c1.slider("စာတန်း Blur အထူ (%)", 0, 100, 100 if st.session_state["enable_blur"] else 0, 5)
        vblur_opacity_pct = sl_c2.slider("ဒေါင်လိုက် Blur အထူ (%)", 0, 100, 90 if st.session_state["enable_vblur"] else 0, 5)

        frame_bytes = extract_frame_bytes(video_temp_path, preview_sec, os.path.getsize(video_temp_path))
        if frame_bytes:
            sample_sub_txt = st.session_state["script_segments"][0]["translated"] if st.session_state.get("script_segments") else "ပြန်စရာအိမ်မရှိတော့တဲ့"

            cur_bx, cur_by, cur_bw, cur_bh = st.session_state["blur_box_disp"]
            cur_by = min(max(6, cur_by), disp_h - 24)
            cur_bh = min(max(16, cur_bh), disp_h - cur_by - 4)

            cur_vx, cur_vy, cur_vw, cur_vh = st.session_state["vblur_box_disp"]
            cur_vx = min(max(6, cur_vx), disp_w - 24)
            cur_vy = min(max(6, cur_vy), disp_h - 30)
            cur_vw = min(max(16, cur_vw), disp_w - cur_vx - 4)
            cur_vh = min(max(24, cur_vh), disp_h - cur_vy - 4)

            cur_sx, cur_sy = st.session_state["sub_center_disp"]
            cur_sy = min(max(15, cur_sy), disp_h - 15)

            bg_pil = build_touch_canvas_background(
                frame_bytes=frame_bytes,
                disp_w=disp_w,
                disp_h=disp_h,
                active_mode=active_mode,
                enable_blur=st.session_state["enable_blur"],
                blur_box_disp=(cur_bx, cur_by, cur_bw, cur_bh),
                blur_opacity_pct=blur_opacity_pct,
                enable_vblur=st.session_state["enable_vblur"],
                vblur_box_disp=(cur_vx, cur_vy, cur_vw, cur_vh),
                vblur_opacity_pct=vblur_opacity_pct,
                show_sub=show_sub,
                sub_center_disp=(cur_sx, cur_sy),
                sample_text=sample_sub_txt,
                font_path=active_font_path,
                sub_size_pct=sub_size_pct,
                sub_color_hex=sub_color_hex,
                mirror_vid=mirror_vid
            )

            pad_l, center_col, pad_r = st.columns([0.8, 2.4, 0.8])
            with center_col:
                if active_mode == "blur":
                    st.caption("🟧 **လိမ္မော်ရောင် အလျားလိုက် Blur ဘောင်ကို လက်ဖြင့် ဖိဆွဲ၍ နေရာရွှေ့ပါ / အကြီးအသေးချဲ့ပါ**")
                    def_coords = (cur_bx, min(disp_w - 4, cur_bx + cur_bw), cur_by, min(disp_h - 4, cur_by + cur_bh))
                    box_dict = st_cropper(
                        bg_pil,
                        realtime_update=True,
                        box_color="#EA580C",
                        aspect_ratio=None,
                        default_coords=def_coords,
                        return_type="box",
                        key="touch_drag_blur"
                    )
                    new_bx = max(0, int(box_dict["left"]))
                    new_by = max(0, int(box_dict["top"]))
                    new_bw = max(14, int(box_dict["width"]))
                    new_bh = max(14, int(box_dict["height"]))
                    st.session_state["blur_box_disp"] = (new_bx, new_by, new_bw, new_bh)
                elif active_mode == "vblur":
                    st.caption("🟩 **အစိမ်းရောင် ဒေါင်လိုက် Blur (အမဲမပါ) ဘောင်ကို လက်ဖြင့် ဖိဆွဲ၍ နေရာရွှေ့ပါ / အကြီးအသေးချဲ့ပါ**")
                    st.session_state["enable_vblur"] = True
                    def_vcoords = (cur_vx, min(disp_w - 4, cur_vx + cur_vw), cur_vy, min(disp_h - 4, cur_vy + cur_vh))
                    vbox_dict = st_cropper(
                        bg_pil,
                        realtime_update=True,
                        box_color="#10B981",
                        aspect_ratio=None,
                        default_coords=def_vcoords,
                        return_type="box",
                        key="touch_drag_vblur"
                    )
                    new_vx = max(0, int(vbox_dict["left"]))
                    new_vy = max(0, int(vbox_dict["top"]))
                    new_vw = max(14, int(vbox_dict["width"]))
                    new_vh = max(18, int(vbox_dict["height"]))
                    st.session_state["vblur_box_disp"] = (new_vx, new_vy, new_vw, new_vh)
                else:
                    st.caption("🟦 **အပြာရောင် စာတန်းဘောင်ကို လက်ဖြင့် ဖိဆွဲပြီး ထားချင်သည့်နေရာသို့ ရွှေ့ပါ**")
                    sub_box_w = int(disp_w * 0.82)
                    sub_box_h = 34
                    s_left = max(4, cur_sx - (sub_box_w // 2))
                    s_top = max(4, cur_sy - (sub_box_h // 2))
                    def_sub_coords = (s_left, min(disp_w - 4, s_left + sub_box_w), s_top, min(disp_h - 4, s_top + sub_box_h))
                    sub_dict = st_cropper(
                        bg_pil,
                        realtime_update=True,
                        box_color="#0284C7",
                        aspect_ratio=None,
                        default_coords=def_sub_coords,
                        return_type="box",
                        key="touch_drag_subtitle"
                    )
                    new_scx = int(sub_dict["left"] + (sub_dict["width"] // 2))
                    new_scy = int(sub_dict["top"] + (sub_dict["height"] // 2))
                    st.session_state["sub_center_disp"] = (new_scx, new_scy)
else:
    blur_opacity_pct = 100
    vblur_opacity_pct = 90

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

    if st.button("🪄 Script နှင့် Poster ခေါင်းစဉ် (၃) မျိုး ထုတ်မယ်", type="primary", use_container_width=True):
        if not video_temp_path:
            st.error("Video အရင်တင်ပေးပါ။")
        elif not groq_key or not gemini_key:
            st.error("Groq နှင့် Gemini API Key နှစ်ခုလုံး ထည့်ပေးပါ။")
        else:
            s_box = st.status("⏳ မြန်မာ Script နှင့် Poster ခေါင်းစဉ်များ စတင်ထုတ်ယူနေပါသည်...", expanded=True)
            try:
                segs, ai_titles = extract_and_translate_pipeline(
                    video_path=video_temp_path,
                    groq_key=groq_key,
                    gemini_key=gemini_key,
                    gemini_model=gemini_model,
                    style_mode=style_mode,
                    log_fn=s_box.write
                )
                st.session_state["script_segments"] = segs
                if len(ai_titles) >= 3:
                    st.session_state["poster_title_1"] = ai_titles[0]
                    st.session_state["poster_title_2"] = ai_titles[1]
                    st.session_state["poster_title_3"] = ai_titles[2]
                s_box.update(label=f"✅ စာကြောင်း ({len(segs)}) ကြောင်းနှင့် Poster ခေါင်းစဉ် (၃) မျိုး ထုတ်ပြီးပါပြီ!", state="complete", expanded=False)
                st.rerun()
            except Exception as e:
                s_box.update(label="❌ Script ထုတ်ရာတွင် Error တက်သွားပါသည်", state="error", expanded=True)
                st.error(f"**Error အသေးစိတ်:**\n{e}")
                st.code(traceback.format_exc())

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

    mirror_vid = st.toggle("ဘယ်ညာ ပြောင်းပြန်လှည့် (Mirror - Copyright ကာကွယ်ရန်)", value=False, key="mirror_state")
    show_sub = st.toggle("မြန်မာစာတန်း video ထဲ ထည့်မယ်", value=True, key="show_sub_state")

    font_choice = st.selectbox("ဖောင့် ရွေးချယ်ရန် (Noto Sans / Noto Serif / Padauk)", FONT_CHOICES, index=0, key="font_choice_state")
    active_font_path = find_font_path(font_choice, custom_font_path)

    color_label = st.radio("စာလုံးအရောင်", list(COLOR_PRESETS.keys()), index=2, horizontal=True, key="color_label_state")
    sub_color_hex = COLOR_PRESETS[color_label]

    sub_size_pct = st.slider("စာလုံးအရွယ် (%)", 60, 140, 90, 5, key="sub_size_state")
    if st.button("🔄 စာတန်းနှင့် Blur (၂) ခုလုံး မူလနေရာ ပြန်ထားမယ်"):
        st.session_state["blur_box_disp"] = (int(disp_w * 0.08), int(disp_h * 0.74), int(disp_w * 0.84), int(disp_h * 0.11))
        st.session_state["vblur_box_disp"] = (int(disp_w * 0.76), int(disp_h * 0.08), int(disp_w * 0.16), int(disp_h * 0.45))
        st.session_state["sub_center_disp"] = (disp_w // 2, int(disp_h * 0.79))
        st.rerun()

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

# ==================== CARD 4: ထုတ်ယူမယ် ====================
with st.container(border=True):
    st.markdown("""
    <div class="step-header">
        <div class="step-circle">4</div>
        <div class="step-title">Recap Video ထုတ်ယူမယ်</div>
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

                if not st.session_state.get("script_segments"):
                    status.write("🎧 **၁/၄ - မြန်မာ Script နှင့် Poster ခေါင်းစဉ်များ စတင်ထုတ်ယူနေပါသည်...**")
                    segs, ai_titles = extract_and_translate_pipeline(
                        video_path=video_temp_path,
                        groq_key=groq_key,
                        gemini_key=gemini_key,
                        gemini_model=gemini_model,
                        style_mode=style_mode,
                        log_fn=status.write
                    )
                    st.session_state["script_segments"] = segs
                    if len(ai_titles) >= 3:
                        st.session_state["poster_title_1"] = ai_titles[0]
                        st.session_state["poster_title_2"] = ai_titles[1]
                        st.session_state["poster_title_3"] = ai_titles[2]

                segments = st.session_state["script_segments"]

                status.write(f"🗣️ **၂/၄ - မြန်မာ Voiceover အသံ ({len(segments)} ကြောင်း) ထုတ်ယူနေပါသည်...**")
                tts_res = asyncio.run(
                    synthesize_all_tts(segments, v_cfg["voice"], f"{int(extra_speed):+d}%", f"{int(extra_pitch):+d}Hz")
                )
                for idx, wav_p, tdur in tts_res:
                    segments[idx]["wav"] = wav_p
                    segments[idx]["tts_dur"] = tdur

                status.write("📝 **၃/၄ - မြန်မာစာတန်းထိုးနှင့် အသံ Timing ချိန်ညှိနေပါသည်...**")
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
                                    c_str, active_font_path, int(sub_size_pct), vid_w, sub_color_hex, pill_bg=False
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

                status.write(f"🎞️ **၄/၄ - HD Video ({vid_w}x{vid_h}) ကို ပေါင်းစပ်နေပါသည်...**")
                p_bar = st.progress(0.0)

                sx = vid_w / float(disp_w)
                sy = vid_h / float(disp_h)

                dbx, dby, dbw, dbh = st.session_state["blur_box_disp"]
                norm_blur_box = (
                    min(max(0, int(dbx * sx)), vid_w - 16),
                    min(max(0, int(dby * sy)), vid_h - 16),
                    max(16, min(vid_w, int(dbw * sx))),
                    max(16, min(vid_h, int(dbh * sy)))
                )

                dvx, dvy, dvw, dvh = st.session_state["vblur_box_disp"]
                norm_vblur_box = (
                    min(max(0, int(dvx * sx)), vid_w - 16),
                    min(max(0, int(dvy * sy)), vid_h - 16),
                    max(16, min(vid_w, int(dvw * sx))),
                    max(16, min(vid_h, int(dvh * sy)))
                )

                dsx, dsy = st.session_state["sub_center_disp"]
                norm_sub_center = (
                    min(max(10, int(dsx * sx)), vid_w - 10),
                    min(max(10, int(dsy * sy)), vid_h - 10)
                )

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
                    blur_box_norm=norm_blur_box,
                    blur_opacity_pct=blur_opacity_pct,
                    enable_vblur=st.session_state["enable_vblur"],
                    vblur_box_norm=norm_vblur_box,
                    vblur_opacity_pct=vblur_opacity_pct,
                    show_sub=show_sub,
                    sub_center_norm=norm_sub_center,
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
                status.update(label="❌ Error ဖြစ်ပွားပါသည် (အောက်တွင် အသေးစိတ်ကြည့်ပါ)", state="error", expanded=True)
                st.error(f"**Error အသေးစိတ်:**\n{e}")
                st.code(traceback.format_exc())

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

# ==================== CARD 5: MOVIE POSTER THUMBNAIL GENERATOR (AI ခေါင်းစဉ် ၃ မျိုး + 16:9 / 9:16) ====================
with st.container(border=True):
    st.markdown("""
    <div class="step-header">
        <div class="step-circle">5</div>
        <div class="step-title">🎬 Movie Poster Thumbnail (AI ခေါင်းစဉ် ၃ မျိုး & အချိုးရွေးရန်)</div>
    </div>
    """, unsafe_allow_html=True)

    if not video_temp_path:
        st.info("📌 Video ဖိုင်တင်လိုက်သည်နှင့် Movie Poster ပုံစံ Thumbnail (၃) ပုံကို AI ခေါင်းစဉ် (၃) မျိုးဖြင့် ထုတ်ယူနိုင်ပါမည်။")
    else:
        aspect_label = st.radio(
            "📐 Thumbnail အချိုးအစား (Aspect Ratio) ရွေးပါ -",
            list(THUMBNAIL_ASPECT_RATIOS.keys()),
            index=0,
            horizontal=True
        )
        aspect_code = THUMBNAIL_ASPECT_RATIOS[aspect_label]

        if st.button("🪄 AI ဖြင့် ဆွဲဆောင်မှုရှိသော ရုပ်ရှင်ပိုစတာ ခေါင်းစဉ် (၃) မျိုး အော်တိုထုတ်မယ်", use_container_width=True):
            if not groq_key and not gemini_key:
                st.error("API Key အရင်ထည့်ပေးပါ။")
            else:
                with st.spinner("Gemini AI က Video အကြောင်းအရာကိုဖတ်ပြီး ရုပ်ရှင်ပိုစတာ ခေါင်းစဉ် (၃) မျိုး ရေးပေးနေပါသည်..."):
                    try:
                        if not st.session_state.get("script_segments"):
                            segs, ai_titles = extract_and_translate_pipeline(
                                video_path=video_temp_path,
                                groq_key=groq_key,
                                gemini_key=gemini_key,
                                gemini_model=gemini_model,
                                style_mode=style_mode
                            )
                            st.session_state["script_segments"] = segs
                        else:
                            g_cli = genai.Client(api_key=gemini_key.strip())
                            q_cli = Groq(api_key=groq_key.strip(), timeout=30.0)
                            ai_titles = generate_ai_poster_titles(g_cli, q_cli, gemini_model, st.session_state["script_segments"])

                        if len(ai_titles) >= 3:
                            st.session_state["poster_title_1"] = ai_titles[0]
                            st.session_state["poster_title_2"] = ai_titles[1]
                            st.session_state["poster_title_3"] = ai_titles[2]
                            st.rerun()
                    except Exception as e:
                        st.error(f"AI ခေါင်းစဉ်ထုတ်ရာတွင် Error တက်ပါသည်: {e}")

        st.markdown("##### ✍️ ပုံ (၃) ပုံအတွက် ရုပ်ရှင်ပိုစတာ ခေါင်းစဉ် (၃) မျိုး (စိတ်ကြိုက် ပြင်ရေးနိုင်သည်)")
        t_col1, t_col2, t_col3 = st.columns(3)
        title_1 = t_col1.text_area("ပုံ (၁) ခေါင်းစဉ်", key="poster_title_1", height=76)
        title_2 = t_col2.text_area("ပုံ (၂) ခေါင်းစဉ်", key="poster_title_2", height=76)
        title_3 = t_col3.text_area("ပုံ (၃) ခေါင်းစဉ်", key="poster_title_3", height=76)

        p_col1, p_col2 = st.columns(2)
        poster_tag = p_col1.text_input("အပေါ်ထိပ် စာတန်း (Tagline)", value="MOVIE RECAP")
        poster_font_choice = p_col2.selectbox(
            "Poster ဖောင့်ရွေးရန်",
            FONT_CHOICES,
            index=1,
            key="poster_font_select"
        )
        poster_font_path = find_font_path(poster_font_choice, custom_font_path)

        poster_color_label = st.radio(
            "Poster စာလုံးအရောင် ဒီဇိုင်း",
            list(POSTER_COLOR_PRESETS.keys()),
            index=0,
            horizontal=True
        )
        prim_hex, sec_hex = POSTER_COLOR_PRESETS[poster_color_label]

        sc_1, sc_2 = st.columns(2)
        poster_title_size = sc_1.slider("ခေါင်းစဉ် စာလုံးအရွယ် (%)", 60, 150, 100, 5)
        poster_title_y = sc_2.slider("ခေါင်းစဉ် အပေါ်/အောက် နေရာ (%)", 20, 90, 78, 2)

        max_d = max(1.0, float(vid_dur))
        with st.expander("⏱️ ပုံ (၃) ပုံ ဖမ်းယူမည့် စက္ကန့်များကို စိတ်ကြိုက်ပြင်ရန်", expanded=False):
            t1_sec = st.slider("ပုံ (၁) စက္ကန့်", 0.0, max_d, round(max_d * 0.20, 1), 0.5, key="thumb_t1")
            t2_sec = st.slider("ပုံ (၂) စက္ကန့်", 0.0, max_d, round(max_d * 0.50, 1), 0.5, key="thumb_t2")
            t3_sec = st.slider("ပုံ (၃) စက္ကန့်", 0.0, max_d, round(max_d * 0.80, 1), 0.5, key="thumb_t3")

        fsize = os.path.getsize(video_temp_path)
        thumb_configs = [
            (t1_sec, title_1),
            (t2_sec, title_2),
            (t3_sec, title_3)
        ]
        cols = st.columns(3)

        for idx, (col_ui, (t_sec, t_str)) in enumerate(zip(cols, thumb_configs), start=1):
            raw_fb = extract_frame_bytes(video_temp_path, t_sec, fsize)
            if raw_fb:
                poster_png_bytes = render_movie_poster_thumbnail(
                    frame_bytes=raw_fb,
                    title_text=t_str,
                    subtitle_tag=poster_tag,
                    font_path=poster_font_path,
                    primary_hex=prim_hex,
                    secondary_hex=sec_hex,
                    aspect_code=aspect_code,
                    title_size_pct=poster_title_size,
                    title_y_pct=poster_title_y,
                    mirror_vid=mirror_vid
                )
                with col_ui:
                    st.image(poster_png_bytes, caption=f"Poster #{idx} ({format_mm_ss(t_sec)})", use_container_width=True)
                    st.download_button(
                        f"📥 ပုံ ({idx}) ယူမယ်",
                        data=poster_png_bytes,
                        file_name=f"Movie_Poster_{idx}_{aspect_code.replace(':', 'x')}.png",
                        mime="image/png",
                        use_container_width=True,
                        key=f"dl_poster_{idx}"
            )
