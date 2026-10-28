import os
import re
import json
import time
import asyncio
import subprocess
import tempfile
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
from google import genai
from google.genai import types
import edge_tts

st.set_page_config(
    page_title="RecapMM • Studio99",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==================== CLEAN LIGHT UI & NO EXTRA BORDERS ====================
st.markdown("""
<style>
    header[data-testid="stHeader"], footer, #MainMenu, div[data-testid="stDecoration"] {
        display: none !important;
    }
    .stApp {
        background-color: #F1F5F9 !important;
        color: #0F172A !important;
    }
    .block-container {
        padding-top: 0.6rem !important;
        padding-bottom: 3rem !important;
        padding-left: 0.7rem !important;
        padding-right: 0.7rem !important;
        max-width: 480px !important;
    }
    p, span, label, div[data-testid="stMarkdownContainer"] p {
        color: #1E293B !important;
    }
    .topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #0F172A;
        color: #FFFFFF;
        padding: 10px 14px;
        border-radius: 14px;
        margin-bottom: 10px;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12);
    }
    .brand-logo {
        font-size: 1.15rem;
        font-weight: 800;
        color: #F97316 !important;
    }
    .brand-logo span {
        color: #FFFFFF !important;
    }
    .badge-916 {
        background: rgba(56, 189, 248, 0.18);
        color: #38BDF8 !important;
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 0.76rem;
        font-weight: 700;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 16px !important;
        padding: 0.9rem !important;
        margin-bottom: 0.8rem !important;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04) !important;
    }
    .step-head {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
    }
    .step-num {
        width: 26px;
        height: 26px;
        border-radius: 50%;
        background: #EA580C;
        color: #FFFFFF !important;
        font-weight: 800;
        font-size: 0.85rem;
        display: inline-flex;
        align-items: center;
        justify-content: center;
    }
    .step-title {
        font-size: 1rem;
        font-weight: 800;
        color: #0F172A !important;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #EA580C 0%, #F97316 100%) !important;
        color: #FFFFFF !important;
        font-weight: 800 !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.7rem 1rem !important;
        box-shadow: 0 4px 12px rgba(234, 88, 12, 0.25) !important;
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
        padding: 0.7rem 1rem !important;
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
    "Direct Translation (မူရင်း POV အတိုင်း ဘာသာပြန်မယ်)": "direct",
    "Third Person (ပြင်ပဇာတ်ကြောင်းပြောသူအနေနဲ့ ပြောမယ်)": "third_person",
    "First Person (အဓိကဇာတ်ကောင် ကိုယ်တိုင်ပြောသလို ပြောမယ်)": "first_person"
}

COLOR_PRESETS = {
    "🔵 အပြာနု": "#38BDF8",
    "🟡 အဝါ": "#FFE600",
    "⚪ အဖြူ": "#FFFFFF",
    "🌸 ပန်းရောင်": "#F472B6"
}

FONT_CHOICES = [
    "Noto Sans (မင်္ဂလာပါ)",
    "Padauk (မင်္ဂလာပါ)",
    "AJ 02 / Custom (.ttf)"
]

def hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16), alpha)
    return (255, 255, 255, alpha)

def clean_text_for_myanmar_font(text: str) -> str:
    """လေးထောင့်ကွက် (Tofu □) လုံးဝမပေါ်စေရန် သန့်စင်ခြင်း"""
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

def get_media_duration(file_path: str) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(res.stdout.strip())
    except Exception:
        return 0.0

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

def split_into_short_lines(text: str, max_chars: int = 18) -> list:
    """9:16 ဗီဒီယိုဘောင်အပြင်သို့ စာသားလုံးဝမထွက်စေရန် စာကြောင်းတိုလေးများ ဖြတ်တောက်ခြင်း"""
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

def render_myanmar_subtitle_rgba(
    text: str, font_path: str, size_scale_pct: int, vid_w: int,
    text_hex: str = "#38BDF8"
) -> Image.Image:
    clean_txt = clean_text_for_myanmar_font(text) or " "
    base_pt = 19 * (size_scale_pct / 100.0)
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
    pad_x = int(16 * (vid_w / 720.0))
    pad_y = int(10 * (vid_w / 720.0))
    img_w = tw + (sp * 2) + (pad_x * 2)
    img_h = th + (sp * 2) + (pad_y * 2)

    canvas = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # RecapMM စတိုင် အမည်းရောင် Pill Background ဘောင်
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

    # 9:16 ဗီဒီယိုဘောင်အတွင်း 92% ထက် လုံးဝမကျော်စေရန် Auto-Fit လုပ်ခြင်း
    max_allowed_w = int(vid_w * 0.92)
    if canvas.width > max_allowed_w:
        ratio = max_allowed_w / float(canvas.width)
        canvas = canvas.resize((max_allowed_w, max(14, int(canvas.height * ratio))), Image.LANCZOS)
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
    sem = asyncio.Semaphore(8)
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

def render_916_fast_video(
    video_path: str,
    tts_audio_path: str,
    timeline: list,
    sub_overlays: list,
    out_w: int,
    out_h: int,
    vid_fps: float,
    enable_blur1: bool,
    blur1_box: tuple,
    enable_blur2: bool,
    blur2_box: tuple,
    blur_opacity_pct: int,
    show_sub: bool,
    sub_y_pct: int,
    wm_rgba: Image.Image,
    mirror_vid: bool,
    zoom_pct: int,
    brightness_val: float,
    contrast_val: float,
    saturation_val: float,
    orig_vol_pct: int,
    vo_vol_pct: int,
    progress_bar,
    step_text_placeholder
) -> str:
    """
    9:16 Portrait (720x1280) အချိုးအစားအမှန်ဖြင့် အမြန်ဆုံးနှင့် ဖိုင်ဆိုဒ်အသေးဆုံး
    Render လုပ်ပေးပြီး လုပ်ဆောင်နေသည့် အဆင့်နှင့် % ကို တိုက်ရိုက်ပြသပေးသည့် စနစ်
    """
    raw_out_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    web_ready_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name

    # 9:16 Portrait Canvas အတွင်း မူရင်း Video ကို အချိုးကျ ထည့်သွင်းခြင်း
    vf_chain = [f"fps={vid_fps:.2f}"]
    if mirror_vid:
        vf_chain.append("hflip")

    if zoom_pct != 100:
        zf = zoom_pct / 100.0
        vf_chain.append(f"scale=iw*{zf:.3f}:ih*{zf:.3f},crop=iw/{zf:.3f}:ih/{zf:.3f}")

    vf_chain.append(
        f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,"
        f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2:color=#090D16,setsar=1"
    )

    if abs(brightness_val) > 0.01 or abs(contrast_val - 1.0) > 0.01 or abs(saturation_val - 1.0) > 0.01:
        vf_chain.append(f"eq=brightness={brightness_val:.2f}:contrast={contrast_val:.2f}:saturation={saturation_val:.2f}")

    vf_chain.append("format=rgb24")
    curr_vf = ",".join(vf_chain)

    sigma_val = max(3.0, 20.0 * (blur_opacity_pct / 100.0))
    if enable_blur1 and blur_opacity_pct > 0:
        b1x, b1y, b1w, b1h = blur1_box
        curr_vf += (
            f",split=2[vm1][vc1];"
            f"[vc1]crop={b1w}:{b1h}:{b1x}:{b1y},gblur=sigma={sigma_val:.1f},eq=brightness=-0.15[vb1];"
            f"[vm1][vb1]overlay={b1x}:{b1y}"
        )

    if enable_blur2 and blur_opacity_pct > 0:
        b2x, b2y, b2w, b2h = blur2_box
        curr_vf += (
            f",split=2[vm2][vc2];"
            f"[vc2]crop={b2w}:{b2h}:{b2x}:{b2y},gblur=sigma={sigma_val:.1f},eq=brightness=-0.15[vb2];"
            f"[vm2][vb2]overlay={b2x}:{b2y}"
        )

    decoder_cmd = ["ffmpeg", "-v", "error", "-i", video_path, "-vf", curr_vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]
    encoder_cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{out_w}x{out_h}", "-pix_fmt", "rgb24", "-r", f"{vid_fps:.2f}",
        "-i", "pipe:0",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24",
        "-maxrate", "2000k", "-bufsize", "4000k",
        "-profile:v", "main", "-pix_fmt", "yuv420p", "-threads", "2",
        raw_out_video
    ]

    dec_proc = subprocess.Popen(decoder_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    enc_proc = subprocess.Popen(encoder_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    frame_bytes_len = out_w * out_h * 3
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

    sub_cy = int(out_h * (sub_y_pct / 100.0))
    wx, wy = int(out_w * 0.72), int(out_h * 0.05)

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
            frame_img = Image.frombytes("RGB", (out_w, out_h), curr_in_frame_bytes)
            if wm_rgba is not None:
                frame_img.paste(wm_rgba, (wx, wy), wm_rgba)
            if active_sub is not None:
                sub_rgba = active_sub["img"]
                ox = max(4, (out_w - sub_rgba.width) // 2)
                oy = min(max(4, sub_cy - (sub_rgba.height // 2)), out_h - sub_rgba.height - 4)
                frame_img.paste(sub_rgba, (ox, oy), sub_rgba)
            frame_to_write = frame_img.tobytes()
        else:
            frame_to_write = curr_in_frame_bytes

        try:
            enc_proc.stdin.write(frame_to_write)
            frames_written += 1
        except BrokenPipeError:
            break

        if out_idx % 20 == 0:
            pct = int((out_idx / float(total_out_frames)) * 100)
            progress_bar.progress(min(0.95, out_idx / float(total_out_frames)))
            step_text_placeholder.info(
                f"🎞️ **အဆင့် ၄/၄ ({pct}%)** - 9:16 Video Frame ({out_idx}/{total_out_frames}) တွင် Blur နှင့် မြန်မာစာတန်း ရေးဆွဲနေပါသည်..."
            )

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

    step_text_placeholder.info("🔊 နောက်ဆုံးအဆင့် (98%) - Voiceover အသံနှင့် MP4 FastStart ပေါင်းစပ်နေပါသည်...")
    vo_gain = max(0.1, vo_vol_pct / 100.0)
    if orig_vol_pct > 0:
        orig_gain = orig_vol_pct / 100.0
        af_mix = f"[1:a]volume={vo_gain:.2f}[vo];[2:a]volume={orig_gain:.2f}[oa];[vo][oa]amix=inputs=2:duration=first:normalize=0[aout]"
        subprocess.run([
            "ffmpeg", "-y", "-v", "error",
            "-i", raw_out_video, "-i", tts_audio_path, "-i", video_path,
            "-filter_complex", af_mix,
            "-map", "0:v:0", "-map", "[aout]",
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

# ==================== 9:16 INTERACTIVE LOCAL PREVIEW HTML ====================
def build_916_preview_component(b1_y: int, b1_h: int, b2_on: bool, b2_y: int, sub_y: int, sub_clr: str, wm_txt: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Myanmar:wght@700&display=swap" rel="stylesheet">
<style>
    * {{ box-sizing: border-box; user-select: none; }}
    body {{ margin: 0; padding: 0; background: transparent; font-family: 'Noto Sans Myanmar', sans-serif; }}
    .wrap-916 {{
        width: 250px;
        height: 444px;
        margin: 0 auto;
        background: #090D16;
        border-radius: 16px;
        border: 2px solid #334155;
        position: relative;
        overflow: hidden;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.18);
    }}
    video {{
        width: 100%;
        height: 100%;
        object-fit: contain;
        display: block;
    }}
    .pick-overlay {{
        position: absolute;
        top: 10px;
        left: 10px;
        right: 10px;
        display: flex;
        justify-content: space-between;
        z-index: 20;
    }}
    .pick-btn {{
        background: rgba(15, 23, 42, 0.85);
        color: #FFFFFF;
        border: 1.5px solid #14B8A6;
        padding: 5px 10px;
        border-radius: 8px;
        font-size: 0.74rem;
        font-weight: 700;
        cursor: pointer;
    }}
    .blur-box-1 {{
        position: absolute;
        left: 6%;
        width: 88%;
        top: {b1_y}%;
        height: {b1_h}%;
        backdrop-filter: blur(10px);
        background: rgba(20, 20, 20, 0.45);
        border: 2px solid #00E5FF;
        border-radius: 10px;
        pointer-events: none;
    }}
    .blur-box-2 {{
        position: absolute;
        left: 6%;
        width: 45%;
        top: {b2_y}%;
        height: 8%;
        backdrop-filter: blur(10px);
        background: rgba(20, 20, 20, 0.45);
        border: 2px solid #D946EF;
        border-radius: 8px;
        display: {'block' if b2_on else 'none'};
        pointer-events: none;
    }}
    .sub-pill {{
        position: absolute;
        left: 50%;
        top: {sub_y}%;
        transform: translate(-50%, -50%);
        width: 90%;
        text-align: center;
        background: rgba(15, 15, 15, 0.75);
        color: {sub_clr};
        padding: 5px 8px;
        border-radius: 10px;
        font-size: 0.78rem;
        font-weight: 700;
        text-shadow: 1px 1px 2px #000;
        border: 1px solid rgba(255,255,255,0.2);
        pointer-events: none;
    }}
    .wm-label {{
        position: absolute;
        right: 12px;
        top: 42px;
        color: rgba(255,255,255,0.55);
        font-size: 0.72rem;
        font-weight: 700;
        pointer-events: none;
    }}
</style>
</head>
<body>
<div class="wrap-916">
    <div class="pick-overlay">
        <label class="pick-btn">
            🖼️ Local အမြန်စမ်းကြည့်ရန်
            <input type="file" accept="video/*" style="display:none" onchange="if(this.files[0]) document.getElementById('pvVid').src=URL.createObjectURL(this.files[0])">
        </label>
    </div>
    <video id="pvVid" controls playsinline></video>
    <div class="wm-label">{wm_txt}</div>
    <div class="blur-box-2"></div>
    <div class="blur-box-1"></div>
    <div class="sub-pill">ပြန်စရာအိမ်မရှိတော့တဲ့ ဇနီးမောင်နှံ</div>
</div>
</body>
</html>
"""

# ==================== TOP BAR ====================
st.markdown("""
<div class="topbar">
    <div class="brand-logo">Recap<span>MM</span> • Studio99</div>
    <div class="badge-916">📐 9:16 Portrait Studio</div>
</div>
""", unsafe_allow_html=True)

default_groq = st.secrets.get("GROQ_API_KEY", "") if "GROQ_API_KEY" in st.secrets else ""
default_gemini = st.secrets.get("GEMINI_API_KEY", "") if "GEMINI_API_KEY" in st.secrets else ""

with st.expander("🔑 API Keys နှင့် Custom Font (.ttf) ထည့်သွင်းရန်", expanded=not (default_groq and default_gemini)):
    groq_key = st.text_input("Groq API Key (gsk_...)", value=default_groq, type="password")
    gemini_key = st.text_input("Gemini API Key (AIzaSy...)", value=default_gemini, type="password")
    gemini_model = st.selectbox("Gemini Model", ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-3.1-flash-lite-preview", "gemini-2.5-flash"])
    uploaded_font = st.file_uploader("📁 AJ 02 (.ttf) သို့မဟုတ် စိတ်ကြိုက် Font တင်ရန်", type=["ttf", "otf"])
    custom_font_path = register_uploaded_font(uploaded_font)

# ==================== GALLERY VIDEO PICKER & 9:16 PREVIEW ====================
with st.container(border=True):
    uploaded_video = st.file_uploader("🖼️ Gallery မှ ဗီဒီယို ရွေးမည် (MP4 / MOV)", type=["mp4", "mov", "mkv", "webm"])
    video_temp_path = None
    if uploaded_video:
        video_temp_path = os.path.join(tempfile.gettempdir(), "recap_source_916.mp4")
        with open(video_temp_path, "wb") as f:
            f.write(uploaded_video.getbuffer())

    st.markdown("##### 🌫️ Blur Mask နှင့် 9:16 မျက်နှာပြင် ချိန်ညှိမှု")
    b_c1, b_c2 = st.columns(2)
    enable_blur1 = b_c1.toggle("Blur 1 (အောက်စာတန်း)", value=True)
    enable_blur2 = b_c2.toggle("Blur 2 (အပေါ် Logo)", value=False)

    s_c1, s_c2, s_c3 = st.columns(3)
    blur1_y_pct = s_c1.slider("Blur 1 အပေါ်/အောက်", 10, 92, 74, 1)
    blur1_h_pct = s_c2.slider("Blur 1 အမြင့်", 4, 25, 11, 1)
    blur_opacity_pct = s_c3.slider("Blur အထူ (%)", 0, 100, 100, 5)

    if enable_blur2:
        blur2_y_pct = st.slider("Blur 2 (Logo) အပေါ်/အောက် (%)", 2, 50, 6, 1)
    else:
        blur2_y_pct = 6

    sub_y_pct = st.slider("📝 မြန်မာစာတန်း အပေါ်/အောက် နေရာ (%)", 10, 92, 78, 1)

    # 9:16 ဒေါင်လိုက် Preview Box ပြသခြင်း
    pv_html = build_916_preview_component(
        b1_y=blur1_y_pct,
        b1_h=blur1_h_pct,
        b2_on=enable_blur2,
        b2_y=blur2_y_pct,
        sub_y=sub_y_pct,
        sub_clr=COLOR_PRESETS.get(st.session_state.get("clr_state", "🔵 အပြာနု"), "#38BDF8"),
        wm_txt=st.session_state.get("wm_txt_state", "MY RECAP")
    )
    components.html(pv_html, height=455, scrolling=False)

# ==================== STEP 1: မြန်မာဘာသာပြန် SCRIPT (စာကြောင်းပြင်မည် ဖျက်ထားသည်) ====================
with st.container(border=True):
    st.markdown("""
    <div class="step-head">
        <div class="step-num">1</div>
        <div class="step-title">မြန်မာဘာသာပြန် Script ပုံစံ</div>
    </div>
    """, unsafe_allow_html=True)

    narration_label = st.radio("ဇာတ်ကြောင်းပုံစံ ရွေးပါ", list(NARRATION_STYLES.keys()), index=0)
    style_mode = NARRATION_STYLES[narration_label]

# ==================== STEP 2: VOICEOVER အသံရွေးပါ (SPEED % နှင့် PITCH % ပါဝင်သည်) ====================
with st.container(border=True):
    st.markdown("""
    <div class="step-head">
        <div class="step-num">2</div>
        <div class="step-title">Voiceover အသံ နှင့် Speed / Pitch (%)</div>
    </div>
    """, unsafe_allow_html=True)

    selected_voice_preset = st.radio("အသံအမျိုးအစား (၆ မျိုး)", list(VOICE_PRESETS.keys()), index=4)
    v_cfg = VOICE_PRESETS[selected_voice_preset]

    sp_col1, sp_col2 = st.columns(2)
    tts_speed_pct = sp_col1.slider("⚡ TTS အသံ Speed (%)", -50, 100, v_cfg["rate"], 5, format="%d%%")
    tts_pitch_pct = sp_col2.slider("🎵 TTS အသံ Pitch (%)", -50, 50, v_cfg["pitch"], 2, format="%d%%")

    audio_offset_sec = st.slider("⏱️ အသံ အစော / အနောက် ချိန် (စက္ကန့်)", -2.0, 2.0, 0.0, 0.1)

# ==================== STEP 3: VIDEO ချိန်ညှိမှု ====================
with st.container(border=True):
    st.markdown("""
    <div class="step-head">
        <div class="step-num">3</div>
        <div class="step-title">Video ချိန်ညှိမှု</div>
    </div>
    """, unsafe_allow_html=True)

    m_c1, m_c2 = st.columns(2)
    mirror_vid = m_c1.toggle("ဘယ်ညာလှည့် (Mirror)", value=False)
    show_sub = m_c2.toggle("မြန်မာစာတန်း ထည့်မယ်", value=True)

    font_choice = st.selectbox("ဖောင့် ရွေးချယ်ရန်", FONT_CHOICES, index=0)
    active_font_path = find_font_path(font_choice, custom_font_path)

    color_label = st.radio("စာလုံးအရောင်", list(COLOR_PRESETS.keys()), index=0, horizontal=True, key="clr_state")
    sub_color_hex = COLOR_PRESETS[color_label]
    sub_size_pct = st.slider("စာလုံးအရွယ် (%)", 60, 130, 90, 5, format="%d%%")

    st.divider()
    enable_wm = st.toggle("Channel Watermark ထည့်မယ်", value=True)
    if enable_wm:
        wm_text = st.text_input("Channel အမည်", value="MY RECAP", key="wm_txt_state")
        w_c1, w_c2 = st.columns(2)
        wm_opacity_pct = w_c1.slider("Watermark Opacity (%)", 10, 100, 55, 5, format="%d%%")
        wm_size_pct = w_c2.slider("Watermark အရွယ် (%)", 50, 150, 95, 5, format="%d%%")
    else:
        wm_text, wm_opacity_pct, wm_size_pct = "", 50, 95

    with st.expander("🎨 Copyright ကာကွယ်ရေး (Zoom / အလင်း / Contrast / အသံ %)", expanded=False):
        zoom_pct = st.slider("Zoom (%)", 80, 130, 100, 2, format="%d%%")
        brightness_val = st.slider("အလင်း (Brightness)", -0.3, 0.3, 0.0, 0.02)
        contrast_val = st.slider("Contrast", 0.7, 1.4, 1.0, 0.05)
        saturation_val = st.slider("အရောင် (Saturation)", 0.5, 1.5, 1.0, 0.05)
        orig_vol_pct = st.slider("မူရင်းအသံ (%)", 0, 50, 0, 5, format="%d%%")
        vo_vol_pct = st.slider("Voiceover အသံ (%)", 50, 200, 120, 10, format="%d%%")

# ==================== STEP 4: ထုတ်ယူမယ် (အဆင့်တိုင်း ဘာလုပ်နေလဲ အသေးစိတ်ပြမည်) ====================
with st.container(border=True):
    st.markdown("""
    <div class="step-head">
        <div class="step-num">4</div>
        <div class="step-title">ထုတ်ယူမယ် (Fast 9:16 HD Render)</div>
    </div>
    """, unsafe_allow_html=True)

    render_btn = st.button("📥 Recap Video ထုတ်မယ်", type="primary", use_container_width=True)

    if render_btn:
        if not video_temp_path:
            st.error("ကျေးဇူးပြု၍ အပေါ်ဆုံးရှိ 'Gallery မှ ဗီဒီယို ရွေးမည်' တွင် Video အရင်ရွေးပေးပါ။")
        elif not groq_key or not gemini_key:
            st.error("Groq နှင့် Gemini API Key နှစ်ခုလုံး ထည့်သွင်းပေးပါ။")
        else:
            step_box = st.empty()
            p_bar = st.progress(0.0)
            try:
                # 9:16 Portrait Resolution (720x1280) အတိအကျ သတ်မှတ်ခြင်း
                out_w, out_h = 720, 1280
                _, _, vid_fps, vid_dur = get_video_info(video_temp_path)

                step_box.info("🎧 **အဆင့် ၁/၄ (15%)** - ဗီဒီယိုထဲမှ အသံထုတ်ယူပြီး Groq Whisper AI ဖြင့် စကားပြောချိန်များ နားထောင်နေပါသည်...")
                p_bar.progress(0.15)
                extracted_audio = extract_compressed_audio(video_temp_path)
                groq_client = Groq(api_key=groq_key.strip())
                with open(extracted_audio, "rb") as f:
                    trans = groq_client.audio.transcriptions.create(
                        file=(extracted_audio, f.read()),
                        model="whisper-large-v3-turbo",
                        response_format="verbose_json"
                    )
                raw_segs = getattr(trans, "segments", None) or (trans.get("segments", []) if isinstance(trans, dict) else [])
                segments = merge_close_whisper_segments(raw_segs)
                if not segments:
                    raise RuntimeError("ဗီဒီယိုထဲတွင် စကားပြောသံ မတွေ့ရှိပါ။")

                step_box.info(f"🤖 **အဆင့် ၂/၄ (40%)** - စာကြောင်း ({len(segments)}) ကြောင်းကို `{gemini_model}` ဖြင့် မြန်မာဘာသာပြန်နေပါသည်...")
                p_bar.progress(0.40)
                gemini_client = genai.Client(api_key=gemini_key.strip())
                translate_segments_recap_style(gemini_client, groq_client, gemini_model, segments, style_mode)

                step_box.info(f"🗣️ **အဆင့် ၃/၄ (65%)** - Edge-TTS ဖြင့် မြန်မာ Voiceover (Speed: {tts_speed_pct:+}%, Pitch: {tts_pitch_pct:+}%) ထုတ်ယူနေပါသည်...")
                p_bar.progress(0.65)
                safe_speed = max(-99, min(100, int(tts_speed_pct)))
                safe_pitch = max(-50, min(50, int(tts_pitch_pct)))
                tts_res = asyncio.run(
                    synthesize_all_tts(segments, v_cfg["voice"], f"{safe_speed:+d}%", f"{safe_pitch:+d}Hz")
                )
                for idx, wav_p, tdur in tts_res:
                    segments[idx]["wav"] = wav_p
                    segments[idx]["tts_dur"] = tdur

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
                            short_lines = split_into_short_lines(item["text"], 18)
                            tot_c = sum(len(c) for c in short_lines) or 1
                            loc_c = 0.0
                            for c_idx, c_str in enumerate(short_lines):
                                c_dur = dur * (len(c_str) / tot_c) if c_idx < len(short_lines) - 1 else (dur - loc_c)
                                st_time = new_time_cursor + loc_c
                                et_time = st_time + c_dur
                                srt_blocks.append(f"{srt_counter}\n{format_srt_time(st_time)} --> {format_srt_time(et_time)}\n{c_str}\n")
                                srt_counter += 1
                                sub_rgba = render_myanmar_subtitle_rgba(
                                    c_str, active_font_path, int(sub_size_pct), out_w, sub_color_hex
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

                b1_box = (
                    int(out_w * 0.06),
                    min(max(0, int(out_h * (blur1_y_pct / 100.0))), out_h - 32),
                    int(out_w * 0.88),
                    max(24, int(out_h * (blur1_h_pct / 100.0)))
                )
                b2_box = (
                    int(out_w * 0.06),
                    min(max(0, int(out_h * (blur2_y_pct / 100.0))), out_h - 32),
                    int(out_w * 0.45),
                    int(out_h * 0.08)
                )

                wm_rgba = render_watermark_rgba(wm_text, active_font_path, wm_opacity_pct, wm_size_pct, out_w) if enable_wm else None

                out_video_path = render_916_fast_video(
                    video_path=video_temp_path,
                    tts_audio_path=final_audio,
                    timeline=timeline,
                    sub_overlays=sub_overlays,
                    out_w=out_w,
                    out_h=out_h,
                    vid_fps=vid_fps,
                    enable_blur1=enable_blur1,
                    blur1_box=b1_box,
                    enable_blur2=enable_blur2,
                    blur2_box=b2_box,
                    blur_opacity_pct=blur_opacity_pct,
                    show_sub=show_sub,
                    sub_y_pct=sub_y_pct,
                    wm_rgba=wm_rgba,
                    mirror_vid=mirror_vid,
                    zoom_pct=zoom_pct,
                    brightness_val=brightness_val,
                    contrast_val=contrast_val,
                    saturation_val=saturation_val,
                    orig_vol_pct=orig_vol_pct,
                    vo_vol_pct=vo_vol_pct,
                    progress_bar=p_bar,
                    step_text_placeholder=step_box
                )

                with open(out_video_path, "rb") as vf:
                    v_bytes = vf.read()
                st.session_state["final_video_bytes"] = v_bytes
                st.session_state["final_srt_content"] = srt_content
                st.session_state["final_mb_size"] = len(v_bytes) / (1024 * 1024)

                step_box.success(f"✅ အားလုံး အောင်မြင်စွာ ပြီးဆုံးပါပြီ! (9:16 HD • {st.session_state['final_mb_size']:.1f} MB)")

            except Exception as e:
                step_box.error(f"❌ Error ဖြစ်ပွားပါသည်: {e}")

    if "final_srt_content" in st.session_state and st.session_state["final_srt_content"]:
        st.download_button(
            "📄 မြန်မာ SRT Download",
            data=st.session_state["final_srt_content"],
            file_name="RecapMM_Subtitle.srt",
            mime="text/plain",
            use_container_width=True
        )

    if "final_video_bytes" in st.session_state and st.session_state["final_video_bytes"]:
        mb_val = st.session_state.get("final_mb_size", 0.0)
        st.video(st.session_state["final_video_bytes"], format="video/mp4")
        st.download_button(
            f"📥 MP4 Download ({mb_val:.1f} MB)",
            data=st.session_state["final_video_bytes"],
            file_name="RecapMM_916_Video.mp4",
            mime="video/mp4",
            use_container_width=True
    )
