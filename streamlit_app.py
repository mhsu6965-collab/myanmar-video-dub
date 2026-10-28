import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="RecapMM • Studio99 Smart Sync",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Streamlit ရဲ့ အပေါ်အောက်ဘောင်များကို ဖျောက်ပြီး မျက်နှာပြင်အပြည့် (100dvh) ထားရှိခြင်း
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
        user-select: none;
        -webkit-user-select: none;
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
    .split-layout {{
        display: flex;
        flex-direction: column;
        width: 100%;
        max-width: 500px;
        height: 100dvh;
        margin: 0 auto;
        background: var(--bg-main);
    }}
    /* ==================== ၁။ အပေါ်ပိုင်း FIXED 9:16 VIDEO PANE ==================== */
    .fixed-video-pane {{
        flex: 0 0 auto;
        background: #FFFFFF;
        border-bottom: 2px solid #CBD5E1;
        padding: 8px 12px 10px 12px;
        z-index: 100;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
    }}
    .topbar-compact {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }}
    .brand-logo {{
        font-size: 1.02rem;
        font-weight: 800;
        color: #EA580C;
        line-height: 1.2;
    }}
    .brand-logo span {{
        color: #0F172A;
    }}
    .top-right-btns {{
        display: flex;
        align-items: center;
        gap: 6px;
    }}
    .gallery-btn {{
        background: #0F172A;
        color: #FFFFFF;
        border: 1.5px solid #14B8A6;
        padding: 6px 11px;
        border-radius: 10px;
        font-size: 0.78rem;
        font-weight: 700;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 5px;
        box-shadow: 0 2px 8px rgba(20, 184, 166, 0.25);
    }}
    .key-btn {{
        background: #F1F5F9;
        color: #0F172A;
        border: 1px solid #CBD5E1;
        border-radius: 10px;
        padding: 6px 10px;
        font-size: 0.78rem;
        font-weight: 700;
        cursor: pointer;
    }}
    .stage-outer {{
        width: 100%;
        display: flex;
        justify-content: center;
        align-items: center;
        background: #0F172A;
        border-radius: 14px;
        padding: 6px 0;
        border: 1px solid #334155;
        position: relative;
    }}
    .canvas-916-box {{
        position: relative;
        height: 245px;
        aspect-ratio: 9 / 16;
        background: #000000;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 0 0 1.5px rgba(255,255,255,0.15);
        touch-action: none;
    }}
    canvas {{
        width: 100%;
        height: 100%;
        display: block;
        touch-action: none;
    }}
    .sync-badge {{
        position: absolute;
        top: 10px;
        right: 12px;
        background: rgba(16, 185, 129, 0.9);
        color: #FFFFFF;
        font-size: 0.68rem;
        font-weight: 800;
        padding: 3px 8px;
        border-radius: 6px;
        pointer-events: none;
    }}
    .player-bar {{
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 8px;
        padding: 5px 10px;
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
    }}
    .play-btn {{
        background: var(--accent-orange);
        color: #FFFFFF;
        border: none;
        border-radius: 7px;
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
        min-width: 72px;
        text-align: right;
    }}

    /* ==================== ၂။ အောက်ပိုင်း SCROLLABLE TOOLS PANE ==================== */
    .scrollable-tools-pane {{
        flex: 1 1 auto;
        overflow-y: auto;
        -webkit-overflow-scrolling: touch;
        padding: 12px 12px 100px 12px;
    }}
    .card {{
        background: var(--bg-card);
        border: 1px solid var(--border-clr);
        border-radius: 16px;
        padding: 14px;
        margin-bottom: 12px;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.03);
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
        font-size: 0.96rem;
        font-weight: 800;
        color: var(--text-dark);
    }}
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
    input:checked + .slider-pill.green {{ background-color: #10B981; }}
    input:checked + .slider-pill:before {{ transform: translateX(20px); }}

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
    .sc-sub {{ font-size: 0.76rem; color: var(--text-muted); margin-top: 2px; }}

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
    .btn-primary {{
        width: 100%;
        padding: 13px;
        background: linear-gradient(90deg, #EA580C 0%, #F97316 100%);
        color: #FFFFFF;
        border: none;
        border-radius: 12px;
        font-weight: 800;
        font-size: 0.94rem;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(234, 88, 12, 0.25);
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
        font-size: 0.85rem;
        cursor: pointer;
        margin-bottom: 8px;
    }}
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

    .progress-card {{
        margin-top: 10px;
        padding: 12px;
        border-radius: 12px;
        background: #F8FAFC;
        border: 1.5px solid #0284C7;
        display: none;
    }}
    .prog-bar-bg {{
        width: 100%;
        height: 10px;
        background: #E2E8F0;
        border-radius: 8px;
        overflow: hidden;
        margin: 8px 0;
    }}
    .prog-bar-fill {{
        height: 100%;
        width: 0%;
        background: linear-gradient(90deg, #0284C7, #10B981);
        transition: width 0.2s;
    }}
    .prog-step-txt {{
        font-size: 0.82rem;
        font-weight: 700;
        color: #0F172A;
    }}
    .prog-sub-txt {{
        font-size: 0.75rem;
        color: #475569;
        margin-top: 2px;
    }}
</style>
</head>
<body>

<div class="split-layout">

    <!-- ==================== ၁။ အပေါ်ပိုင်း FIXED 9:16 VIDEO PANE ==================== -->
    <div class="fixed-video-pane">
        <div class="topbar-compact">
            <div class="brand-logo">Recap<span>MM</span> • Studio99</div>
            <div class="top-right-btns">
                <label class="gallery-btn">
                    <span>🖼️ Gallery မှ ရွေးမည်</span>
                    <input type="file" id="galleryVideoInput" accept="video/*" style="display:none">
                </label>
                <button class="key-btn" onclick="toggleApiModal()">🔑 Keys</button>
            </div>
        </div>

        <div class="stage-outer">
            <div class="sync-badge" id="smartSyncIndicator">⚡ Smart Sync: 1.00x</div>
            <div class="canvas-916-box" id="canvasBox">
                <canvas id="mainCanvas" width="540" height="960"></canvas>
            </div>
        </div>

        <div class="player-bar">
            <button class="play-btn" id="playBtn">▶</button>
            <input type="range" class="seek-bar" id="seekBar" min="0" max="100" step="0.05" value="0">
            <span class="time-label" id="timeLabel">0:00 / 0:00</span>
        </div>
    </div>

    <!-- ==================== ၂။ အောက်ပိုင်း SCROLLABLE TOOLS PANE ==================== -->
    <div class="scrollable-tools-pane">

        <!-- API KEYS DRAWER -->
        <div class="card" id="apiModal" style="display:none; border-color:#0284C7;">
            <div class="step-title" style="margin-bottom:8px;">🔑 API Keys (တစ်ခါထည့်ထားရုံဖြင့် အမြဲမှတ်ထားမည်)</div>
            <div style="margin-bottom:8px;">
                <label style="font-size:0.78rem;font-weight:700;">Groq API Key:</label>
                <input type="password" id="groqKeyInput" value="{default_groq}" placeholder="gsk_..." style="width:100%;padding:8px;border-radius:8px;border:1px solid #CBD5E1;margin-top:3px;user-select:text;-webkit-user-select:text;">
            </div>
            <div style="margin-bottom:8px;">
                <label style="font-size:0.78rem;font-weight:700;">Gemini API Key:</label>
                <input type="password" id="geminiKeyInput" value="{default_gemini}" placeholder="AIzaSy..." style="width:100%;padding:8px;border-radius:8px;border:1px solid #CBD5E1;margin-top:3px;user-select:text;-webkit-user-select:text;">
            </div>
            <button class="btn-secondary" style="margin-bottom:0;" onclick="saveKeysToLocal()">✅ သိမ်းဆည်းမည်</button>
        </div>

        <!-- BLUR MASK & 9:16 RATIO CARD -->
        <div class="card">
            <div class="step-title" style="margin-bottom:6px;">🌫️ Blur Mask (9:16 Video ပေါ်တွင် လက်ဖြင့်ဆွဲရွှေ့ပါ)</div>
            <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:8px;">🔒 မူရင်း Video ကို ရွှေ့မရအောင် ပုံသေထားထားပါသည်။ Blur နှင့် မြန်မာစာတန်းကိုသာ လက်ဖြင့် ဖိဆွဲရွှေ့နိုင်ပါသည်။</div>

            <div class="blur-item">
                <div style="display:flex;align-items:center;gap:10px;">
                    <label class="switch">
                        <input type="checkbox" id="blur1Chk" checked>
                        <span class="slider-pill cyan"></span>
                    </label>
                    <span style="font-weight:700;color:#0284C7;font-size:0.86rem;">Blur 1 (အောက်စာတန်း)</span>
                </div>
                <button class="btn-secondary" style="width:auto;padding:4px 9px;margin:0;font-size:0.75rem;" onclick="resetBlur1()">နေရာပြန်ချိန်</button>
            </div>

            <div class="blur-item">
                <div style="display:flex;align-items:center;gap:10px;">
                    <label class="switch">
                        <input type="checkbox" id="blur2Chk">
                        <span class="slider-pill pink"></span>
                    </label>
                    <span style="font-weight:700;color:#C026D3;font-size:0.86rem;">Blur 2 (အပေါ် Logo)</span>
                </div>
                <button class="btn-secondary" style="width:auto;padding:4px 9px;margin:0;font-size:0.75rem;" onclick="clearAllBlurs()">🗑️ Blur အားလုံးဖျက်</button>
            </div>

            <div class="slider-group" style="margin-top:8px;">
                <div class="slider-head">
                    <span>Blur အထူ (Opacity)</span>
                    <span id="blurOpVal">100%</span>
                </div>
                <input type="range" class="full-slider" id="blurOpacity" min="0" max="100" value="100" oninput="document.getElementById('blurOpVal').innerText=this.value+'%'">
            </div>

            <hr style="border:none;border-top:1px solid #E2E8F0;margin:10px 0;">

            <div class="step-title" style="font-size:0.9rem;">📐 Video Ratio & 9:16 Background</div>
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

        <!-- STEP 1: GEMINI VISION + SMART SYNC SCRIPT -->
        <div class="card">
            <div class="step-head">
                <div class="step-num">1</div>
                <div class="step-title">Gemini Vision (Video ကြည့်၍ ဘာသာပြန်ခြင်း) + Smart Sync</div>
            </div>

            <div class="blur-item" style="border-color:#A7F3D0;background:#ECFDF5;">
                <div>
                    <div style="font-weight:800;font-size:0.86rem;color:#065F46;">⚡ Smart Auto-Sync (ရုပ် + အသံ + စာတန်း)</div>
                    <div style="font-size:0.73rem;color:#047857;">စကားပြောအရှည်ပေါ်မူတည်၍ Video နှင့် TTS အသံကို မြန်သင့်ရင်မြန် / နှေးသင့်ရင်နှေး အလိုအလျောက် ချိန်ညှိပေးမည်</div>
                </div>
                <label class="switch">
                    <input type="checkbox" id="smartSyncChk" checked>
                    <span class="slider-pill green"></span>
                </label>
            </div>

            <div class="select-card active" onclick="selectNarration('direct', this)">
                <div class="sc-title">Direct Translation (Gemini Vision + Audio)</div>
                <div class="sc-sub">Gemini က Video ပုံရိပ်နှင့် စကားပြောကို ကြည့်ပြီး မူရင်းအဓိပ္ပာယ်အတိုင်း ဘာသာပြန်မယ်</div>
            </div>
            <div class="select-card" onclick="selectNarration('third', this)">
                <div class="sc-title">Third Person (Movie Recap ပုံစံ)</div>
                <div class="sc-sub">Gemini က ဗီဒီယိုဇာတ်ဝင်ခန်းများကို ကြည့်ပြီး ပြင်ပဇာတ်ကြောင်းပြောသူအနေနဲ့ ပြောမယ်</div>
            </div>
            <div class="select-card" onclick="selectNarration('first', this)">
                <div class="sc-title">First Person (အဓိကဇာတ်ကောင် POV)</div>
                <div class="sc-sub">အဓိကဇာတ်ကောင် ကိုယ်တိုင်ပြောသလို ဘာသာပြန်မယ်</div>
            </div>

            <button class="btn-primary" id="genScriptBtn" onclick="runGeminiVisionAndSmartSync()" style="margin-top:8px;">
                👁️ Gemini ဖြင့် Video ကြည့်၍ Script + Smart Sync ထုတ်မယ်
            </button>

            <div class="progress-card" id="aiProgressCard">
                <div class="prog-step-txt" id="aiStepTitle">⏳ စတင်နေပါသည်...</div>
                <div class="prog-bar-bg"><div class="prog-bar-fill" id="aiProgFill"></div></div>
                <div class="prog-sub-txt" id="aiStepDetail">ဗီဒီယိုပုံရိပ်နှင့် အသံလမ်းကြောင်းကို ဖတ်ယူနေပါသည်...</div>
            </div>
        </div>

        <!-- STEP 2: VOICEOVER အသံ နှင့် SPEED % / PITCH % -->
        <div class="card">
            <div class="step-head">
                <div class="step-num">2</div>
                <div class="step-title">Voiceover အသံ နှင့် Speed / Pitch (%)</div>
            </div>

            <div id="voiceListContainer">
                <div class="voice-row" onclick="selectVoice(0, this)">
                    <span style="font-weight:700;font-size:0.86rem;">မိန်းကလေး ၁ - တည်ငြိမ်</span>
                    <button class="v-sample-btn" onclick="event.stopPropagation();previewVoice(0)">▶</button>
                </div>
                <div class="voice-row" onclick="selectVoice(1, this)">
                    <span style="font-weight:700;font-size:0.86rem;">မိန်းကလေး ၂ - ပေါ့ပါး</span>
                    <button class="v-sample-btn" onclick="event.stopPropagation();previewVoice(1)">▶</button>
                </div>
                <div class="voice-row" onclick="selectVoice(2, this)">
                    <span style="font-weight:700;font-size:0.86rem;">မိန်းကလေး ၃ - နုပျို</span>
                    <button class="v-sample-btn" onclick="event.stopPropagation();previewVoice(2)">▶</button>
                </div>
                <div class="voice-row" onclick="selectVoice(3, this)">
                    <span style="font-weight:700;font-size:0.86rem;">ယောက်ျား ၁ - တက်ကြွ</span>
                    <button class="v-sample-btn" onclick="event.stopPropagation();previewVoice(3)">▶</button>
                </div>
                <div class="voice-row active" onclick="selectVoice(4, this)">
                    <span style="font-weight:700;font-size:0.86rem;">ယောက်ျား ၂ - လေးနက်</span>
                    <button class="v-sample-btn" onclick="event.stopPropagation();previewVoice(4)">▶</button>
                </div>
                <div class="voice-row" onclick="selectVoice(5, this)">
                    <span style="font-weight:700;font-size:0.86rem;">ယောက်ျား ၃ - စိတ်လှုပ်ရှား</span>
                    <button class="v-sample-btn" onclick="event.stopPropagation();previewVoice(5)">▶</button>
                </div>
            </div>

            <div class="slider-group" style="margin-top:12px;">
                <div class="slider-head">
                    <span>⚡ TTS အသံ Speed (%)</span>
                    <span id="ttsSpeedVal">+0%</span>
                </div>
                <input type="range" class="full-slider" id="ttsSpeedSlider" min="-50" max="100" step="5" value="0" oninput="document.getElementById('ttsSpeedVal').innerText=(this.value>=0?'+':'')+this.value+'%'">
            </div>

            <div class="slider-group">
                <div class="slider-head">
                    <span>🎵 TTS အသံ Pitch (%)</span>
                    <span id="ttsPitchVal">+0%</span>
                </div>
                <input type="range" class="full-slider" id="ttsPitchSlider" min="-50" max="50" step="5" value="0" oninput="document.getElementById('ttsPitchVal').innerText=(this.value>=0?'+':'')+this.value+'%'">
            </div>

            <div class="slider-group">
                <div class="slider-head">
                    <span>⏱️ အသံ အစော / အနောက် ချိန်</span>
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
                <span style="font-weight:700;font-size:0.86rem;">ဘယ်ညာ ပြောင်းပြန်လှည့် (Mirror)</span>
                <label class="switch">
                    <input type="checkbox" id="mirrorChk">
                    <span class="slider-pill orange"></span>
                </label>
            </div>

            <div class="blur-item">
                <span style="font-weight:700;font-size:0.86rem;">မြန်မာစာတန်း video ထဲ ထည့်မယ်</span>
                <label class="switch">
                    <input type="checkbox" id="showSubChk" checked>
                    <span class="slider-pill orange"></span>
                </label>
            </div>

            <div class="font-grid">
                <div class="font-card active" onclick="selectFont('Noto Sans Myanmar', this)">
                    <div style="font-size:0.92rem;font-weight:700;">မင်္ဂလာပါ</div>
                    <div style="font-size:0.7rem;color:var(--text-muted);">Noto Sans</div>
                </div>
                <div class="font-card" onclick="selectFont('Noto Serif Myanmar', this)">
                    <div style="font-size:0.92rem;font-family:'Noto Serif Myanmar';font-weight:700;">မင်္ဂလာပါ</div>
                    <div style="font-size:0.7rem;color:var(--text-muted);">Noto Serif</div>
                </div>
                <div class="font-card" onclick="selectFont('Padauk', this)">
                    <div style="font-size:0.92rem;font-family:'Padauk';font-weight:700;">မင်္ဂလာပါ</div>
                    <div style="font-size:0.7rem;color:var(--text-muted);">Padauk</div>
                </div>
                <div class="font-card" onclick="document.getElementById('customFontInput').click()">
                    <div style="font-size:0.88rem;font-weight:700;color:var(--accent-orange);">＋ Custom Font</div>
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
                <div class="slider-head"><span>စာလုံးအရွယ် (%)</span><span id="subScaleTxt">85%</span></div>
                <input type="range" class="full-slider" id="subScaleSlider" min="55" max="130" value="85" oninput="document.getElementById('subScaleTxt').innerText=this.value+'%'">
            </div>

            <button class="btn-secondary" onclick="resetSubPos()">စာတန်းနေရာ မူလအတိုင်း ပြန်ထားမယ်</button>

            <hr style="border:none;border-top:1px solid #E2E8F0;margin:10px 0;">

            <!-- CHANNEL WATERMARK -->
            <div class="blur-item">
                <span style="font-weight:700;font-size:0.86rem;">Channel Watermark ထည့်မယ်</span>
                <label class="switch">
                    <input type="checkbox" id="wmChk" checked>
                    <span class="slider-pill orange"></span>
                </label>
            </div>
            <input type="text" id="wmTextInput" value="MY RECAP" placeholder="Channel အမည်" style="width:100%;padding:8px 10px;border-radius:10px;border:1px solid #CBD5E1;font-weight:700;margin-bottom:8px;user-select:text;-webkit-user-select:text;">

            <div class="slider-group">
                <div class="slider-head"><span>Opacity (%)</span><span id="wmOpTxt">55%</span></div>
                <input type="range" class="full-slider" id="wmOpSlider" min="10" max="100" value="55" oninput="document.getElementById('wmOpTxt').innerText=this.value+'%'">
            </div>
            <div class="slider-group">
                <div class="slider-head"><span>စာလုံးအရွယ် (%)</span><span id="wmSzTxt">95%</span></div>
                <input type="range" class="full-slider" id="wmSzSlider" min="50" max="150" value="95" oninput="document.getElementById('wmSzTxt').innerText=this.value+'%'">
            </div>

            <hr style="border:none;border-top:1px solid #E2E8F0;margin:10px 0;">

            <!-- COPYRIGHT FILTERS -->
            <div class="slider-group">
                <div class="slider-head"><span>Zoom (%)</span><span id="zoomTxt">100%</span></div>
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
                <div class="slider-head"><span>မူရင်းအသံ (%)</span><span id="origVolTxt">0%</span></div>
                <input type="range" class="full-slider" id="origVolSlider" min="0" max="100" value="0" oninput="document.getElementById('origVolTxt').innerText=this.value+'%'">
            </div>
            <div class="slider-group">
                <div class="slider-head"><span>Voiceover အသံ (%)</span><span id="voVolTxt">100%</span></div>
                <input type="range" class="full-slider" id="voVolSlider" min="20" max="100" value="100" oninput="document.getElementById('voVolTxt').innerText=this.value+'%'">
            </div>
            <button class="btn-secondary" onclick="resetVisualFilters()">Reset</button>
        </div>

        <!-- STEP 4: ထုတ်ယူမယ် (SMART SYNC LOCAL RENDER WITH LIVE PROGRESS) -->
        <div class="card">
            <div class="step-head">
                <div class="step-num">4</div>
                <div class="step-title">ထုတ်ယူမယ် (Smart Sync Render)</div>
            </div>

            <button class="btn-secondary" onclick="downloadSRTFile()">📄 မြန်မာ SRT Download</button>
            <button class="btn-primary" id="renderFinalBtn" onclick="startSmartSyncLocalRender()">📥 Recap Video ထုတ်မယ် (Smart Sync)</button>

            <div class="progress-card" id="renderProgressCard">
                <div class="prog-step-txt" id="renderStepTitle">⏳ Video Render ပြုလုပ်နေပါသည်...</div>
                <div class="prog-bar-bg"><div class="prog-bar-fill" id="renderProgFill"></div></div>
                <div class="prog-sub-txt" id="renderStepDetail">0% ပြီးစီးပါပြီ</div>
            </div>

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
const canvasBox = document.getElementById('canvasBox');
const playBtn = document.getElementById('playBtn');
const seekBar = document.getElementById('seekBar');
const timeLabel = document.getElementById('timeLabel');
const smartSyncIndicator = document.getElementById('smartSyncIndicator');

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

// Smart Sync ပါဝင်သော Segments (vidSpeed နှင့် ttsRate ကို စာကြောင်းအလိုက် အလိုအလျောက် တွက်ချက်ပေးသည်)
let segments = [
    {{ start: 0.0, end: 3.5, text: "ပြန်စရာအိမ်မရှိတော့တဲ့ ဇနီးမောင်နှံနှစ်ယောက်", vidSpeed: 1.0, ttsRate: 1.0 }},
    {{ start: 3.5, end: 7.5, text: "မြို့ပေါ်က သားငယ်ဆီမှာ တည်းခိုဖို့ စဉ်းစားခဲ့တယ်", vidSpeed: 1.0, ttsRate: 1.0 }}
];

let synthesizedAudioMap = {{}};
let activeSpeechAudio = new Audio();
let audioCtxGlobal = null;
let ttsGainNode = null;

let boxes = {{
    blur1: {{ x: 0.06, y: 0.72, w: 0.88, h: 0.10, color: '#00E5FF' }},
    blur2: {{ x: 0.06, y: 0.06, w: 0.40, h: 0.08, color: '#D946EF' }},
    sub:   {{ x: 0.50, y: 0.77 }},
    wm:    {{ x: 0.78, y: 0.06 }}
}};

window.addEventListener('DOMContentLoaded', () => {{
    const savedGroq = localStorage.getItem('s99_groq_key');
    const savedGemini = localStorage.getItem('s99_gemini_key');
    if (savedGroq && !document.getElementById('groqKeyInput').value) document.getElementById('groqKeyInput').value = savedGroq;
    if (savedGemini && !document.getElementById('geminiKeyInput').value) document.getElementById('geminiKeyInput').value = savedGemini;
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

// ==================== INSTANT LOCAL GALLERY VIDEO LOAD ====================
document.getElementById('galleryVideoInput').addEventListener('change', function(e) {{
    const file = e.target.files[0];
    if (!file) return;
    currentVideoFile = file;
    video.src = URL.createObjectURL(file);
    video.load();
    video.onloadedmetadata = () => {{
        seekBar.max = video.duration || 100;
        video.currentTime = Math.min(0.5, (video.duration || 1) * 0.05);
        timeLabel.innerText = `0:00 / ${{fmtTime(video.duration || 0)}}`;
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
    syncSmartVideoAndVoice(video.currentTime);
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
        if (Math.abs(pt.x - boxes.sub.x) < 0.42 && Math.abs(pt.y - boxes.sub.y) < 0.065) return {{ key: 'sub', mode: 'move' }};
    }}
    if (document.getElementById('wmChk').checked) {{
        if (Math.abs(pt.x - boxes.wm.x) < 0.22 && Math.abs(pt.y - boxes.wm.y) < 0.055) return {{ key: 'wm', mode: 'move' }};
    }}
    const checkRect = (b) => {{
        const rx = b.x + b.w, ry = b.y + b.h;
        if (Math.abs(pt.x - rx) < 0.08 && Math.abs(pt.y - ry) < 0.07) return 'resize';
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
        boxes[activeDrag].x = Math.min(0.90, Math.max(0.10, origBox.x + dx));
        boxes[activeDrag].y = Math.min(0.94, Math.max(0.05, origBox.y + dy));
    }} else {{
        if (dragMode === 'move') {{
            boxes[activeDrag].x = Math.min(1.0 - origBox.w, Math.max(0.0, origBox.x + dx));
            boxes[activeDrag].y = Math.min(1.0 - origBox.h, Math.max(0.0, origBox.y + dy));
        }} else {{
            boxes[activeDrag].w = Math.min(1.0 - origBox.x, Math.max(0.14, origBox.w + dx));
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

// ==================== 60FPS 9:16 CANVAS RENDER LOOP ====================
function cleanMyanmarText(txt) {{
    if (!txt) return "";
    return String(txt).replace(/[\u200b\u200c\u200d\ufeff]/g, "").trim();
}}

function wrapMyanmarSubtitleLines(ctx, text, maxWidth) {{
    if (ctx.measureText(text).width <= maxWidth) return [text];
    const mid = Math.floor(text.length / 2);
    let splitIdx = text.lastIndexOf(' ', mid + 6);
    if (splitIdx === -1 || splitIdx < 4) splitIdx = mid;
    return [text.slice(0, splitIdx).trim(), text.slice(splitIdx).trim()];
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
        ctx.font = '700 24px "Noto Sans Myanmar", sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('▶ Gallery မှ ဗီဒီယိုရွေးပါ', cw / 2, ch / 2);
    }}

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
            ctx.arc(bx + bw, by + bh, 11, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        }}
    }};
    renderBlurBox(boxes.blur1, document.getElementById('blur1Chk').checked);
    renderBlurBox(boxes.blur2, document.getElementById('blur2Chk').checked);

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
            const fontPx = Math.round(23 * scalePct * (cw / 540.0));
            ctx.save();
            ctx.font = `700 ${{fontPx}}px "${{selectedFontFamily}}", "Noto Sans Myanmar", sans-serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';

            const maxAllowedW = cw * 0.88;
            const lines = wrapMyanmarSubtitleLines(ctx, subLine, maxAllowedW);
            const lineHeight = fontPx * 1.35;
            const totalH = lines.length * lineHeight;
            let maxW = 0;
            lines.forEach(l => {{ const w = ctx.measureText(l).width; if (w > maxW) maxW = w; }});

            const sx = boxes.sub.x * cw, sy = boxes.sub.y * ch;

            ctx.fillStyle = 'rgba(15, 15, 15, 0.74)';
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.22)';
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.roundRect(sx - maxW / 2 - 16, sy - totalH / 2 - 6, maxW + 32, totalH + 12, 12);
            ctx.fill();
            ctx.stroke();

            ctx.lineWidth = Math.max(3.5, fontPx * 0.16);
            ctx.strokeStyle = '#000000';
            lines.forEach((l, idx) => {{
                const ly = (sy - totalH / 2) + (idx + 0.5) * lineHeight;
                ctx.strokeText(l, sx, ly);
                ctx.fillStyle = selectedSubColor;
                ctx.fillText(l, sx, ly);
            }});
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
    if (r === '9:16') {{ canvas.width = 540; canvas.height = 960; canvasBox.style.aspectRatio = '9 / 16'; }}
    else if (r === '16:9') {{ canvas.width = 854; canvas.height = 480; canvasBox.style.aspectRatio = '16 / 9'; }}
    else if (r === '1:1') {{ canvas.width = 640; canvas.height = 640; canvasBox.style.aspectRatio = '1 / 1'; }}
    else if (r === '4:3') {{ canvas.width = 640; canvas.height = 480; canvasBox.style.aspectRatio = '4 / 3'; }}
    wakeHandles();
}}

function resetBlur1() {{ boxes.blur1 = {{ x: 0.06, y: 0.72, w: 0.88, h: 0.10, color: '#00E5FF' }}; wakeHandles(); }}
function clearAllBlurs() {{ document.getElementById('blur1Chk').checked = false; document.getElementById('blur2Chk').checked = false; }}
function resetSubPos() {{ boxes.sub = {{ x: 0.50, y: 0.77 }}; wakeHandles(); }}
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

const voiceConfigs = [
    {{ pitch: 1.0, rate: 0 }},
    {{ pitch: 1.1, rate: 8 }},
    {{ pitch: 1.2, rate: 5 }},
    {{ pitch: 0.95, rate: 10 }},
    {{ pitch: 0.85, rate: 0 }},
    {{ pitch: 1.0, rate: 15 }}
];

function selectVoice(idx, el) {{
    selectedVoiceIdx = idx;
    document.querySelectorAll('.voice-row').forEach(r => r.classList.remove('active'));
    el.classList.add('active');
    document.getElementById('ttsSpeedSlider').value = voiceConfigs[idx].rate;
    document.getElementById('ttsSpeedVal').innerText = (voiceConfigs[idx].rate >= 0 ? '+' : '') + voiceConfigs[idx].rate + '%';
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

// ==================== 1. VIDEO KEYFRAMES EXTRACTOR FOR GEMINI VISION ====================
async function captureVideoKeyframesBase64(vidEl, count = 4) {{
    const frames = [];
    const origTime = vidEl.currentTime;
    const dur = Math.max(1.0, vidEl.duration || 10.0);
    const tmpCanvas = document.createElement('canvas');
    tmpCanvas.width = 320;
    tmpCanvas.height = 568;
    const tCtx = tmpCanvas.getContext('2d');

    for (let i = 0; i < count; i++) {{
        const targetT = Math.min(dur - 0.2, (dur / (count + 1)) * (i + 1));
        vidEl.currentTime = targetT;
        await new Promise(res => {{
            const onSeek = () => {{ vidEl.removeEventListener('seeked', onSeek); res(); }};
            vidEl.addEventListener('seeked', onSeek);
            setTimeout(res, 400);
        }});
        tCtx.drawImage(vidEl, 0, 0, tmpCanvas.width, tmpCanvas.height);
        const b64 = tmpCanvas.toDataURL('image/jpeg', 0.65).split(',')[1];
        if (b64) frames.push(b64);
    }}
    vidEl.currentTime = origTime;
    return frames;
}}

// ==================== 2. FAST 8KHz WAV AUDIO EXTRACTOR ====================
async function extractFastAudioBlob(file) {{
    const arrayBuf = await file.arrayBuffer();
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const decoded = await audioCtx.decodeAudioData(arrayBuf);
    const sampleRate = 8000;
    const offlineCtx = new OfflineAudioContext(1, Math.floor(decoded.duration * sampleRate), sampleRate);
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
    view.setUint16(22, 1, true); view.setUint32(24, sampleRate, true); view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true); view.setUint16(34, 16, true); writeStr(36, 'data');
    view.setUint32(40, pcm.length * 2, true);
    let offset = 44;
    for (let i = 0; i < pcm.length; i++, offset += 2) {{
        let s = Math.max(-1, Math.min(1, pcm[i]));
        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }}
    return new Blob([wavBuf], {{ type: 'audio/wav' }});
}}

// ==================== 3. SAFE JSON PARSER & MULTI-MODEL GEMINI VISION TRANSLATOR ====================
function safeExtractJsonMap(rawText) {{
    const map = {{}};
    if (!rawText) return map;
    try {{
        let cleaned = rawText.replace(/```json/gi, '').replace(/```/g, '').trim();
        const parsed = JSON.parse(cleaned);
        const list = Array.isArray(parsed) ? parsed : (parsed.items || parsed.translations || parsed.data || []);
        if (Array.isArray(list)) {{
            list.forEach(item => {{
                if (item && item.id !== undefined && item.translation) {{
                    map[parseInt(item.id)] = String(item.translation).trim();
                }}
            }});
        }}
    }} catch (e) {{
        console.warn("JSON fallback regex parse:", e);
    }}
    return map;
}}

async function translateWithGeminiVisionAndFallback(rawSegments, keyframesB64, geminiKey, groqKey, stylePrompt, updateProg) {{
    const finalTransMap = {{}};
    const batchSize = 20;
    const geminiModels = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash'];

    for (let b = 0; b < rawSegments.length; b += batchSize) {{
        const chunk = rawSegments.slice(b, b + batchSize);
        const payload = chunk.map((s, idx) => ({{ id: b + idx, text: s.text }}));
        const pct = Math.min(82, 45 + Math.round((b / rawSegments.length) * 35));
        updateProg(pct, "👁️ အဆင့် ၃/၄ - Gemini Vision ဘာသာပြန်စနစ်", `ဗီဒီယိုပုံရိပ်များကို ကြည့်၍ စာကြောင်း (${{b + 1}} မှ ${{b + chunk.length}}) ကို မြန်မာဘာသာပြန်နေပါသည်...`);

        let batchSuccess = false;

        // Gemini Vision Models စမ်းသပ်ခြင်း (Cannot read properties of undefined reading '0' လုံးဝမဖြစ်စေရန် Safe Check ပါဝင်သည်)
        for (const mName of geminiModels) {{
            try {{
                const parts = [];
                if (b === 0 && keyframesB64.length > 0) {{
                    keyframesB64.forEach(b64 => {{
                        parts.push({{ inlineData: {{ mimeType: "image/jpeg", data: b64 }} }});
                    }});
                }}
                parts.push({{
                    text: `You are watching these keyframes from a video. ${{stylePrompt}}\nTranslate each item into natural, concise spoken Burmese (Myanmar) so it fits the speaking duration. Do NOT use emojis. Return ONLY a valid JSON array of objects with keys "id" and "translation":\n${{JSON.stringify(payload)}}`
                }});

                const gUrl = `https://generativelanguage.googleapis.com/v1beta/models/${{mName}}:generateContent?key=${{geminiKey}}`;
                const gResp = await fetch(gUrl, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        contents: [{{ parts: parts }}],
                        generationConfig: {{ responseMimeType: "application/json", temperature: 0.3 }}
                    }})
                }});

                if (gResp.ok) {{
                    const gJson = await gResp.json();
                    const candText = gJson && gJson.candidates && gJson.candidates[0] && gJson.candidates[0].content && gJson.candidates[0].content.parts && gJson.candidates[0].content.parts[0] ? gJson.candidates[0].content.parts[0].text : null;
                    if (candText) {{
                        const parsedMap = safeExtractJsonMap(candText);
                        if (Object.keys(parsedMap).length > 0) {{
                            Object.assign(finalTransMap, parsedMap);
                            batchSuccess = true;
                            break;
                        }}
                    }}
                }}
            }} catch (err) {{
                console.warn(`Gemini model ${{mName}} retry:`, err);
            }}
        }}

        // အကယ်၍ Gemini Key သို့မဟုတ် Model အခက်အခဲရှိပါက Groq Llama-3.3-70B က ချက်ချင်း ဝင်ရောက်ဘာသာပြန်ပေးမည်
        if (!batchSuccess) {{
            const bResp = await fetch('https://api.groq.com/openai/v1/chat/completions', {{
                method: 'POST',
                headers: {{ 'Authorization': 'Bearer ' + groqKey, 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    model: 'llama-3.3-70b-versatile',
                    messages: [
                        {{ role: 'system', content: `${{stylePrompt}} Translate into concise spoken Burmese (Myanmar). Output valid JSON only.` }},
                        {{ role: 'user', content: `Return a JSON object with key "items" containing an array of objects with "id" and "translation":\n${{JSON.stringify(payload)}}` }}
                    ],
                    response_format: {{ type: 'json_object' }}
                }})
            }});
            if (bResp.ok) {{
                const bJson = await bResp.json();
                const contentTxt = bJson && bJson.choices && bJson.choices[0] && bJson.choices[0].message ? bJson.choices[0].message.content : "";
                const parsedMap = safeExtractJsonMap(contentTxt);
                Object.assign(finalTransMap, parsedMap);
            }}
        }}
    }}
    return finalTransMap;
}}

// ==================== 4. SMART SYNC CALCULATOR (VIDEO SPEED + TTS SPEED + SRT TIMING) ====================
function computeSmartSyncParameters(segList, userBaseSpeedPct) {{
    const baseRate = Math.max(0.6, Math.min(1.8, 1.0 + (userBaseSpeedPct / 100.0)));
    return segList.map(seg => {{
        const slotDur = Math.max(0.4, seg.end - seg.start);
        // မြန်မာစာလုံး အရေအတွက်ပေါ်မူတည်၍ ကြာချိန်ကို ခန့်မှန်းတွက်ချက်ခြင်း (၁ စက္ကန့်လျှင် ပျမ်းမျှ ၁၁ လုံး)
        const charCount = Math.max(1, seg.text.length);
        const estimatedTtsDur = (charCount / 11.5) / baseRate;
        const ratio = estimatedTtsDur / slotDur;

        let ttsRate = baseRate;
        let vidSpeed = 1.0;

        if (ratio > 1.12) {{
            // စာကြောင်းရှည်နေပါက TTS အသံကို မြန်ပေးပြီး Video အပိုင်းကိုပါ အနည်းငယ် နှေးပေးခြင်းဖြင့် ကွက်တိကျစေသည်
            ttsRate = Math.min(1.65, baseRate * Math.pow(ratio, 0.65));
            const remainingRatio = (estimatedTtsDur / (ttsRate / baseRate)) / slotDur;
            vidSpeed = Math.max(0.65, Math.min(1.0, 1.0 / remainingRatio));
        }} else if (ratio < 0.72) {{
            // စာကြောင်းတိုနေပါက Video အပိုင်းကို အနည်းငယ် မြန်ပေးပြီး TTS ကို သဘာဝအတိုင်း နှေးပေးသည်
            ttsRate = Math.max(0.82, baseRate * Math.pow(ratio, 0.35));
            vidSpeed = Math.min(1.45, Math.max(1.0, 1.0 / Math.max(0.65, ratio)));
        }}

        return {{
            ...seg,
            ttsRate: parseFloat(ttsRate.toFixed(2)),
            vidSpeed: parseFloat(vidSpeed.toFixed(2))
        }};
    }});
}}

async function runGeminiVisionAndSmartSync() {{
    const groqKey = document.getElementById('groqKeyInput').value.trim();
    const geminiKey = document.getElementById('geminiKeyInput').value.trim();
    const card = document.getElementById('aiProgressCard');
    const titleEl = document.getElementById('aiStepTitle');
    const fillEl = document.getElementById('aiProgFill');
    const detailEl = document.getElementById('aiStepDetail');

    const updateProg = (pct, title, detail) => {{
        card.style.display = 'block';
        fillEl.style.width = pct + '%';
        titleEl.innerText = `${{title}} (${{pct}}%)`;
        if (detail) detailEl.innerText = detail;
    }};

    if (!currentVideoFile) {{ alert("ကျေးဇူးပြု၍ အပေါ်ဆုံးမှ Gallery ဗီဒီယို အရင်ရွေးပေးပါ။"); return; }}
    if (!groqKey || !geminiKey) {{ toggleApiModal(); alert("Groq နှင့် Gemini API Key ထည့်သွင်းပေးပါ။"); return; }}

    try {{
        updateProg(10, "👁️ အဆင့် ၁/၄ - Video ပုံရိပ်များ ဖမ်းယူနေသည်", "Gemini ကြည့်ရှုနိုင်ရန် Video ထဲမှ အဓိက ဇာတ်ဝင်ခန်းပုံရိပ်များကို ဆွဲထုတ်နေပါသည်...");
        const keyframesB64 = await captureVideoKeyframesBase64(video, 4);

        updateProg(22, "🎧 အဆင့် ၂/၄ - အသံနှင့် စကားပြောချိန် ထုတ်ယူနေသည်", "ဗီဒီယိုထဲမှ အသံကို ဆွဲထုတ်ပြီး Groq Whisper AI ဖြင့် နားထောင်နေပါသည်...");
        const wavBlob = await extractFastAudioBlob(currentVideoFile);

        const formData = new FormData();
        formData.append('file', wavBlob, 'audio.wav');
        formData.append('model', 'whisper-large-v3-turbo');
        formData.append('response_format', 'verbose_json');

        const wResp = await fetch('https://api.groq.com/openai/v1/audio/transcriptions', {{
            method: 'POST',
            headers: {{ 'Authorization': 'Bearer ' + groqKey }},
            body: formData
        }});
        if (!wResp.ok) throw new Error("Groq API Key မှားယွင်းနေပါသည် သို့မဟုတ် အင်တာနက်လိုင်း ပြတ်တောက်နေပါသည်။");
        const wData = await wResp.json();
        const rawSegs = (wData && Array.isArray(wData.segments)) ? wData.segments : [];
        if (rawSegs.length === 0) throw new Error("ဗီဒီယိုထဲတွင် စကားပြောသံ မတွေ့ရှိပါ။");

        let stylePrompt = "Translate directly and naturally into spoken Burmese (Myanmar) keeping original POV.";
        if (narrationStyle === 'third') stylePrompt = "Rewrite and translate into natural Burmese (Myanmar) as a Third-Person movie recap narrator.";
        if (narrationStyle === 'first') stylePrompt = "Rewrite and translate into natural Burmese (Myanmar) from a First-Person main character perspective.";

        const transMap = await translateWithGeminiVisionAndFallback(rawSegs, keyframesB64, geminiKey, groqKey, stylePrompt, updateProg);

        const baseSegs = rawSegs.map((s, idx) => ({{
            start: parseFloat(Number(s.start || 0).toFixed(2)),
            end: parseFloat(Number(s.end || (s.start + 2)).toFixed(2)),
            text: cleanMyanmarText(transMap[idx] || s.text || "")
        }})).filter(s => s.text.length > 0);

        updateProg(88, "⚡ အဆင့် ၄/၄ - Smart Sync ချိန်ညှိနေသည်", "Video ရုပ်၊ မြန်မာ TTS အသံ နှင့် SRT စာတန်း ၃ ခုလုံး ကွက်တိဖြစ်အောင် အနှေး/အမြန် တွက်ချက်နေပါသည်...");
        const userSpd = parseInt(document.getElementById('ttsSpeedSlider').value) || 0;
        segments = computeSmartSyncParameters(baseSegs, userSpd);

        synthesizedAudioMap = {{}};
        for (let i = 0; i < segments.length; i++) {{
            const txt = segments[i].text;
            synthesizedAudioMap[i] = `https://translate.google.com/translate_tts?ie=UTF-8&q=${{encodeURIComponent(txt.slice(0, 180))}}&tl=my&client=tw-ob`;
        }}

        updateProg(100, "✅ Gemini Vision + Smart Sync အောင်မြင်ပါပြီ!", `စာကြောင်း (${{segments.length}}) ကြောင်းကို ရုပ်+အသံ+စာတန်း ချိတ်ဆက်ပြီးပါပြီ။ အပေါ်က Video ကို Play နှိပ်ကြည့်ပါ။`);
    }} catch (err) {{
        updateProg(100, "❌ Error ဖြစ်ပွားပါသည်", err.message || String(err));
    }}
}}

function previewVoice(idx) {{
    const spdPct = parseInt(document.getElementById('ttsSpeedSlider').value) || 0;
    const sampleUrl = `https://translate.google.com/translate_tts?ie=UTF-8&q=${{encodeURIComponent("မင်္ဂလာပါရှင်၊ အသံနမူနာဖြစ်ပါတယ်")}}&tl=my&client=tw-ob`;
    const aud = new Audio(sampleUrl);
    aud.playbackRate = Math.max(0.5, Math.min(2.0, 1.0 + (spdPct / 100.0)));
    aud.play().catch(() => {{}});
}}

// ==================== SMART SYNC PLAYBACK (AUTO VIDEO SPEED + TTS RATE + SRT) ====================
let lastPlayedSegIdx = -1;
function syncSmartVideoAndVoice(curTime) {{
    if (video.paused) return;
    video.volume = parseInt(document.getElementById('origVolSlider').value) / 100.0;
    const offset = parseFloat(document.getElementById('audioOffsetSlider').value) || 0;
    const adjTime = curTime - offset;
    const smartOn = document.getElementById('smartSyncChk').checked;

    let foundIdx = -1;
    for (let i = 0; i < segments.length; i++) {{
        if (adjTime >= segments[i].start && adjTime <= segments[i].end) {{
            foundIdx = i;
            break;
        }}
    }}

    if (foundIdx !== -1) {{
        const seg = segments[foundIdx];
        const targetVidSpeed = smartOn ? (seg.vidSpeed || 1.0) : 1.0;
        if (Math.abs(video.playbackRate - targetVidSpeed) > 0.04) {{
            video.playbackRate = targetVidSpeed;
        }}
        smartSyncIndicator.innerText = `⚡ Smart Sync: Video ${{targetVidSpeed.toFixed(2)}}x | TTS ${{(seg.ttsRate || 1.0).toFixed(2)}}x`;

        if (foundIdx !== lastPlayedSegIdx && synthesizedAudioMap[foundIdx]) {{
            lastPlayedSegIdx = foundIdx;
            const userSpdPct = parseInt(document.getElementById('ttsSpeedSlider').value) || 0;
            const baseUserRate = Math.max(0.5, Math.min(2.0, 1.0 + (userSpdPct / 100.0)));
            const finalTtsRate = smartOn ? (seg.ttsRate || baseUserRate) : baseUserRate;

            activeSpeechAudio.src = synthesizedAudioMap[foundIdx];
            activeSpeechAudio.volume = parseInt(document.getElementById('voVolSlider').value) / 100.0;
            activeSpeechAudio.playbackRate = Math.max(0.5, Math.min(2.2, finalTtsRate));
            activeSpeechAudio.play().catch(() => {{}});
        }}
    }} else {{
        lastPlayedSegIdx = -1;
        if (Math.abs(video.playbackRate - 1.0) > 0.04) video.playbackRate = 1.0;
        smartSyncIndicator.innerText = `⚡ Smart Sync: 1.00x`;
    }}
}}

// ==================== SRT DOWNLOAD & SMART SYNC LOCAL RENDER ====================
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
    a.download = "RecapMM_SmartSync.srt";
    a.click();
}}

function startSmartSyncLocalRender() {{
    if (!video.src) {{ alert("ကျေးဇူးပြု၍ အပေါ်ဆုံးမှ Gallery ဗီဒီယို အရင်ရွေးပေးပါ။"); return; }}
    const pCard = document.getElementById('renderProgressCard');
    const pTitle = document.getElementById('renderStepTitle');
    const pFill = document.getElementById('renderProgFill');
    const pDetail = document.getElementById('renderStepDetail');
    const outWrap = document.getElementById('outputVideoWrap');
    const outVid = document.getElementById('finalOutputPreview');
    const dlAnchor = document.getElementById('finalDownloadAnchor');

    pCard.style.display = 'block';
    outWrap.style.display = 'none';

    isRecording = true;
    showHandles = false;
    const chunks = [];
    const stream = canvas.captureStream(30);

    // WebAudio ဖြင့် TTS အသံကို Video Stream ထဲသို့ တိုက်ရိုက် ပေါင်းထည့်ခြင်း
    try {{
        if (!audioCtxGlobal) {{
            audioCtxGlobal = new (window.AudioContext || window.webkitAudioContext)();
            const dest = audioCtxGlobal.createMediaStreamDestination();
            activeSpeechAudio.crossOrigin = "anonymous";
            const ttsSource = audioCtxGlobal.createMediaElementSource(activeSpeechAudio);
            ttsSource.connect(dest);
            ttsSource.connect(audioCtxGlobal.destination);
            dest.stream.getAudioTracks().forEach(t => stream.addTrack(t));
        }}
    }} catch (e) {{
        console.log("Audio stream note:", e);
    }}

    const mime = MediaRecorder.isTypeSupported('video/mp4') ? 'video/mp4' : 'video/webm;codecs=vp8';
    const recorder = new MediaRecorder(stream, {{ mimeType: mime, videoBitsPerSecond: 1800000 }});

    const progInterval = setInterval(() => {{
        if (!isRecording) {{ clearInterval(progInterval); return; }}
        const dur = video.duration || 1;
        const pct = Math.min(99, Math.round((video.currentTime / dur) * 100));
        const remSec = Math.max(0, Math.round(dur - video.currentTime));
        pFill.style.width = pct + '%';
        pTitle.innerText = `🎬 Smart Sync Rendering — ${{pct}}%`;
        pDetail.innerText = `လက်ရှိအချိန်: ${{fmtTime(video.currentTime)}} / ${{fmtTime(dur)}} (Video Speed: ${{video.playbackRate.toFixed(2)}}x ဖြင့် ရုပ်+အသံ+စာတန်း ချိန်ညှိပေါင်းစပ်နေသည်...)`;
    }}, 250);

    recorder.ondataavailable = (e) => {{ if (e.data && e.data.size > 0) chunks.push(e.data); }};
    recorder.onstop = () => {{
        clearInterval(progInterval);
        isRecording = false;
        video.playbackRate = 1.0;
        pFill.style.width = '100%';
        const blob = new Blob(chunks, {{ type: mime }});
        const mb = (blob.size / (1024 * 1024)).toFixed(1);
        const url = URL.createObjectURL(blob);
        outVid.src = url;
        dlAnchor.href = url;
        dlAnchor.download = mime.includes('mp4') ? `RecapMM_SmartSync_${{mb}}MB.mp4` : `RecapMM_SmartSync_${{mb}}MB.webm`;
        dlAnchor.innerText = `📥 MP4 Download (${{mb}} MB)`;
        pTitle.innerText = `✅ Smart Sync Render အောင်မြင်စွာ ပြီးဆုံးပါပြီ!`;
        pDetail.innerText = `ဖိုင်ဆိုဒ်: ${{mb}} MB (အောက်တွင် တိုက်ရိုက် ကြည့်ရှု/Download ဆွဲနိုင်ပါပြီ)`;
        outWrap.style.display = 'block';
    }};

    video.currentTime = 0;
    lastPlayedSegIdx = -1;
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
