import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Studio99 & RecapMM Local Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Streamlit ရဲ့ အပေါ်အောက်ဘောင်များကို ဖျောက်ပြီး Iframe ကို ဖုန်းမျက်နှာပြင်အပြည့် (100dvh) ချိတ်ဆက်ခြင်း
st.markdown("""
<style>
    header[data-testid="stHeader"], footer, #MainMenu, div[data-testid="stDecoration"] {
        display: none !important;
    }
    html, body, .stApp {
        background-color: #F1F5F9 !important;
        margin: 0 !important;
        padding: 0 !important;
        height: 100dvh !important;
        overflow: hidden !important;
    }
    .block-container {
        padding: 0 !important;
        margin: 0 !important;
        max-width: 100% !important;
        height: 100dvh !important;
    }
    div[data-testid="stVerticalBlock"] {
        gap: 0 !important;
        height: 100dvh !important;
    }
    iframe {
        border: none !important;
        width: 100vw !important;
        height: 100dvh !important;
        display: block !important;
    }
</style>
""", unsafe_allow_html=True)

default_groq = st.secrets.get("GROQ_API_KEY", "") if "GROQ_API_KEY" in st.secrets else ""
default_gemini = st.secrets.get("GEMINI_API_KEY", "") if "GEMINI_API_KEY" in st.secrets else ""

APP_HTML = f"""
<!DOCTYPE html>
<html lang="my">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Myanmar:wght@400;600;700;800&family=Noto+Serif+Myanmar:wght@700&family=Padauk:wght@700&display=swap" rel="stylesheet">
<style>
    :root {{
        --bg-main: #F1F5F9;
        --bg-card: #FFFFFF;
        --text-dark: #0F172A;
        --text-muted: #475569;
        --border-clr: #CBD5E1;
        --accent-orange: #EA580C;
        --accent-blue: #0284C7;
    }}
    * {{
        box-sizing: border-box;
        -webkit-tap-highlight-color: transparent;
    }}
    html, body {{
        margin: 0;
        padding: 0;
        width: 100%;
        height: 100dvh;
        background-color: var(--bg-main);
        font-family: 'Noto Sans Myanmar', sans-serif;
        color: var(--text-dark);
        overflow: hidden;
    }}
    /* မျက်နှာပြင်ကို အပေါ် (Fixed Video) နှင့် အောက် (Scrollable Tools) နှစ်ပိုင်းခွဲသည့် Layout */
    .split-layout {{
        display: flex;
        flex-direction: column;
        width: 100%;
        max-width: 500px;
        height: 100dvh;
        margin: 0 auto;
        background: var(--bg-main);
    }}
    /* ၁။ အပေါ်ပိုင်း FIXED VIDEO HEADER (လုံးဝ မရွေ့ပါ) */
    .fixed-video-pane {{
        flex: 0 0 auto;
        background: #FFFFFF;
        border-bottom: 2px solid #CBD5E1;
        padding: 8px 10px 10px 10px;
        z-index: 100;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08);
    }}
    .topbar-compact {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
    }}
    .brand-logo {{
        font-size: 1.05rem;
        font-weight: 800;
        color: #EA580C;
    }}
    .brand-logo span {{
        color: #0F172A;
    }}
    .top-right-btns {{
        display: flex;
        align-items: center;
        gap: 6px;
    }}
    .mini-gallery-btn {{
        background: #0F172A;
        color: #FFFFFF;
        border: 1.5px solid #14B8A6;
        padding: 5px 10px;
        border-radius: 8px;
        font-size: 0.78rem;
        font-weight: 700;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }}
    .key-btn {{
        background: #F1F5F9;
        color: #0F172A;
        border: 1px solid #CBD5E1;
        border-radius: 8px;
        padding: 5px 8px;
        font-size: 0.78rem;
        font-weight: 700;
        cursor: pointer;
    }}
    .canvas-stage {{
        position: relative;
        width: 100%;
        height: 235px;
        background: #090D16;
        border-radius: 12px;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1px solid #334155;
        touch-action: none;
    }}
    canvas {{
        max-width: 100%;
        max-height: 100%;
        display: block;
        touch-action: none;
    }}
    .player-bar {{
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 6px;
        padding: 4px 8px;
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
    }}
    .play-Pause-btn {{
        background: var(--accent-orange);
        color: #FFFFFF;
        border: none;
        border-radius: 6px;
        width: 32px;
        height: 28px;
        font-size: 0.9rem;
        font-weight: bold;
        cursor: pointer;
    }}
    .seek-bar {{
        flex: 1;
        accent-color: var(--accent-orange);
        height: 5px;
    }}
    .time-label {{
        font-size: 0.74rem;
        font-weight: 700;
        color: var(--text-muted);
        min-width: 68px;
        text-align: right;
    }}

    /* ၂။ အောက်ပိုင်း SCROLLABLE TOOLS PANE (အောက်ဆုံးအထိ လွတ်လပ်စွာ ဆွဲနိုင်သည်) */
    .scrollable-tools-pane {{
        flex: 1 1 auto;
        overflow-y: auto;
        -webkit-overflow-scrolling: touch;
        padding: 12px 10px 90px 10px;
    }}
    .card {{
        background: var(--bg-card);
        border: 1px solid var(--border-clr);
        border-radius: 16px;
        padding: 14px;
        margin-bottom: 12px;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
    }}
    .step-head {{
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 10px;
    }}
    .step-num {{
        width: 26px;
        height: 26px;
        border-radius: 50%;
        background: var(--accent-orange);
        color: #FFFFFF;
        font-weight: 800;
        font-size: 0.85rem;
        display: inline-flex;
        align-items: center;
        justify-content: center;
    }}
    .step-title {{
        font-size: 1rem;
        font-weight: 800;
        color: var(--text-dark);
    }}
    /* BLUR MASK TOGGLES */
    .blur-item {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 9px 12px;
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        margin-bottom: 8px;
    }}
    .switch {{
        position: relative;
        display: inline-block;
        width: 44px;
        height: 24px;
    }}
    .switch input {{ opacity: 0; width: 0; height: 0; }}
    .slider-pill {{
        position: absolute;
        cursor: pointer;
        top: 0; left: 0; right: 0; bottom: 0;
        background-color: #CBD5E1;
        transition: .25s;
        border-radius: 24px;
    }}
    .slider-pill:before {{
        position: absolute;
        content: "";
        height: 18px;
        width: 18px;
        left: 3px;
        bottom: 3px;
        background-color: white;
        transition: .25s;
        border-radius: 50%;
    }}
    input:checked + .slider-pill.cyan {{ background-color: #0284C7; }}
    input:checked + .slider-pill.pink {{ background-color: #C026D3; }}
    input:checked + .slider-pill.orange {{ background-color: var(--accent-orange); }}
    input:checked + .slider-pill:before {{ transform: translateX(20px); }}

    /* RATIO BUTTONS */
    .ratio-row {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
        margin: 8px 0;
    }}
    .r-btn {{
        padding: 8px 4px;
        background: #F8FAFC;
        border: 1.5px solid #CBD5E1;
        border-radius: 10px;
        font-weight: 800;
        color: #334155;
        text-align: center;
        cursor: pointer;
        font-size: 0.84rem;
    }}
    .r-btn.active {{
        background: #FFF7ED;
        border-color: var(--accent-orange);
        color: var(--accent-orange);
    }}
    /* NARRATION & VOICE CARDS */
    .select-card {{
        padding: 10px 12px;
        border: 1.5px solid #E2E8F0;
        background: #F8FAFC;
        border-radius: 12px;
        margin-bottom: 8px;
        cursor: pointer;
    }}
    .select-card.active {{
        background: var(--accent-orange);
        border-color: var(--accent-orange);
        color: #FFFFFF !important;
    }}
    .select-card.active .sc-title, .select-card.active .sc-sub {{
        color: #FFFFFF !important;
    }}
    .sc-title {{ font-weight: 800; font-size: 0.88rem; color: var(--text-dark); }}
    .sc-sub {{ font-size: 0.78rem; color: var(--text-muted); margin-top: 2px; }}

    .voice-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 9px 12px;
        border: 1.5px solid #E2E8F0;
        background: #F8FAFC;
        border-radius: 12px;
        margin-bottom: 7px;
        cursor: pointer;
    }}
    .voice-row.active {{
        border-color: var(--accent-orange);
        background: #FFF7ED;
    }}
    .v-sample-btn {{
        background: #E2E8F0;
        border: none;
        border-radius: 50%;
        width: 28px;
        height: 28px;
        font-size: 0.78rem;
        cursor: pointer;
    }}
    /* ACTION BUTTONS */
    .btn-primary {{
        width: 100%;
        padding: 12px;
        background: linear-gradient(90deg, #EA580C 0%, #F97316 100%);
        color: #FFFFFF;
        border: none;
        border-radius: 12px;
        font-weight: 800;
        font-size: 0.94rem;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(234, 88, 12, 0.22);
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
    }}
    .btn-secondary {{
        width: 100%;
        padding: 10px;
        background: #F1F5F9;
        color: #0F172A;
        border: 1px solid #CBD5E1;
        border-radius: 10px;
        font-weight: 700;
        font-size: 0.86rem;
        cursor: pointer;
        margin-bottom: 8px;
    }}
    /* SCRIPT SEGMENT LIST */
    .seg-box {{
        background: #F8FAFC;
        border: 1px solid #CBD5E1;
        border-radius: 10px;
        padding: 8px;
        margin-bottom: 8px;
    }}
    .seg-top {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
    }}
    .seg-time {{
        background: #E2E8F0;
        color: #1E293B;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 2px 7px;
        border-radius: 6px;
    }}
    .seg-del {{
        background: none;
        border: none;
        color: #EF4444;
        cursor: pointer;
        font-size: 0.95rem;
    }}
    .seg-input {{
        width: 100%;
        border: 1px solid #CBD5E1;
        border-radius: 8px;
        padding: 7px;
        font-family: 'Noto Sans Myanmar', sans-serif;
        font-size: 0.86rem;
        color: #0F172A;
        background: #FFFFFF;
        resize: vertical;
    }}
    /* FONT GRID */
    .font-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin: 8px 0;
    }}
    .font-card {{
        padding: 9px;
        border: 1.5px solid #CBD5E1;
        border-radius: 10px;
        background: #F8FAFC;
        text-align: center;
        cursor: pointer;
    }}
    .font-card.active {{
        border-color: var(--accent-orange);
        background: #FFF7ED;
    }}
    .color-row {{
        display: flex;
        gap: 14px;
        margin: 8px 0;
    }}
    .c-swatch {{
        width: 32px;
        height: 32px;
        border-radius: 50%;
        cursor: pointer;
        border: 2px solid #94A3B8;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
    }}
    .c-swatch.active {{
        border: 3px solid var(--accent-orange);
        transform: scale(1.1);
    }}
    .slider-group {{ margin-bottom: 10px; }}
    .slider-head {{
        display: flex;
        justify-content: space-between;
        font-size: 0.82rem;
        font-weight: 700;
        margin-bottom: 3px;
    }}
    .full-slider {{ width: 100%; accent-color: var(--accent-orange); }}
    .status-banner {{
        margin-top: 8px;
        padding: 9px;
        border-radius: 10px;
        background: #EFF6FF;
        border: 1px solid #BFDBFE;
        color: #1E40AF;
        font-size: 0.82rem;
        font-weight: 600;
        display: none;
    }}
</style>
</head>
<body>

<div class="split-layout">

    <!-- ==================== ၁။ အပေါ်ပိုင်း FIXED VIDEO PANE (အသေထားရှိသည့်အပိုင်း) ==================== -->
    <div class="fixed-video-pane">
        <div class="topbar-compact">
            <div class="brand-logo">Recap<span>MM</span> • Studio99</div>
            <div class="top-right-btns">
                <label class="mini-gallery-btn">
                    <span>🖼️ Gallery မှ ရွေးမည်</span>
                    <input type="file" id="galleryVideoInput" accept="video/*" style="display:none">
                </label>
                <button class="key-btn" onclick="toggleApiModal()">🔑 Keys</button>
            </div>
        </div>

        <div class="canvas-stage">
            <canvas id="mainCanvas" width="540" height="960"></canvas>
        </div>

        <div class="player-bar">
            <button class="play-Pause-btn" id="playBtn">▶</button>
            <input type="range" class="seek-bar" id="seekBar" min="0" max="100" step="0.05" value="0">
            <span class="time-label" id="timeLabel">0:00 / 0:00</span>
        </div>
    </div>

    <!-- ==================== ၂။ အောက်ပိုင်း SCROLLABLE TOOLS PANE (အောက်သို့ ဆွဲကြည့်နိုင်သည့်အပိုင်း) ==================== -->
    <div class="scrollable-tools-pane">

        <!-- API KEYS DRAWER -->
        <div class="card" id="apiModal" style="display:none; border-color:#0284C7;">
            <div class="step-title" style="margin-bottom:8px;">🔑 API Keys & Gemini 3.5</div>
            <div style="margin-bottom:8px;">
                <label style="font-size:0.78rem;font-weight:700;">Groq API Key:</label>
                <input type="password" id="groqKeyInput" value="{default_groq}" placeholder="gsk_..." style="width:100%;padding:8px;border-radius:8px;border:1px solid #CBD5E1;margin-top:3px;">
            </div>
            <div style="margin-bottom:8px;">
                <label style="font-size:0.78rem;font-weight:700;">Gemini API Key:</label>
                <input type="password" id="geminiKeyInput" value="{default_gemini}" placeholder="AIzaSy..." style="width:100%;padding:8px;border-radius:8px;border:1px solid #CBD5E1;margin-top:3px;">
            </div>
            <button class="btn-secondary" style="margin-bottom:0;" onclick="saveKeysToLocal()">✅ သိမ်းဆည်းမည်</button>
        </div>

        <!-- BLUR MASK & RATIO CARD -->
        <div class="card">
            <div class="step-title" style="margin-bottom:8px;">🌫️ Blur Mask (Video ပေါ်တွင် Blur ကို လက်ဖြင့်ဆွဲရွှေ့ပါ)</div>
            <div style="font-size:0.76rem;color:var(--text-muted);margin-bottom:8px;">📌 မူရင်း Video ကို ရွှေ့မရအောင် ပုံသေထားပေးထားပါသည်။ Blur နှင့် စာတန်းကိုသာ လက်ဖြင့် ဖိဆွဲရွှေ့နိုင်ပါသည်။</div>

            <div class="blur-item">
                <div style="display:flex;align-items:center;gap:10px;">
                    <label class="switch">
                        <input type="checkbox" id="blur1Chk" checked>
                        <span class="slider-pill cyan"></span>
                    </label>
                    <span style="font-weight:700;color:#0284C7;font-size:0.88rem;">Blur 1 (အောက်စာတန်း)</span>
                </div>
                <button class="btn-secondary" style="width:auto;padding:4px 9px;margin:0;font-size:0.76rem;" onclick="resetBlur1()">နေရာပြန်ချိန်</button>
            </div>

            <div class="blur-item">
                <div style="display:flex;align-items:center;gap:10px;">
                    <label class="switch">
                        <input type="checkbox" id="blur2Chk">
                        <span class="slider-pill pink"></span>
                    </label>
                    <span style="font-weight:700;color:#C026D3;font-size:0.88rem;">Blur 2 (အပေါ် Logo)</span>
                </div>
                <button class="btn-secondary" style="width:auto;padding:4px 9px;margin:0;font-size:0.76rem;" onclick="clearAllBlurs()">🗑️ Blur အားလုံးဖျက်</button>
            </div>

            <div class="slider-group" style="margin-top:8px;">
                <div class="slider-head">
                    <span>Blur အထူ (Opacity)</span>
                    <span id="blurOpVal">100%</span>
                </div>
                <input type="range" class="full-slider" id="blurOpacity" min="0" max="100" value="100" oninput="document.getElementById('blurOpVal').innerText=this.value+'%'">
            </div>

            <hr style="border:none;border-top:1px solid #E2E8F0;margin:10px 0;">

            <div class="step-title" style="font-size:0.92rem;">📐 Video Ratio & Background</div>
            <div class="ratio-row">
                <div class="r-btn active" onclick="changeRatio('9:16', this)">9:16</div>
                <div class="r-btn" onclick="changeRatio('16:9', this)">16:9</div>
                <div class="r-btn" onclick="changeRatio('1:1', this)">1:1</div>
                <div class="r-btn" onclick="changeRatio('4:3', this)">4:3</div>
            </div>
            <label class="btn-secondary" style="display:flex;align-items:center;justify-content:center;gap:6px;margin-bottom:0;">
                <span>🏞️ 9:16 နောက်ခံပုံ (Background) တင်မည်</span>
                <input type="file" id="bgFileInput" accept="image/*" style="display:none">
            </label>
        </div>

        <!-- STEP 1: မြန်မာဘာသာပြန် SCRIPT -->
        <div class="card">
            <div class="step-head">
                <div class="step-num">1</div>
                <div class="step-title">မြန်မာဘာသာပြန် Script</div>
            </div>

            <div class="select-card active" onclick="selectNarration('direct', this)">
                <div class="sc-title">Direct Translation</div>
                <div class="sc-sub">မူရင်း POV နှင့် အဓိပ္ပာယ်ကို မပြောင်းဘဲ ဘာသာပြန်မယ်</div>
            </div>
            <div class="select-card" onclick="selectNarration('third', this)">
                <div class="sc-title">Third Person</div>
                <div class="sc-sub">ပြင်ပဇာတ်ကြောင်းပြောသူအနေနဲ့ ဖြစ်စဉ်ကို ပြောမယ်</div>
            </div>
            <div class="select-card" onclick="selectNarration('first', this)">
                <div class="sc-title">First Person</div>
                <div class="sc-sub">အဓိကဇာတ်ကောင် ကိုယ်တိုင်ပြောသလို ပြောမယ်</div>
            </div>

            <button class="btn-primary" id="genScriptBtn" onclick="generateScriptFromLocalVideo()" style="margin-top:8px;">
                🪄 Script ပြန်ထုတ်မယ်
            </button>
            <div class="status-banner" id="scriptStatus"></div>

            <div style="display:flex;justify-content:space-between;align-items:center;margin-top:12px;margin-bottom:6px;">
                <span style="font-size:0.8rem;font-weight:700;color:var(--text-muted);" id="segCountLabel">စာကြောင်း: 2 | ပြင်ချင်တာ ပြင်နိုင်ပါတယ်</span>
                <button class="btn-secondary" style="width:auto;padding:4px 9px;margin:0;font-size:0.78rem;color:var(--accent-orange);" onclick="addBlankSegment()">＋ စာကြောင်းထည့်</button>
            </div>

            <div id="segmentsContainer"></div>
        </div>

        <!-- STEP 2: VOICEOVER အသံရွေးပါ -->
        <div class="card">
            <div class="step-head">
                <div class="step-num">2</div>
                <div class="step-title">Voiceover အသံရွေးပါ</div>
            </div>

            <div id="voiceListContainer">
                <div class="voice-row" onclick="selectVoice(0, this)">
                    <span style="font-weight:700;font-size:0.88rem;">မိန်းကလေး ၁ - တည်ငြိမ်</span>
                    <button class="v-sample-btn" onclick="event.stopPropagation();previewVoice(0)">▶</button>
                </div>
                <div class="voice-row" onclick="selectVoice(1, this)">
                    <span style="font-weight:700;font-size:0.88rem;">မိန်းကလေး ၂ - ပေါ့ပါး</span>
                    <button class="v-sample-btn" onclick="event.stopPropagation();previewVoice(1)">▶</button>
                </div>
                <div class="voice-row" onclick="selectVoice(2, this)">
                    <span style="font-weight:700;font-size:0.88rem;">မိန်းကလေး ၃ - နုပျို</span>
                    <button class="v-sample-btn" onclick="event.stopPropagation();previewVoice(2)">▶</button>
                </div>
                <div class="voice-row" onclick="selectVoice(3, this)">
                    <span style="font-weight:700;font-size:0.88rem;">ယောက်ျား ၁ - တက်ကြွ</span>
                    <button class="v-sample-btn" onclick="event.stopPropagation();previewVoice(3)">▶</button>
                </div>
                <div class="voice-row active" onclick="selectVoice(4, this)">
                    <span style="font-weight:700;font-size:0.88rem;">ယောက်ျား ၂ - လေးနက်</span>
                    <button class="v-sample-btn" onclick="event.stopPropagation();previewVoice(4)">▶</button>
                </div>
                <div class="voice-row" onclick="selectVoice(5, this)">
                    <span style="font-weight:700;font-size:0.88rem;">ယောက်ျား ၃ - စိတ်လှုပ်ရှား</span>
                    <button class="v-sample-btn" onclick="event.stopPropagation();previewVoice(5)">▶</button>
                </div>
            </div>

            <button class="btn-primary" id="genVoBtn" onclick="generateVoiceoverAudio()" style="margin-top:6px;">
                🎙️ Voiceover ပြန်ဖန်တီးမယ်
            </button>
            <div class="status-banner" id="voStatus"></div>

            <div class="slider-group" style="margin-top:10px;">
                <div class="slider-head">
                    <span>အသံ အစော / အနောက် ချိန်</span>
                    <span id="offsetVal">0.0s</span>
                </div>
                <input type="range" class="full-slider" id="audioOffsetSlider" min="-2.0" max="2.0" step="0.1" value="0.0" oninput="document.getElementById('offsetVal').innerText=this.value+'s'">
            </div>
        </div>

        <!-- STEP 3: VIDEO ချိန်ညှိမှု -->
        <div class="card">
            <div class="step-head">
                <div class="step-num">3</div>
                <div class="step-title">Video ချိန်ညှိမှု</div>
            </div>

            <div class="blur-item">
                <span style="font-weight:700;font-size:0.88rem;">ဘယ်ညာ ပြောင်းပြန်လှည့် (Mirror)</span>
                <label class="switch">
                    <input type="checkbox" id="mirrorChk">
                    <span class="slider-pill orange"></span>
                </label>
            </div>

            <div class="blur-item">
                <span style="font-weight:700;font-size:0.88rem;">မြန်မာစာတန်း video ထဲ ထည့်မယ်</span>
                <label class="switch">
                    <input type="checkbox" id="showSubChk" checked>
                    <span class="slider-pill orange"></span>
                </label>
            </div>

            <div class="font-grid">
                <div class="font-card active" onclick="selectFont('Noto Sans Myanmar', this)">
                    <div style="font-size:0.95rem;font-weight:700;">မင်္ဂလာပါ</div>
                    <div style="font-size:0.7rem;color:var(--text-muted);">Noto Sans</div>
                </div>
                <div class="font-card" onclick="selectFont('Noto Serif Myanmar', this)">
                    <div style="font-size:0.95rem;font-family:'Noto Serif Myanmar';font-weight:700;">မင်္ဂလာပါ</div>
                    <div style="font-size:0.7rem;color:var(--text-muted);">Noto Serif</div>
                </div>
                <div class="font-card" onclick="selectFont('Padauk', this)">
                    <div style="font-size:0.95rem;font-family:'Padauk';font-weight:700;">မင်္ဂလာပါ</div>
                    <div style="font-size:0.7rem;color:var(--text-muted);">Padauk</div>
                </div>
                <div class="font-card" onclick="document.getElementById('customFontInput').click()">
                    <div style="font-size:0.9rem;font-weight:700;color:var(--accent-orange);">＋ Custom Font</div>
                    <div style="font-size:0.7rem;color:var(--text-muted);" id="customFontName">AJ 02 (.ttf) တင်ရန်</div>
                    <input type="file" id="customFontInput" accept=".ttf,.otf" style="display:none">
                </div>
            </div>

            <div style="font-size:0.82rem;font-weight:700;margin-top:8px;">စာလုံးအရောင်</div>
            <div class="color-row">
                <div class="c-swatch" style="background:#FFFFFF;color:#000;" onclick="pickSubColor('#FFFFFF', this)"></div>
                <div class="c-swatch" style="background:#FFE600;color:#000;" onclick="pickSubColor('#FFE600', this)"></div>
                <div class="c-swatch active" style="background:#38BDF8;color:#000;" onclick="pickSubColor('#38BDF8', this)">✓</div>
                <div class="c-swatch" style="background:#F472B6;color:#000;" onclick="pickSubColor('#F472B6', this)"></div>
            </div>

            <div class="slider-group">
                <div class="slider-head"><span>စာလုံးအရွယ်</span><span id="subScaleTxt">90%</span></div>
                <input type="range" class="full-slider" id="subScaleSlider" min="60" max="140" value="90" oninput="document.getElementById('subScaleTxt').innerText=this.value+'%'">
            </div>

            <button class="btn-secondary" onclick="resetSubPos()">စာတန်းနေရာ မူလအတိုင်း ပြန်ထားမယ်</button>

            <hr style="border:none;border-top:1px solid #E2E8F0;margin:10px 0;">

            <!-- CHANNEL WATERMARK -->
            <div class="blur-item">
                <span style="font-weight:700;font-size:0.88rem;">Channel Watermark ထည့်မယ်</span>
                <label class="switch">
                    <input type="checkbox" id="wmChk" checked>
                    <span class="slider-pill orange"></span>
                </label>
            </div>
            <input type="text" id="wmTextInput" value="MY RECAP" placeholder="Channel အမည်" style="width:100%;padding:8px 10px;border-radius:10px;border:1px solid #CBD5E1;font-weight:700;margin-bottom:8px;">

            <div class="slider-group">
                <div class="slider-head"><span>Opacity</span><span id="wmOpTxt">50%</span></div>
                <input type="range" class="full-slider" id="wmOpSlider" min="10" max="100" value="50" oninput="document.getElementById('wmOpTxt').innerText=this.value+'%'">
            </div>
            <div class="slider-group">
                <div class="slider-head"><span>စာလုံးအရွယ်</span><span id="wmSzTxt">95%</span></div>
                <input type="range" class="full-slider" id="wmSzSlider" min="50" max="150" value="95" oninput="document.getElementById('wmSzTxt').innerText=this.value+'%'">
            </div>

            <hr style="border:none;border-top:1px solid #E2E8F0;margin:10px 0;">

            <!-- COPYRIGHT FILTERS -->
            <div class="slider-group">
                <div class="slider-head"><span>Zoom</span><span id="zoomTxt">100%</span></div>
                <input type="range" class="full-slider" id="zoomSlider" min="80" max="135" value="100" oninput="document.getElementById('zoomTxt').innerText=this.value+'%'">
            </div>
            <div class="slider-group">
                <div class="slider-head"><span>အလင်း (Brightness)</span><span id="brightTxt">1.00</span></div>
                <input type="range" class="full-slider" id="brightSlider" min="0.6" max="1.4" step="0.05" value="1.0" oninput="document.getElementById('brightTxt').innerText=parseFloat(this.value).toFixed(2)">
            </div>
            <div class="slider-group">
                <div class="slider-head"><span>Contrast</span><span id="contTxt">1.00</span></div>
                <input type="range" class="full-slider" id="contSlider" min="0.7" max="1.4" step="0.05" value="1.0" oninput="document.getElementById('contTxt').innerText=parseFloat(this.value).toFixed(2)">
            </div>
            <div class="slider-group">
                <div class="slider-head"><span>အရောင် (Saturation)</span><span id="satTxt">1.00</span></div>
                <input type="range" class="full-slider" id="satSlider" min="0.5" max="1.6" step="0.05" value="1.0" oninput="document.getElementById('satTxt').innerText=parseFloat(this.value).toFixed(2)">
            </div>
            <div class="slider-group">
                <div class="slider-head"><span>မူရင်းအသံ</span><span id="origVolTxt">0%</span></div>
                <input type="range" class="full-slider" id="origVolSlider" min="0" max="100" value="0" oninput="document.getElementById('origVolTxt').innerText=this.value+'%'">
            </div>
            <div class="slider-group">
                <div class="slider-head"><span>Voiceover အသံ</span><span id="voVolTxt">100%</span></div>
                <input type="range" class="full-slider" id="voVolSlider" min="20" max="100" value="100" oninput="document.getElementById('voVolTxt').innerText=this.value+'%'">
            </div>
            <button class="btn-secondary" onclick="resetVisualFilters()">Reset</button>
        </div>

        <!-- STEP 4: ထုတ်ယူမယ် -->
        <div class="card">
            <div class="step-head">
                <div class="step-num">4</div>
                <div class="step-title">ထုတ်ယူမယ်</div>
            </div>

            <button class="btn-secondary" onclick="downloadSRTFile()">📄 မြန်မာ SRT Download</button>
            <button class="btn-primary" id="renderFinalBtn" onclick="startSmoothLocalRender()">📥 Recap Video ထုတ်မယ်</button>
            <div class="status-banner" id="renderStatusBanner"></div>

            <div id="outputVideoWrap" style="display:none;margin-top:12px;">
                <video id="finalOutputPreview" controls playsinline style="width:100%;border-radius:12px;background:#000;"></video>
                <a id="finalDownloadAnchor" class="btn-primary" style="margin-top:8px;text-decoration:none;display:flex;">📥 MP4 Download</a>
            </div>
        </div>

    </div><!-- END SCROLLABLE TOOLS PANE -->

</div><!-- END SPLIT LAYOUT -->

<script>
const canvas = document.getElementById('mainCanvas');
const ctx = canvas.getContext('2d');
const playBtn = document.getElementById('playBtn');
const seekBar = document.getElementById('seekBar');
const timeLabel = document.getElementById('timeLabel');

const video = document.createElement('video');
video.playsInline = true;
video.crossOrigin = 'anonymous';

let currentVideoFile = null;
let bgImage = null;
let narrationStyle = 'direct';
let selectedVoiceIdx = 4;
let selectedFontFamily = 'Noto Sans Myanmar';
let selectedSubColor = '#38BDF8';
let isRecording = false;
let showHandles = true;
let handlesTimer = null;

let segments = [
    {{ start: 0.0, end: 3.5, text: "ပြန်စရာအိမ်မရှိတော့တဲ့" }},
    {{ start: 3.5, end: 7.5, text: "ဇနီးမောင်နှံနှစ်ယောက်က မြို့ပေါ်က သားငယ်ဆီမှာ" }}
];

let synthesizedAudioMap = {{}};
let activeSpeechAudio = new Audio();

// Video သည် အလယ်တွင် ပုံသေ (Fixed) ဖြစ်ပြီး Blur 1, Blur 2, Subtitle, Watermark သာ ရွှေ့နိုင်မည်
let boxes = {{
    blur1: {{ x: 0.06, y: 0.72, w: 0.88, h: 0.11, color: '#00E5FF' }},
    blur2: {{ x: 0.06, y: 0.06, w: 0.38, h: 0.08, color: '#D946EF' }},
    sub:   {{ x: 0.50, y: 0.775 }},
    wm:    {{ x: 0.80, y: 0.06 }}
}};

window.addEventListener('DOMContentLoaded', () => {{
    const savedGroq = localStorage.getItem('s99_groq_key');
    const savedGemini = localStorage.getItem('s99_gemini_key');
    if (savedGroq && !document.getElementById('groqKeyInput').value) document.getElementById('groqKeyInput').value = savedGroq;
    if (savedGemini && !document.getElementById('geminiKeyInput').value) document.getElementById('geminiKeyInput').value = savedGemini;
    renderSegmentsUI();
}});

function toggleApiModal() {{
    const el = document.getElementById('apiModal');
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
}}

function saveKeysToLocal() {{
    localStorage.setItem('s99_groq_key', document.getElementById('groqKeyInput').value.trim());
    localStorage.setItem('s99_gemini_key', document.getElementById('geminiKeyInput').value.trim());
    document.getElementById('apiModal').style.display = 'none';
}}

function wakeHandles() {{
    showHandles = true;
    if (handlesTimer) clearTimeout(handlesTimer);
    handlesTimer = setTimeout(() => {{ if (!activeDrag) showHandles = false; }}, 3000);
}}

// ==================== GALLERY VIDEO & CUSTOM FONT LOAD ====================
document.getElementById('galleryVideoInput').addEventListener('change', function(e) {{
    const file = e.target.files[0];
    if (!file) return;
    currentVideoFile = file;
    video.src = URL.createObjectURL(file);
    video.load();
    video.onloadedmetadata = () => {{
        seekBar.max = video.duration || 100;
        video.currentTime = Math.min(0.5, (video.duration || 1) * 0.05);
        wakeHandles();
    }};
}});

document.getElementById('bgFileInput').addEventListener('change', function(e) {{
    const file = e.target.files[0];
    if (!file) return;
    const img = new Image();
    img.onload = () => {{ bgImage = img; }};
    img.src = URL.createObjectURL(file);
}});

document.getElementById('customFontInput').addEventListener('change', async function(e) {{
    const file = e.target.files[0];
    if (!file) return;
    const buf = await file.arrayBuffer();
    const fontFace = new FontFace('UserCustomFont', buf);
    await fontFace.load();
    document.fonts.add(fontFace);
    selectedFontFamily = 'UserCustomFont';
    document.getElementById('customFontName').innerText = file.name;
    document.querySelectorAll('.font-card').forEach(c => c.classList.remove('active'));
    e.target.parentElement.classList.add('active');
}});

// ==================== PLAYER CONTROLS ====================
playBtn.addEventListener('click', () => {{
    if (!video.src) {{
        document.getElementById('galleryVideoInput').click();
        return;
    }}
    if (video.paused) {{
        video.play();
        playBtn.innerText = '⏸';
    }} else {{
        video.pause();
        activeSpeechAudio.pause();
        playBtn.innerText = '▶';
    }}
}});

seekBar.addEventListener('input', () => {{
    video.currentTime = parseFloat(seekBar.value);
}});

video.addEventListener('timeupdate', () => {{
    if (!seekBar.matches(':active')) seekBar.value = video.currentTime;
    timeLabel.innerText = `${{fmtTime(video.currentTime)}} / ${{fmtTime(video.duration || 0)}}`;
    syncVoiceoverPlayback(video.currentTime);
}});

function fmtTime(s) {{
    s = Math.max(0, s || 0);
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${{m}}:${{sec < 10 ? '0' : ''}}${{sec}}`;
}}

// ==================== TOUCH DRAG (BLUR, SUBTITLE, WATERMARK ONLY — VIDEO LOCKED) ====================
let activeDrag = null;
let dragMode = null;
let startPt = {{ x: 0, y: 0 }};
let origBox = null;

function getNormPt(e) {{
    const r = canvas.getBoundingClientRect();
    const cx = e.touches ? e.touches[0].clientX : e.clientX;
    const cy = e.touches ? e.touches[0].clientY : e.clientY;
    return {{ x: (cx - r.left) / r.width, y: (cy - r.top) / r.height }};
}}

function hitTestCanvas(pt) {{
    if (document.getElementById('showSubChk').checked) {{
        if (Math.abs(pt.x - boxes.sub.x) < 0.36 && Math.abs(pt.y - boxes.sub.y) < 0.055) return {{ key: 'sub', mode: 'move' }};
    }}
    if (document.getElementById('wmChk').checked) {{
        if (Math.abs(pt.x - boxes.wm.x) < 0.18 && Math.abs(pt.y - boxes.wm.y) < 0.05) return {{ key: 'wm', mode: 'move' }};
    }}
    const checkRect = (b) => {{
        const rx = b.x + b.w, ry = b.y + b.h;
        if (Math.abs(pt.x - rx) < 0.075 && Math.abs(pt.y - ry) < 0.065) return 'resize';
        if (pt.x >= b.x && pt.x <= rx && pt.y >= b.y && pt.y <= ry) return 'move';
        return null;
    }};
    if (document.getElementById('blur2Chk').checked) {{
        const m2 = checkRect(boxes.blur2);
        if (m2) return {{ key: 'blur2', mode: m2 }};
    }}
    if (document.getElementById('blur1Chk').checked) {{
        const m1 = checkRect(boxes.blur1);
        if (m1) return {{ key: 'blur1', mode: m1 }};
    }}
    // Video ကို ရွှေ့လို့မရအောင် null ပြန်ပေးထားသည်
    return null;
}}

function handleDown(e) {{
    wakeHandles();
    const pt = getNormPt(e);
    const hit = hitTestCanvas(pt);
    if (hit) {{
        e.preventDefault();
        activeDrag = hit.key;
        dragMode = hit.mode;
        startPt = pt;
        origBox = {{ ...boxes[activeDrag] }};
    }}
}}

function handleMove(e) {{
    if (!activeDrag) return;
    e.preventDefault();
    wakeHandles();
    const pt = getNormPt(e);
    const dx = pt.x - startPt.x;
    const dy = pt.y - startPt.y;

    if (activeDrag === 'sub' || activeDrag === 'wm') {{
        boxes[activeDrag].x = Math.min(0.92, Math.max(0.08, origBox.x + dx));
        boxes[activeDrag].y = Math.min(0.95, Math.max(0.04, origBox.y + dy));
    }} else {{
        if (dragMode === 'move') {{
            boxes[activeDrag].x = Math.min(1.0 - origBox.w, Math.max(0.0, origBox.x + dx));
            boxes[activeDrag].y = Math.min(1.0 - origBox.h, Math.max(0.0, origBox.y + dy));
        }} else {{
            boxes[activeDrag].w = Math.min(1.0 - origBox.x, Math.max(0.12, origBox.w + dx));
            boxes[activeDrag].h = Math.min(1.0 - origBox.y, Math.max(0.04, origBox.h + dy));
        }}
    }}
}}

function handleUp() {{ activeDrag = null; dragMode = null; }}

canvas.addEventListener('mousedown', handleDown);
window.addEventListener('mousemove', handleMove);
window.addEventListener('mouseup', handleUp);
canvas.addEventListener('touchstart', handleDown, {{ passive: false }});
window.addEventListener('touchmove', handleMove, {{ passive: false }});
window.addEventListener('touchend', handleUp);

// ==================== 60FPS SMOOTH CANVAS RENDER LOOP ====================
function cleanMyanmarText(txt) {{
    if (!txt) return "";
    return txt.replace(/[\u200b\u200c\u200d\ufeff]/g, "").trim();
}}

function drawFrame() {{
    const cw = canvas.width, ch = canvas.height;
    ctx.clearRect(0, 0, cw, ch);

    if (bgImage) {{
        ctx.drawImage(bgImage, 0, 0, cw, ch);
    }} else {{
        ctx.fillStyle = '#090D16';
        ctx.fillRect(0, 0, cw, ch);
    }}

    const bright = parseFloat(document.getElementById('brightSlider').value);
    const cont = parseFloat(document.getElementById('contSlider').value);
    const sat = parseFloat(document.getElementById('satSlider').value);

    // Video ကို အလယ်တည့်တည့်တွင် ပုံသေ (Fixed Center) ဆွဲပေးခြင်း
    if (video.readyState >= 2) {{
        const vw = video.videoWidth || 720, vh = video.videoHeight || 1280;
        const zm = parseFloat(document.getElementById('zoomSlider').value) / 100.0;
        const sc = Math.min(cw / vw, ch / vh) * zm;
        const dw = vw * sc, dh = vh * sc;
        const dx = (cw - dw) / 2;
        const dy = (ch - dh) / 2;

        ctx.save();
        ctx.filter = `brightness(${{bright}}) contrast(${{cont}}) saturate(${{sat}})`;
        if (document.getElementById('mirrorChk').checked) {{
            ctx.translate(cw, 0);
            ctx.scale(-1, 1);
            ctx.drawImage(video, cw - dx - dw, dy, dw, dh);
        }} else {{
            ctx.drawImage(video, dx, dy, dw, dh);
        }}
        ctx.restore();
    }} else {{
        ctx.fillStyle = '#94A3B8';
        ctx.font = '700 22px "Noto Sans Myanmar", sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('▶ Gallery မှ ဗီဒီယိုရွေးပါ', cw / 2, ch / 2);
    }}

    // BLUR MASKS
    const blurOp = parseInt(document.getElementById('blurOpacity').value) / 100.0;
    const renderBlurBox = (b, enabled) => {{
        if (!enabled || blurOp <= 0) return;
        const bx = b.x * cw, by = b.y * ch, bw = b.w * cw, bh = b.h * ch;
        ctx.save();
        ctx.beginPath();
        ctx.roundRect(bx, by, bw, bh, 12);
        ctx.clip();
        ctx.filter = `blur(${{Math.max(4, Math.round(20 * blurOp))}}px)`;
        ctx.drawImage(canvas, 0, 0);
        ctx.filter = 'none';
        ctx.fillStyle = `rgba(20, 20, 20, ${{0.42 * blurOp}})`;
        ctx.fillRect(bx, by, bw, bh);
        ctx.restore();

        if (showHandles && !isRecording) {{
            ctx.save();
            ctx.strokeStyle = b.color;
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.roundRect(bx, by, bw, bh, 12);
            ctx.stroke();
            ctx.fillStyle = b.color;
            ctx.beginPath();
            ctx.arc(bx + bw, by + bh, 10, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        }}
    }};
    renderBlurBox(boxes.blur1, document.getElementById('blur1Chk').checked);
    renderBlurBox(boxes.blur2, document.getElementById('blur2Chk').checked);

    // WATERMARK
    if (document.getElementById('wmChk').checked) {{
        const wmTxt = document.getElementById('wmTextInput').value.trim();
        const wmOp = parseInt(document.getElementById('wmOpSlider').value) / 100.0;
        const wmSz = Math.round(22 * (parseInt(document.getElementById('wmSzSlider').value) / 100.0) * (cw / 540.0));
        if (wmTxt) {{
            ctx.save();
            ctx.font = `700 ${{wmSz}}px "${{selectedFontFamily}}", sans-serif`;
            ctx.fillStyle = `rgba(255, 255, 255, ${{wmOp}})`;
            ctx.textAlign = 'center';
            ctx.fillText(wmTxt, boxes.wm.x * cw, boxes.wm.y * ch);
            ctx.restore();
        }}
    }}

    // SUBTITLES
    if (document.getElementById('showSubChk').checked) {{
        const offset = parseFloat(document.getElementById('audioOffsetSlider').value) || 0;
        const t = (video.currentTime || 0) - offset;
        let subLine = "";
        for (let i = 0; i < segments.length; i++) {{
            if (t >= segments[i].start && t <= segments[i].end) {{
                subLine = cleanMyanmarText(segments[i].text);
                break;
            }}
        }}
        if (!subLine && video.paused && segments.length > 0) subLine = cleanMyanmarText(segments[0].text);

        if (subLine) {{
            const scalePct = parseInt(document.getElementById('subScaleSlider').value) / 100.0;
            const fontPx = Math.round(25 * scalePct * (cw / 540.0));
            ctx.save();
            ctx.font = `700 ${{fontPx}}px "${{selectedFontFamily}}", "Noto Sans Myanmar", sans-serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';

            const sx = boxes.sub.x * cw, sy = boxes.sub.y * ch;
            const tw = Math.min(cw * 0.9, ctx.measureText(subLine).width);
            const th = fontPx * 1.45;

            ctx.fillStyle = 'rgba(18, 18, 18, 0.72)';
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.roundRect(sx - tw / 2 - 18, sy - th / 2 - 4, tw + 36, th + 8, 12);
            ctx.fill();
            ctx.stroke();

            ctx.lineWidth = Math.max(3.5, fontPx * 0.16);
            ctx.strokeStyle = '#000000';
            ctx.strokeText(subLine, sx, sy);
            ctx.fillStyle = selectedSubColor;
            ctx.fillText(subLine, sx, sy);
            ctx.restore();
        }}
    }}

    requestAnimationFrame(drawFrame);
}}
requestAnimationFrame(drawFrame);

// ==================== UI HELPERS ====================
function changeRatio(r, el) {{
    document.querySelectorAll('.r-btn').forEach(b => b.classList.remove('active'));
    el.classList.add('active');
    if (r === '9:16') {{ canvas.width = 540; canvas.height = 960; }}
    else if (r === '16:9') {{ canvas.width = 854; canvas.height = 480; }}
    else if (r === '1:1') {{ canvas.width = 640; canvas.height = 640; }}
    else if (r === '4:3') {{ canvas.width = 640; canvas.height = 480; }}
    wakeHandles();
}}

function resetBlur1() {{ boxes.blur1 = {{ x: 0.06, y: 0.72, w: 0.88, h: 0.11, color: '#00E5FF' }}; wakeHandles(); }}
function clearAllBlurs() {{ document.getElementById('blur1Chk').checked = false; document.getElementById('blur2Chk').checked = false; }}
function resetSubPos() {{ boxes.sub = {{ x: 0.50, y: 0.775 }}; wakeHandles(); }}
function resetVisualFilters() {{
    document.getElementById('zoomSlider').value = 100; document.getElementById('zoomTxt').innerText = '100%';
    document.getElementById('brightSlider').value = 1.0; document.getElementById('brightTxt').innerText = '1.00';
    document.getElementById('contSlider').value = 1.0; document.getElementById('contTxt').innerText = '1.00';
    document.getElementById('satSlider').value = 1.0; document.getElementById('satTxt').innerText = '1.00';
}}

function selectNarration(mode, el) {{
    narrationStyle = mode;
    document.querySelectorAll('.select-card').forEach(c => c.classList.remove('active'));
    el.classList.add('active');
}}

function selectVoice(idx, el) {{
    selectedVoiceIdx = idx;
    document.querySelectorAll('.voice-row').forEach(r => r.classList.remove('active'));
    el.classList.add('active');
}}

function selectFont(fam, el) {{
    selectedFontFamily = fam;
    document.querySelectorAll('.font-card').forEach(c => c.classList.remove('active'));
    el.classList.add('active');
}}

function pickSubColor(clr, el) {{
    selectedSubColor = clr;
    document.querySelectorAll('.c-swatch').forEach(s => {{ s.classList.remove('active'); s.innerText = ''; }});
    el.classList.add('active');
    el.innerText = '✓';
}}

function renderSegmentsUI() {{
    const wrap = document.getElementById('segmentsContainer');
    document.getElementById('segCountLabel').innerText = `စာကြောင်း: ${{segments.length}} | ပြင်ချင်တာ ပြင်နိုင်ပါတယ်`;
    wrap.innerHTML = '';
    segments.forEach((seg, idx) => {{
        const div = document.createElement('div');
        div.className = 'seg-box';
        div.innerHTML = `
            <div class="seg-top">
                <span class="seg-time">${{fmtTime(seg.start)}} - ${{fmtTime(seg.end)}}</span>
                <button class="seg-del" onclick="deleteSeg(${{idx}})">🗑️</button>
            </div>
            <textarea class="seg-input" rows="2" oninput="segments[${{idx}}].text=this.value">${{seg.text}}</textarea>
        `;
        wrap.appendChild(div);
    }});
}}

function deleteSeg(idx) {{ segments.splice(idx, 1); renderSegmentsUI(); }}
function addBlankSegment() {{
    const lastEnd = segments.length > 0 ? segments[segments.length - 1].end : 0;
    segments.push({{ start: lastEnd, end: lastEnd + 3.0, text: "စာကြောင်းအသစ်" }});
    renderSegmentsUI();
}}

// ==================== CLIENT-SIDE AUDIO EXTRACTOR & AI TRANSLATION ====================
async function extractWavBlobFromVideoFile(file) {{
    const arrayBuf = await file.arrayBuffer();
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const decoded = await audioCtx.decodeAudioData(arrayBuf);
    const offlineCtx = new OfflineAudioContext(1, Math.floor(decoded.duration * 16000), 16000);
    const source = offlineCtx.createBufferSource();
    source.buffer = decoded;
    source.connect(offlineCtx.destination);
    source.start(0);
    const rendered = await offlineCtx.startRendering();
    const pcm = rendered.getChannelData(0);

    const wavBuf = new ArrayBuffer(44 + pcm.length * 2);
    const view = new DataView(wavBuf);
    const writeStr = (off, s) => {{ for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i)); }};
    writeStr(0, 'RIFF'); view.setUint32(4, 36 + pcm.length * 2, true); writeStr(8, 'WAVE');
    writeStr(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
    view.setUint16(22, 1, true); view.setUint32(24, 16000, true); view.setUint32(28, 32000, true);
    view.setUint16(32, 2, true); view.setUint16(34, 16, true); writeStr(36, 'data');
    view.setUint32(40, pcm.length * 2, true);
    let offset = 44;
    for (let i = 0; i < pcm.length; i++, offset += 2) {{
        let s = Math.max(-1, Math.min(1, pcm[i]));
        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }}
    return new Blob([wavBuf], {{ type: 'audio/wav' }});
}}

async function generateScriptFromLocalVideo() {{
    const groqKey = document.getElementById('groqKeyInput').value.trim();
    const geminiKey = document.getElementById('geminiKeyInput').value.trim();
    const statusEl = document.getElementById('scriptStatus');

    if (!currentVideoFile) {{ alert("ကျေးဇူးပြု၍ အပေါ်ဆုံးမှ Gallery ဗီဒီယို အရင်ရွေးပေးပါ။"); return; }}
    if (!groqKey || !geminiKey) {{ toggleApiModal(); alert("Groq နှင့် Gemini API Key ထည့်သွင်းပေးပါ။"); return; }}

    statusEl.style.display = 'block';
    statusEl.innerText = "⏳ ၁/၂ - ဗီဒီယိုထဲမှ အသံကို ဆွဲထုတ်ပြီး Groq Whisper ဖြင့် နားထောင်နေပါသည်...";

    try {{
        const wavBlob = await extractWavBlobFromVideoFile(currentVideoFile);
        const formData = new FormData();
        formData.append('file', wavBlob, 'audio.wav');
        formData.append('model', 'whisper-large-v3-turbo');
        formData.append('response_format', 'verbose_json');

        const wResp = await fetch('https://api.groq.com/openai/v1/audio/transcriptions', {{
            method: 'POST',
            headers: {{ 'Authorization': 'Bearer ' + groqKey }},
            body: formData
        }});
        const wData = await wResp.json();
        if (!wData.segments || wData.segments.length === 0) throw new Error("စကားပြောသံ မတွေ့ရှိပါ။");

        statusEl.innerText = `⏳ ၂/၂ - စာကြောင်း (${{wData.segments.length}}) ကြောင်းကို Gemini 3.5 ဖြင့် မြန်မာဘာသာပြန်နေပါသည်...`;

        let stylePrompt = "Translate directly and naturally into spoken Burmese (Myanmar) keeping original POV.";
        if (narrationStyle === 'third') stylePrompt = "Rewrite and translate into natural Burmese (Myanmar) as a Third-Person movie recap narrator.";
        if (narrationStyle === 'first') stylePrompt = "Rewrite and translate into natural Burmese (Myanmar) from a First-Person main character perspective.";

        const payload = wData.segments.map((s, idx) => ({{ id: idx, text: s.text }}));
        const gUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${{geminiKey}}`;
        const gResp = await fetch(gUrl, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{
                contents: [{{ parts: [{{ text: `${{stylePrompt}}\nReturn ONLY a valid JSON array of objects with 'id' and 'translation':\n${{JSON.stringify(payload)}}` }}] }}],
                generationConfig: {{ responseMimeType: "application/json" }}
            }})
        }});

        let transMap = {{}};
        if (gResp.ok) {{
            const gJson = await gResp.json();
            const parsed = JSON.parse(gJson.candidates[0].content.parts[0].text);
            parsed.forEach(item => {{ transMap[item.id] = item.translation; }});
        }} else {{
            const bResp = await fetch('https://api.groq.com/openai/v1/chat/completions', {{
                method: 'POST',
                headers: {{ 'Authorization': 'Bearer ' + groqKey, 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    model: 'llama-3.3-70b-versatile',
                    messages: [{{ role: 'user', content: `${{stylePrompt}}\nReturn JSON object with key 'items' containing array of 'id' and 'translation':\n${{JSON.stringify(payload)}}` }}],
                    response_format: {{ type: 'json_object' }}
                }})
            }});
            const bJson = await bResp.json();
            const parsed = JSON.parse(bJson.choices[0].message.content).items || [];
            parsed.forEach(item => {{ transMap[item.id] = item.translation; }});
        }}

        segments = wData.segments.map((s, idx) => ({{
            start: parseFloat(s.start.toFixed(2)),
            end: parseFloat(s.end.toFixed(2)),
            text: cleanMyanmarText(transMap[idx] || s.text)
        }}));

        renderSegmentsUI();
        statusEl.innerText = "✅ မြန်မာဘာသာပြန် Script အောင်မြင်စွာ ထုတ်ပြီးပါပြီ!";
    }} catch (err) {{
        statusEl.innerText = "❌ Error: " + err.message;
    }}
}}

// ==================== VOICEOVER TTS ENGINE ====================
const voiceConfigs = [
    {{ pitch: 1.0, rate: 0.95 }},
    {{ pitch: 1.15, rate: 1.05 }},
    {{ pitch: 1.25, rate: 1.02 }},
    {{ pitch: 0.92, rate: 1.08 }},
    {{ pitch: 0.82, rate: 0.96 }},
    {{ pitch: 0.98, rate: 1.14 }}
];

function previewVoice(idx) {{
    const sampleUrl = `https://translate.google.com/translate_tts?ie=UTF-8&q=${{encodeURIComponent("မင်္ဂလာပါရှင်၊ အသံနမူနာဖြစ်ပါတယ်")}}&tl=my&client=tw-ob`;
    const aud = new Audio(sampleUrl);
    aud.playbackRate = voiceConfigs[idx].rate;
    aud.play().catch(() => {{}});
}}

async function generateVoiceoverAudio() {{
    const voStatus = document.getElementById('voStatus');
    voStatus.style.display = 'block';
    voStatus.innerText = "⏳ Voiceover အသံများ ဖန်တီးနေပါသည်...";
    synthesizedAudioMap = {{}};

    for (let i = 0; i < segments.length; i++) {{
        const txt = segments[i].text.trim();
        if (!txt) continue;
        const url = `https://translate.google.com/translate_tts?ie=UTF-8&q=${{encodeURIComponent(txt.slice(0, 180))}}&tl=my&client=tw-ob`;
        synthesizedAudioMap[i] = url;
    }}
    voStatus.innerText = "✓ Voiceover ရပါပြီ — အပေါ်က Video ကို Play နှိပ်ပြီး နားထောင်ကြည့်ပါ။";
}}

let lastPlayedSegIdx = -1;
function syncVoiceoverPlayback(curTime) {{
    if (video.paused) return;
    video.volume = parseInt(document.getElementById('origVolSlider').value) / 100.0;
    const offset = parseFloat(document.getElementById('audioOffsetSlider').value) || 0;
    const adjTime = curTime - offset;

    let foundIdx = -1;
    for (let i = 0; i < segments.length; i++) {{
        if (adjTime >= segments[i].start && adjTime <= segments[i].end) {{
            foundIdx = i;
            break;
        }}
    }}
    if (foundIdx !== -1 && foundIdx !== lastPlayedSegIdx && synthesizedAudioMap[foundIdx]) {{
        lastPlayedSegIdx = foundIdx;
        activeSpeechAudio.src = synthesizedAudioMap[foundIdx];
        activeSpeechAudio.volume = parseInt(document.getElementById('voVolSlider').value) / 100.0;
        activeSpeechAudio.playbackRate = voiceConfigs[selectedVoiceIdx].rate;
        activeSpeechAudio.play().catch(() => {{}});
    }} else if (foundIdx === -1) {{
        lastPlayedSegIdx = -1;
    }}
}}

// ==================== SRT DOWNLOAD & SMOOTH LOCAL RENDER ====================
function downloadSRTFile() {{
    const fmtSrt = (s) => {{
        const hrs = Math.floor(s / 3600);
        const mins = Math.floor((s % 3600) / 60);
        const secs = Math.floor(s % 60);
        const ms = Math.round((s - Math.floor(s)) * 1000);
        return `${{String(hrs).padStart(2,'0')}}:${{String(mins).padStart(2,'0')}}:${{String(secs).padStart(2,'0')}},${{String(ms).padStart(3,'0')}}`;
    }};
    let srt = "";
    segments.forEach((seg, i) => {{
        srt += `${{i + 1}}\n${{fmtSrt(seg.start)}} --> ${{fmtSrt(seg.end)}}\n${{seg.text}}\n\n`;
    }});
    const blob = new Blob([srt], {{ type: 'text/plain;charset=utf-8' }});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = "RecapMM_Subtitle.srt";
    a.click();
}}

function startSmoothLocalRender() {{
    if (!video.src) {{ alert("ကျေးဇူးပြု၍ Gallery မှ ဗီဒီယို အရင်ရွေးပေးပါ။"); return; }}
    const banner = document.getElementById('renderStatusBanner');
    const outWrap = document.getElementById('outputVideoWrap');
    const outVid = document.getElementById('finalOutputPreview');
    const dlAnchor = document.getElementById('finalDownloadAnchor');

    banner.style.display = 'block';
    outWrap.style.display = 'none';
    banner.innerText = "⏳ Local Video Render ဖမ်းယူနေပါသည် (Video ပြီးဆုံးသည်အထိ ခဏစောင့်ပေးပါ)...";

    isRecording = true;
    showHandles = false;
    const chunks = [];
    const stream = canvas.captureStream(30);

    const mime = MediaRecorder.isTypeSupported('video/mp4') ? 'video/mp4' : 'video/webm;codecs=vp8';
    const recorder = new MediaRecorder(stream, {{ mimeType: mime, videoBitsPerSecond: 1800000 }});

    recorder.ondataavailable = (e) => {{ if (e.data && e.data.size > 0) chunks.push(e.data); }};
    recorder.onstop = () => {{
        isRecording = false;
        const blob = new Blob(chunks, {{ type: mime }});
        const mb = (blob.size / (1024 * 1024)).toFixed(1);
        const url = URL.createObjectURL(blob);
        outVid.src = url;
        dlAnchor.href = url;
        dlAnchor.download = mime.includes('mp4') ? `RecapMM_${{mb}}MB.mp4` : `RecapMM_${{mb}}MB.webm`;
        dlAnchor.innerText = `📥 MP4 Download (${{mb}} MB)`;
        banner.innerText = `✅ အောင်မြင်စွာ ပြီးဆုံးပါပြီ! (ဖိုင်ဆိုဒ်: ${{mb}} MB)`;
        outWrap.style.display = 'block';
    }};

    video.currentTime = 0;
    video.play();
    recorder.start(200);

    video.onended = () => {{
        if (recorder.state === 'recording') recorder.stop();
    }};
}}
</script>
</body>
</html>
"""

components.html(APP_HTML, height=900, scrolling=False)
