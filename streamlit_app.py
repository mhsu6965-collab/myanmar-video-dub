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

st.set_page_config(page_title="Myanmar Video Dubbing Studio", page_icon="🎬", layout="wide")

USER_FONT_DIR = os.path.expanduser("~/.local/share/fonts")
os.makedirs(USER_FONT_DIR, exist_ok=True)

VOICES = {
    "Myanmar - Nilar (Female)": "my-MM-NilarNeural",
    "Myanmar - Thiha (Male)": "my-MM-ThihaNeural",
    "English - Aria (Female)": "en-US-AriaNeural",
    "English - Christopher (Male)": "en-US-ChristopherNeural",
    "Thai - Premwadee (Female)": "th-TH-PremwadeeNeural",
    "Japanese - Nanami (Female)": "ja-JP-NanamiNeural",
    "Chinese - Xiaoxiao (Female)": "zh-CN-XiaoxiaoNeural"
}

FONT_CHOICES = [
    "Noto Sans Myanmar UI Bold",
    "AJ 02 Regular"
]

RESOLUTION_CHOICES = [
    "Original Resolution (မူရင်းအတိုင်း)",
    "720p HD (ဖိုင်ဆိုဒ်သင့်တင့် - အမြန်ဆုံး)",
    "1080p Full HD (အကြည်လင်ဆုံး)"
]

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
    res = subprocess.run(
        ["fc-match", "-f", "%{file}", "Noto Sans Myanmar"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
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
        w = int(stream["width"])
        h = int(stream["height"])
        rot = int(stream.get("tags", {}).get("rotate", 0))
        if rot in (90, 270, -90, -270):
            w, h = h, w
        w = align_to_8(w)
        h = align_to_8(h)
        fps_parts = stream.get("r_frame_rate", "30/1").split("/")
        fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 and float(fps_parts[1]) != 0 else 30.0
        fps = min(30.0, max(15.0, fps))
        dur = float(data["format"]["duration"])
        return w, h, fps, dur
    except Exception:
        return 1280, 720, 30.0, 0.0

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
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", file_path
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(res.stdout.strip())
    except Exception:
        return 0.0

def extract_compressed_audio(video_path: str) -> str:
    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-ac", "1", "-ar", "16000", "-b:a", "48k", temp_audio
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return temp_audio

@st.cache_data(show_spinner=False)
def extract_frame_bytes(video_path: str, time_sec: float, file_size: int) -> bytes:
    frame_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg").name
    cmd = [
        "ffmpeg", "-y", "-ss", f"{time_sec:.2f}", "-i", video_path,
        "-frames:v", "1", "-q:v", "2", frame_file
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(frame_file) and os.path.getsize(frame_file) > 0:
        with open(frame_file, "rb") as f:
            data = f.read()
        os.remove(frame_file)
        return data
    return b""

def render_myanmar_subtitle_rgba(text: str, font_path: str, font_size_pt: int, stroke_px: int, vid_w: int) -> Image.Image:
    scaled_px = max(16, int(font_size_pt * (vid_w / 540.0)))
    try:
        font = ImageFont.truetype(font_path, scaled_px)
    except Exception:
        font = ImageFont.load_default()

    dummy_img = Image.new("RGBA", (10, 10))
    d_draw = ImageDraw.Draw(dummy_img)
    try:
        bbox = d_draw.textbbox((0, 0), text, font=font)
        tw = max(10, bbox[2] - bbox[0])
        th = max(10, bbox[3] - bbox[1])
        offset_x = -bbox[0]
        offset_y = -bbox[1]
    except Exception:
        tw, th, offset_x, offset_y = 300, 40, 0, 0

    sp = max(1, int(round(stroke_px * (vid_w / 720.0))))
    img_w = tw + (sp * 4) + 24
    img_h = th + (sp * 4) + 20

    canvas = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    x_pos = (sp * 2) + 12 + offset_x
    y_pos = (sp * 2) + 10 + offset_y

    for ox in range(-sp, sp + 1):
        for oy in range(-sp, sp + 1):
            if ox != 0 or oy != 0:
                draw.text((x_pos + ox, y_pos + oy), text, font=font, fill=(0, 0, 0, 255))

    draw.text((x_pos, y_pos), text, font=font, fill=(255, 255, 255, 255))

    max_allowed_w = int(vid_w * 0.94)
    if canvas.width > max_allowed_w:
        ratio = max_allowed_w / float(canvas.width)
        canvas = canvas.resize((max_allowed_w, max(12, int(canvas.height * ratio))), Image.LANCZOS)

    return canvas

def generate_blur_preview_image(
    frame_bytes: bytes,
    enable_blur: bool,
    x_pct: int,
    y_pct: int,
    w_pct: int,
    h_pct: int,
    blur_power: int,
    font_path: str,
    font_size_pt: int,
    outline_w: float
):
    img = Image.open(BytesIO(frame_bytes)).convert("RGBA")
    iw, ih = img.size

    bx_w = max(16, int(iw * (w_pct / 100.0)))
    bx_h = max(16, int(ih * (h_pct / 100.0)))
    bx_x = min(max(0, int((iw - bx_w) * (x_pct / 100.0))), iw - bx_w)
    bx_y = min(max(0, int(ih * (y_pct / 100.0))), ih - bx_h)

    if enable_blur:
        crop = img.crop((bx_x, bx_y, bx_x + bx_w, bx_y + bx_h))
        blurred = crop.filter(ImageFilter.GaussianBlur(radius=max(3, int(blur_power / 2))))
        img.paste(blurred, (bx_x, bx_y))
        draw = ImageDraw.Draw(img)
        draw.rectangle([bx_x, bx_y, bx_x + bx_w, bx_y + bx_h], outline=(0, 255, 102, 255), width=max(2, iw // 200))
        center_y = bx_y + (bx_h // 2)
    else:
        center_y = int(ih * (y_pct / 100.0))

    sample_png = render_myanmar_subtitle_rgba("မြန်မာစာတန်းထိုး နမူနာ", font_path, font_size_pt, int(round(outline_w)), iw)
    sx = max(0, (iw - sample_png.width) // 2)
    sy = min(max(4, center_y - (sample_png.height // 2)), ih - sample_png.height - 4)
    img.alpha_composite(sample_png, (sx, sy))

    return img.convert("RGB"), (bx_x, bx_y, bx_w, bx_h)

def split_into_short_lines(text: str, max_chars: int = 20) -> list:
    text = re.sub(r"\s+", " ", text).strip()
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

def merge_close_whisper_segments(raw_segments: list, max_gap: float = 0.4, max_dur: float = 6.5) -> list:
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

def translate_segments_with_fallback(
    gemini_client,
    groq_client,
    preferred_model: str,
    segments: list,
    target_lang: str,
    status_box
):
    fallback_models = [
        preferred_model.strip(),
        "gemini-3.1-flash-lite-preview",
        "gemini-3-flash-preview",
        "gemini-2.5-flash"
    ]
    model_chain = []
    for m in fallback_models:
        if m not in model_chain:
            model_chain.append(m)

    batch_size = 25
    for i in range(0, len(segments), batch_size):
        batch = segments[i:i + batch_size]
        payload = [{"id": idx, "text": s["text"]} for idx, s in enumerate(batch)]
        prompt = (
            f"Translate each 'text' field into natural, concise spoken {target_lang} for video dubbing. "
            f"Return ONLY a JSON list of objects with 'id' and 'translation':\n{json.dumps(payload, ensure_ascii=False)}"
        )

        translated_success = False
        for model_name in model_chain:
            for attempt in range(2):
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
                        s["translated"] = t_map.get(idx, s["text"])
                    translated_success = True
                    break
                except Exception as e:
                    err_str = str(e)
                    if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str:
                        status_box.write(f"⚠️ `{model_name}` Server ခေတ္တကျပ်နေသဖြင့် အရန် Model ဖြင့် အလိုအလျောက် ပြောင်းလဲချိတ်ဆက်နေပါသည်...")
                        time.sleep(2)
                        continue
                    else:
                        break
            if translated_success:
                break

        if not translated_success:
            status_box.write("🔄 Gemini Server ကျပ်နေသဖြင့် Groq (Llama-3.3-70B) Backup စနစ်ဖြင့် ဘာသာပြန်နေပါသည်...")
            try:
                groq_resp = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {
                            "role": "system",
                            "content": f"You are a professional video dubbing translator. Translate accurately into natural spoken {target_lang}. Output valid JSON only."
                        },
                        {
                            "role": "user",
                            "content": f"Return a JSON object with key 'items' containing a list of objects with 'id' and 'translation':\n{json.dumps(payload, ensure_ascii=False)}"
                        }
                    ],
                    response_format={"type": "json_object"}
                )
                g_data = json.loads(groq_resp.choices[0].message.content)
                g_list = g_data.get("items", g_data) if isinstance(g_data, dict) else g_data
                t_map = {int(item["id"]): str(item.get("translation", "")).strip() for item in g_list if isinstance(item, dict) and "id" in item}
                for idx, s in enumerate(batch):
                    s["translated"] = t_map.get(idx, s["text"])
            except Exception as final_err:
                raise RuntimeError(f"ဘာသာပြန်ရာတွင် အခက်အခဲဖြစ်ပွားပါသည်: {final_err}")

async def synthesize_all_tts(segments, voice_id, rate_str, pitch_str):
    sem = asyncio.Semaphore(6)
    async def _one(idx, text):
        async with sem:
            raw_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
            trimmed_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
            comm = edge_tts.Communicate(text=text, voice=voice_id, rate=rate_str, pitch=pitch_str)
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

def render_smooth_final_video(
    video_path: str,
    audio_path: str,
    timeline: list,
    sub_overlays: list,
    vid_w: int,
    vid_h: int,
    vid_fps: float,
    enable_blur: bool,
    blur_box_norm: tuple,
    blur_power: int,
    progress_bar
) -> str:
    raw_out_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    web_ready_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name

    bx_x, bx_y, bx_w, bx_h = blur_box_norm
    # boxblur အစား ဘောင်အရွယ်အစားမရွေး ၁၀၀% အလုပ်လုပ်သော gblur (Gaussian Blur) သုံးထားသည်
    sigma_val = max(2.0, float(blur_power))

    if enable_blur and bx_w >= 8 and bx_h >= 8:
        decode_vf = (
            f"fps={vid_fps:.2f},scale={vid_w}:{vid_h}:flags=bicubic,setsar=1,format=rgb24,"
            f"split=2[vm][vc];[vc]crop={bx_w}:{bx_h}:{bx_x}:{bx_y},gblur=sigma={sigma_val:.1f}[vb];"
            f"[vm][vb]overlay={bx_x}:{bx_y}"
        )
    else:
        decode_vf = f"fps={vid_fps:.2f},scale={vid_w}:{vid_h}:flags=bicubic,setsar=1,format=rgb24"

    center_y = bx_y + (bx_h // 2)

    decoder_cmd = [
        "ffmpeg", "-v", "error", "-i", video_path,
        "-vf", decode_vf,
        "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"
    ]
    encoder_cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{vid_w}x{vid_h}", "-pix_fmt", "rgb24", "-r", f"{vid_fps:.2f}",
        "-i", "pipe:0",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
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
        time_segments.append({
            "out_start": out_cursor,
            "out_end": out_cursor + td,
            "in_start": item["v_start"],
            "in_end": item["v_end"]
        })
        out_cursor += td

    curr_in_frame_idx = -1
    curr_in_frame_bytes = None
    eof_reached = False
    seg_ptr = 0
    sub_ptr = 0
    num_subs = len(sub_overlays)
    frames_written = 0

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

        while sub_ptr < num_subs and sub_overlays[sub_ptr]["end"] < t_out:
            sub_ptr += 1

        active_sub = None
        if sub_ptr < num_subs and sub_overlays[sub_ptr]["start"] <= t_out <= sub_overlays[sub_ptr]["end"]:
            active_sub = sub_overlays[sub_ptr]

        if active_sub is not None:
            frame_img = Image.frombytes("RGB", (vid_w, vid_h), curr_in_frame_bytes)
            sub_rgba = active_sub["img"]
            ox = max(0, (vid_w - sub_rgba.width) // 2)
            oy = min(max(4, center_y - (sub_rgba.height // 2)), vid_h - sub_rgba.height - 4)
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

    mux_cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", raw_out_video,
        "-i", audio_path,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest", web_ready_video
    ]
    subprocess.run(mux_cmd, check=True)

    if os.path.exists(raw_out_video):
        os.remove(raw_out_video)

    progress_bar.progress(1.0)
    return web_ready_video

# Streamlit UI တည်ဆောက်ခြင်း
st.title("🎬 Pro Video Sync + 🌫️ Live Blur Preview + 🇲🇲 Myanmar Font Studio")
st.caption("24/7 Active Streamlit Cloud Studio (Gaussian Blur + FastStart Player + Auto 503-Fallback)")

col1, col2 = st.columns([1, 1])

with col1:
    uploaded_video = st.file_uploader("၁။ မူရင်း Video Upload တင်ရန်", type=["mp4", "mov", "mkv", "webm"])
    video_temp_path = None
    if uploaded_video:
        video_temp_path = os.path.join(tempfile.gettempdir(), "input_source_video.mp4")
        with open(video_temp_path, "wb") as f:
            f.write(uploaded_video.getbuffer())

    st.subheader("📺 ၂။ Resolution နှင့် မြန်မာ Font ရွေးချယ်ရန်")
    res_choice = st.selectbox("ထုတ်ယူမည့် Video Resolution", RESOLUTION_CHOICES)
    font_choice = st.selectbox("မြန်မာ Font ရွေးချယ်ရန်", FONT_CHOICES)
    uploaded_font = st.file_uploader("📁 AJ 02 Regular (.ttf) သို့မဟုတ် စိတ်ကြိုက် Font တင်ရန်", type=["ttf", "otf"])

    custom_font_path = register_uploaded_font(uploaded_font)
    active_font_path = find_font_path(font_choice, custom_font_path)

    c_a, c_b, c_c = st.columns(3)
    max_chars = c_a.slider("တစ်ကြောင်း စာလုံးရေ", 10, 35, 20, 2)
    font_size = c_b.slider("Font Size", 12, 30, 18, 1)
    outline_w = c_c.slider("Outline အထူ", 1.0, 5.0, 2.0, 0.5)

    st.subheader("🌫️ ၃။ မူရင်း Subtitle ကို Blur ဖုံးရန်နှင့် နေရာရွှေ့ရန် (Live Preview)")
    enable_blur = st.checkbox("မူရင်း Subtitle ကို Blur ဖုံးအုပ်မည်", value=True)
    b1, b2 = st.columns(2)
    blur_y_pct = b1.slider("အပေါ်/အောက် နေရာ (Y %)", 5, 95, 82, 1)
    blur_h_pct = b2.slider("Blur အမြင့် (Height %)", 4, 35, 12, 1)
    b3, b4 = st.columns(2)
    blur_w_pct = b3.slider("Blur အကျယ် (Width %)", 20, 100, 88, 2)
    blur_x_pct = b4.slider("ဘယ်/ညာ နေရာ (X %)", 0, 100, 50, 2)
    blur_power = st.slider("Blur အပြင်းအပျော့", 10, 50, 25, 5)

    if video_temp_path:
        orig_w, orig_h, vid_fps, vid_dur = get_video_info(video_temp_path)
        preview_sec = st.slider("စာတန်းပါသော စက္ကန့်ကို ရွှေ့ကြည့်ရန်", 0.5, max(1.0, float(vid_dur)), min(2.0, float(vid_dur)), 0.5)
        frame_bytes = extract_frame_bytes(video_temp_path, preview_sec, os.path.getsize(video_temp_path))
        if frame_bytes:
            preview_img, _ = generate_blur_preview_image(
                frame_bytes, enable_blur, blur_x_pct, blur_y_pct, blur_w_pct, blur_h_pct,
                blur_power, active_font_path, font_size, outline_w
            )
            st.image(preview_img, caption="👁️ Blur ဘောင်နှင့် မြန်မာစာတန်းထိုး ပေါ်မည့်နေရာ နမူနာပုံ", use_container_width=True)

    st.subheader("🔑 ၄။ API Keys နှင့် အသံချိန်ညှိမှု")
    default_groq = st.secrets.get("GROQ_API_KEY", "") if "GROQ_API_KEY" in st.secrets else ""
    default_gemini = st.secrets.get("GEMINI_API_KEY", "") if "GEMINI_API_KEY" in st.secrets else ""
    groq_key = st.text_input("Groq API Key", value=default_groq, type="password")
    gemini_key = st.text_input("Gemini API Key", value=default_gemini, type="password")
    gemini_model = st.selectbox(
        "Gemini Model (Server ကျပ်ပါက အလိုအလျောက် အရန် Model ပြောင်းပေးမည်)",
        ["gemini-3.8-flash", "gemini-3.1-flash-lite-preview", "gemini-3-flash-preview", "gemini-2.5-flash"]
    )
    target_lang = st.selectbox("ဘာသာပြန်မည့် ဘာသာစကား", ["Burmese (Myanmar)", "English", "Thai", "Japanese", "Chinese"])
    voice_label = st.selectbox("TTS အသံ ရွေးချယ်ရန်", list(VOICES.keys()))

    s_a, s_b, s_c = st.columns(3)
    speed_pct = s_a.slider("TTS Speed (%)", -100, 100, 0, 5)
    pitch_hz = s_b.slider("TTS Pitch (Hz)", -50, 50, 0, 2)
    vol_boost = s_c.slider("Volume Boost (dB)", 0, 15, 6, 1)

    start_btn = st.button("🚀 စတင်ပေါင်းစပ်မည် (Generate Smooth HD Video)", type="primary", use_container_width=True)

with col2:
    if start_btn:
        if not video_temp_path:
            st.error("ကျေးဇူးပြု၍ Video ဖိုင် အရင် Upload တင်ပေးပါ။")
        elif not groq_key or not gemini_key:
            st.error("Groq API Key နှင့် Gemini API Key နှစ်ခုလုံး ထည့်ပေးပါ။")
        else:
            status = st.status("⏳ Video စတင်ပြုလုပ်နေပါသည်...", expanded=True)
            try:
                orig_w, orig_h, vid_fps, vid_dur = get_video_info(video_temp_path)
                vid_w, vid_h = calculate_target_resolution(orig_w, orig_h, res_choice)

                status.write("၁/၅ - Groq Whisper ဖြင့် စကားပြောချိန်များ ထုတ်ယူနေပါသည်...")
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

                status.write(f"၂/၅ - စာကြောင်း ({len(segments)}) ကြောင်းကို AI ဖြင့် ဘာသာပြန်နေပါသည်...")
                gemini_client = genai.Client(api_key=gemini_key.strip())
                translate_segments_with_fallback(
                    gemini_client=gemini_client,
                    groq_client=groq_client,
                    preferred_model=gemini_model,
                    segments=segments,
                    target_lang=target_lang,
                    status_box=status
                )

                status.write("၃/၅ - Edge-TTS အသံများကို ပြိုင်တူ ထုတ်ယူနေပါသည်...")
                safe_speed = max(-99, min(100, int(speed_pct)))
                tts_res = asyncio.run(synthesize_all_tts(segments, VOICES[voice_label], f"{safe_speed:+d}%", f"{int(pitch_hz):+d}Hz"))
                for idx, wav_p, tdur in tts_res:
                    segments[idx]["wav"] = wav_p
                    segments[idx]["tts_dur"] = tdur

                status.write("၄/၅ - မြန်မာစာတန်းထိုးများနှင့် အသံလမ်းကြောင်း တည်ဆောက်နေပါသည်...")
                timeline, cursor = [], 0.0
                for seg in segments:
                    s_start = max(cursor, seg["start"])
                    s_end = max(s_start + 0.1, seg["end"])
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
                            short_lines = split_into_short_lines(item["text"], int(max_chars))
                            tot_c = sum(len(c) for c in short_lines) or 1
                            loc_c = 0.0
                            for c_idx, c_str in enumerate(short_lines):
                                c_dur = dur * (len(c_str) / tot_c) if c_idx < len(short_lines) - 1 else (dur - loc_c)
                                st_time = new_time_cursor + loc_c
                                et_time = st_time + c_dur
                                srt_blocks.append(f"{srt_counter}\n{format_srt_time(st_time)} --> {format_srt_time(et_time)}\n{c_str}\n")
                                srt_counter += 1
                                sub_rgba = render_myanmar_subtitle_rgba(c_str, active_font_path, int(font_size), int(round(outline_w)), vid_w)
                                sub_overlays.append({"img": sub_rgba, "start": st_time, "end": et_time})
                                loc_c += c_dur
                        new_time_cursor += dur

                srt_content = "\n".join(srt_blocks)
                combined_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
                final_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
                subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", audio_list_file, "-c", "copy", combined_wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["ffmpeg", "-y", "-i", combined_wav, "-af", f"loudnorm=I=-14:TP=-1.0:LRA=11,volume={int(vol_boost)}dB", "-ar", "44100", "-b:a", "192k", final_audio], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                status.write(f"၅/၅ - လုံးဝမထစ်စေရန် Direct Frame-Pipe ({vid_w}x{vid_h}) ဖြင့် Video ပေါင်းစပ်နေပါသည်...")
                p_bar = st.progress(0.0)

                bx_w = max(16, int(vid_w * (blur_w_pct / 100.0)))
                bx_h = max(16, int(vid_h * (blur_h_pct / 100.0)))
                bx_x = min(max(0, int((vid_w - bx_w) * (blur_x_pct / 100.0))), vid_w - bx_w)
                bx_y = min(max(0, int(vid_h * (blur_y_pct / 100.0))), vid_h - bx_h)

                out_video_path = render_smooth_final_video(
                    video_path=video_temp_path,
                    audio_path=final_audio,
                    timeline=timeline,
                    sub_overlays=sub_overlays,
                    vid_w=vid_w,
                    vid_h=vid_h,
                    vid_fps=vid_fps,
                    enable_blur=enable_blur,
                    blur_box_norm=(bx_x, bx_y, bx_w, bx_h),
                    blur_power=blur_power,
                    progress_bar=p_bar
                )

                with open(out_video_path, "rb") as vf:
                    st.session_state["final_video_bytes"] = vf.read()
                st.session_state["final_srt_content"] = srt_content
                st.session_state["final_res_label"] = f"{vid_w}x{vid_h}"

                status.update(label=f"✅ အားလုံး အောင်မြင်စွာ ပြီးဆုံးပါပြီ! ({vid_w}x{vid_h})", state="complete", expanded=False)

            except Exception as e:
                status.update(label="❌ Error ဖြစ်ပွားပါသည်", state="error")
                st.error(f"Error အသေးစိတ်: {e}")

    if "final_video_bytes" in st.session_state and st.session_state["final_video_bytes"]:
        st.subheader(f"🎬 Final Video ({st.session_state.get('final_res_label', '')})")
        st.video(st.session_state["final_video_bytes"], format="video/mp4")
        st.download_button(
            "📥 Final Video Download ဆွဲရန်",
            data=st.session_state["final_video_bytes"],
            file_name="myanmar_dubbed_video.mp4",
            mime="video/mp4",
            use_container_width=True
        )
        st.download_button(
            "📥 SRT Subtitle Download ဆွဲရန်",
            data=st.session_state.get("final_srt_content", ""),
            file_name="myanmar_subtitle.srt",
            mime="text/plain",
            use_container_width=True
                        )
