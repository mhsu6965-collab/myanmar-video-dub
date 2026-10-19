import os
import re
import json
import shutil
import asyncio
import subprocess
import tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import streamlit as st
from streamlit_drawable_canvas import st_canvas
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
    "1080p Full HD (အကြည်လင်ဆုံး)",
    "720p HD (ဖိုင်ဆိုဒ်သင့်တင့်)"
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
        w = w if w % 2 == 0 else w - 1
        h = h if h % 2 == 0 else h - 1
        fps_parts = stream.get("r_frame_rate", "30/1").split("/")
        fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 and float(fps_parts[1]) != 0 else 30.0
        fps = min(60.0, max(15.0, fps))
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
        return max(2, orig_w - (orig_w % 2)), max(2, orig_h - (orig_h % 2))

    if orig_w <= orig_h:
        new_w = target_short
        new_h = int(round(orig_h * (target_short / float(orig_w))))
    else:
        new_h = target_short
        new_w = int(round(orig_w * (target_short / float(orig_h))))

    return new_w + (new_w % 2), new_h + (new_h % 2)

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

def extract_frame_image(video_path: str, time_sec: float = 2.0):
    _, _, _, dur = get_video_info(video_path)
    seek_t = min(max(0.5, float(time_sec)), max(0.5, dur - 0.5))
    frame_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg").name
    cmd = [
        "ffmpeg", "-y", "-ss", str(seek_t), "-i", video_path,
        "-frames:v", "1", "-q:v", "2", frame_file
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(frame_file):
        return Image.open(frame_file).convert("RGB")
    return None

def render_myanmar_subtitle_png(text: str, font_path: str, font_size_pt: int, stroke_px: int, vid_w: int):
    out_png = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
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
    except Exception:
        tw, th = 300, 40

    sp = max(1, int(round(stroke_px * (vid_w / 720.0))))
    img_w = tw + (sp * 4) + 24
    img_h = th + (sp * 4) + 20

    canvas = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    x_pos = (sp * 2) + 12
    y_pos = (sp * 2) + 10

    for ox in range(-sp, sp + 1):
        for oy in range(-sp, sp + 1):
            if ox != 0 or oy != 0:
                draw.text((x_pos + ox, y_pos + oy), text, font=font, fill=(0, 0, 0, 255))

    draw.text((x_pos, y_pos), text, font=font, fill=(255, 255, 255, 255))
    canvas.save(out_png, "PNG")
    return out_png, canvas.width, canvas.height

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
            return idx, trimmed_wav, dur

    return await asyncio.gather(*[_one(i, s["translated"]) for i, s in enumerate(segments)])

# Streamlit UI တည်ဆောက်ခြင်း
st.title("🎬 Pro Video Sync + 🖐️ Touch Blur + 🇲🇲 Myanmar Font Studio")
st.caption("လုံးဝမထစ်သည့် Continuous Frame-Exact Sync စနစ်နှင့် Original / 1080p / 720p HD Output")

col1, col2 = st.columns([1, 1])

with col1:
    uploaded_video = st.file_uploader("၁။ မူရင်း Video Upload တင်ရန်", type=["mp4", "mov", "mkv", "webm"])
    video_temp_path = None
    if uploaded_video:
        video_temp_path = os.path.join(tempfile.gettempdir(), uploaded_video.name)
        with open(video_temp_path, "wb") as f:
            f.write(uploaded_video.getbuffer())

    st.subheader("🖐️ ၂။ မူရင်း Subtitle ကို လက်ဖြင့်ပွတ်ဆွဲပြီး Blur ဖုံးရန်")
    hand_box = None
    if video_temp_path:
        orig_w, orig_h, vid_fps, vid_dur = get_video_info(video_temp_path)
        preview_sec = st.slider("စာတန်းပါသော စက္ကန့်ကို ရွှေ့ကြည့်ရန်", 0.5, max(1.0, float(vid_dur)), min(2.0, float(vid_dur)), 0.5)
        frame_img = extract_frame_image(video_temp_path, preview_sec)
        if frame_img:
            disp_w = 360
            disp_h = int(round(orig_h * (disp_w / float(orig_w))))
            st.caption("အောက်ပါပုံပေါ်တွင် မူရင်းစာတန်းထိုးနေရာကို လက်ဖြင့် ပွတ်ဆွဲခြယ်ပေးပါ -")
            canvas_res = st_canvas(
                fill_color="rgba(0, 255, 102, 0.4)",
                stroke_width=26,
                stroke_color="rgba(0, 255, 102, 0.8)",
                background_image=frame_img,
                update_streamlit=True,
                height=disp_h,
                width=disp_w,
                drawing_mode="freedraw",
                key="touch_blur_canvas"
            )
            if canvas_res.image_data is not None:
                alpha_mask = canvas_res.image_data[:, :, 3]
                ys, xs = np.where(alpha_mask > 15)
                if len(xs) > 10 and len(ys) > 10:
                    sx, sy = orig_w / float(disp_w), orig_h / float(disp_h)
                    x1, x2 = max(0, int(min(xs) * sx) - 6), min(orig_w, int(max(xs) * sx) + 6)
                    y1, y2 = max(0, int(min(ys) * sy) - 6), min(orig_h, int(max(ys) * sy) + 6)
                    hand_box = (x1, y1, max(16, x2 - x1), max(16, y2 - y1))
                    st.success(f"✅ Blur ဖုံးမည့်နေရာ မှတ်သားပြီးပါပြီ (X:{x1}, Y:{y1}, W:{hand_box[2]}, H:{hand_box[3]})")

    blur_power = st.slider("Blur အပြင်းအပျော့", 10, 50, 25, 5)

    st.subheader("📺 ၃။ Resolution နှင့် မြန်မာ Font ရွေးချယ်ရန်")
    res_choice = st.selectbox("ထုတ်ယူမည့် Video Resolution", RESOLUTION_CHOICES)
    font_choice = st.selectbox("မြန်မာ Font ရွေးချယ်ရန်", FONT_CHOICES)
    uploaded_font = st.file_uploader("📁 AJ 02 Regular (.ttf) သို့မဟုတ် စိတ်ကြိုက် Font တင်ရန်", type=["ttf", "otf"])

    c_a, c_b, c_c = st.columns(3)
    max_chars = c_a.slider("တစ်ကြောင်း စာလုံးရေ", 10, 35, 20, 2)
    font_size = c_b.slider("Font Size", 12, 30, 18, 1)
    outline_w = c_c.slider("Outline အထူ", 1.0, 5.0, 2.0, 0.5)

    st.subheader("🔑 ၄။ API Keys နှင့် အသံချိန်ညှိမှု")
    default_groq = st.secrets.get("GROQ_API_KEY", "") if "GROQ_API_KEY" in st.secrets else ""
    default_gemini = st.secrets.get("GEMINI_API_KEY", "") if "GEMINI_API_KEY" in st.secrets else ""
    groq_key = st.text_input("Groq API Key", value=default_groq, type="password")
    gemini_key = st.text_input("Gemini API Key", value=default_gemini, type="password")
    gemini_model = st.selectbox("Gemini Model", ["gemini-3.8-flash", "gemini-3.1-flash-lite-preview", "gemini-2.5-flash"])
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
                custom_font_path = register_uploaded_font(uploaded_font)
                active_font_path = find_font_path(font_choice, custom_font_path)

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

                status.write(f"၂/၅ - စာကြောင်း ({len(segments)}) ကြောင်းကို Gemini ဖြင့် ဘာသာပြန်နေပါသည်...")
                gemini_client = genai.Client(api_key=gemini_key.strip())
                payload = [{"id": i, "text": s["text"]} for i, s in enumerate(segments)]
                prompt = (
                    f"Translate each 'text' field into natural, concise spoken {target_lang} for video dubbing. "
                    f"Return ONLY a JSON list of objects with 'id' and 'translation':\n{json.dumps(payload, ensure_ascii=False)}"
                )
                resp = gemini_client.models.generate_content(
                    model=gemini_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                parsed = json.loads(resp.text.strip())
                t_map = {int(item["id"]): str(item.get("translation", "")).strip() for item in parsed if "id" in item}
                for i, s in enumerate(segments):
                    s["translated"] = t_map.get(i, s["text"])

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
                                png_p, pw, ph = render_myanmar_subtitle_png(c_str, active_font_path, int(font_size), int(round(outline_w)), vid_w)
                                sub_overlays.append({"png": png_p, "w": pw, "h": ph, "start": st_time, "end": et_time})
                                loc_c += c_dur
                        new_time_cursor += dur

                srt_content = "\n".join(srt_blocks)
                combined_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
                final_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
                subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", audio_list_file, "-c", "copy", combined_wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["ffmpeg", "-y", "-i", combined_wav, "-af", f"loudnorm=I=-14:TP=-1.0:LRA=11,volume={int(vol_boost)}dB", "-ar", "44100", "-b:a", "192k", final_audio], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                status.write(f"၅/၅ - လုံးဝမထစ်စေရန် Continuous Frame Sync ({vid_w}x{vid_h}) ဖြင့် Video ပေါင်းစပ်နေပါသည်...")
                # Video တစ်ပုဒ်လုံးကို အပိုင်းမဖြတ်ဘဲ Continuous Filtergraph ဖြင့် တစ်ဆက်တည်း ဆက်ပေးသဖြင့် လုံးဝမထစ်တော့ပါ
                v_filters, v_labels = [], []
                for idx, item in enumerate(timeline):
                    vs, ve = item["v_start"], item["v_end"]
                    pts_factor = max(0.05, item["target_dur"]) / max(0.05, ve - vs)
                    v_filters.append(f"[0:v]trim=start={vs:.3f}:end={ve:.3f},setpts={pts_factor:.4f}*(PTS-STARTPTS)[v{idx}]")
                    v_labels.append(f"[v{idx}]")

                v_filters.append("".join(v_labels) + f"concat=n={len(timeline)}:v=1:a=0,fps={vid_fps:.2f},scale={vid_w}:{vid_h}:flags=lanczos,setsar=1,format=yuv420p[v_base]")
                curr_v = "[v_base]"

                if hand_box is not None:
                    scale_rx, scale_ry = vid_w / float(orig_w), vid_h / float(orig_h)
                    bx_x, bx_y = int(hand_box[0] * scale_rx), int(hand_box[1] * scale_ry)
                    bx_w, bx_h = max(16, int(hand_box[2] * scale_rx)), max(16, int(hand_box[3] * scale_ry))
                    v_filters.append(
                        f"{curr_v}split=2[vm][vc];[vc]crop={bx_w}:{bx_h}:{bx_x}:{bx_y},boxblur={int(blur_power)}:2[vb];[vm][vb]overlay={bx_x}:{bx_y}[v_blur]"
                    )
                    curr_v = "[v_blur]"
                    center_y = bx_y + (bx_h // 2)
                else:
                    center_y = int(vid_h * 0.86)

                inputs_cmd = ["-i", video_temp_path, "-i", final_audio]
                for s_idx, ov in enumerate(sub_overlays):
                    inputs_cmd.extend(["-i", ov["png"]])
                    in_idx = s_idx + 2
                    ox = max(0, (vid_w - ov["w"]) // 2)
                    oy = min(max(4, center_y - (ov["h"] // 2)), vid_h - ov["h"] - 4)
                    next_v = f"[v_s{s_idx}]"
                    v_filters.append(f"{curr_v}[{in_idx}:v]overlay=x={ox}:y={oy}:enable='between(t,{ov['start']:.3f},{ov['end']:.3f})'{next_v}")
                    curr_v = next_v

                filter_script = tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".txt").name
                with open(filter_script, "w", encoding="utf-8") as fs:
                    fs.write(";\n".join(v_filters))

                out_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                subprocess.run([
                    "ffmpeg", "-y", *inputs_cmd,
                    "-filter_complex_script", filter_script,
                    "-map", curr_v, "-map", "1:a:0",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", out_video
                ], check=True)

                status.update(label="✅ အားလုံး အောင်မြင်စွာ ပြီးဆုံးပါပြီ!", state="complete", expanded=False)

                st.subheader("🎬 Final Video")
                st.video(out_video)
                with open(out_video, "rb") as vf:
                    st.download_button("📥 Final Video Download ဆွဲရန်", vf, file_name="dubbed_video.mp4", mime="video/mp4", use_container_width=True)
                st.download_button("📥 SRT Subtitle Download ဆွဲရန်", srt_content, file_name="subtitle.srt", mime="text/plain", use_container_width=True)

            except Exception as e:
                status.update(label="❌ Error ဖြစ်ပွားပါသည်", state="error")
                st.error(f"Error အသေးစိတ်: {e}")
