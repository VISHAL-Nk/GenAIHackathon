"""
Automated Viva Voce Question Generator & Evaluator
=====================================================
PS-E7 — GenAI Hackathon Project
"""

import os
import sys
import tempfile
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

from modules.pdf_extractor import extract_and_clean
from modules.question_gen import generate_questions, get_bloom_color, get_bloom_text_color
from modules.evaluator import evaluate_answer, calculate_grade, get_score_color, get_score_label
from modules.docx_generator import generate_score_sheet
from modules.dataset_loader import load_arc_examples

st.set_page_config(
    page_title="VivaAI — Intelligent Viva Examiner",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════════════
# PREMIUM CSS
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── Animated gradient background ── */
.stApp {
    font-family: 'Outfit', sans-serif !important;
    background: #050510;
    color: #E2E8F0;
}
.stApp::before {
    content: '';
    position: fixed;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    background:
        radial-gradient(ellipse 80% 60% at 10% 30%, rgba(124,58,237,0.08) 0%, transparent 70%),
        radial-gradient(ellipse 60% 80% at 90% 70%, rgba(6,182,212,0.06) 0%, transparent 70%),
        radial-gradient(ellipse 50% 50% at 50% 0%, rgba(236,72,153,0.04) 0%, transparent 60%);
    animation: bg-drift 20s ease-in-out infinite alternate;
}
@keyframes bg-drift {
    0% { opacity: 1; filter: hue-rotate(0deg); }
    100% { opacity: 0.8; filter: hue-rotate(30deg); }
}

.main .block-container {
    padding-top: 1rem;
    max-width: 1100px;
    position: relative;
    z-index: 1;
}

/* ── Hide all streamlit chrome ── */
#MainMenu, footer, .stDeployButton { visibility: hidden !important; display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; }

/* ── STEP PROGRESS BAR ── */
.step-progress {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    margin: 0 auto 2rem auto;
    max-width: 700px;
}
.step-node {
    width: 44px; height: 44px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem; font-weight: 800;
    flex-shrink: 0;
    transition: all 0.4s ease;
    position: relative;
}
.step-node.done {
    background: linear-gradient(135deg, #10B981, #34D399);
    color: #fff;
    box-shadow: 0 0 20px rgba(16,185,129,0.35);
}
.step-node.active {
    background: linear-gradient(135deg, #8B5CF6, #6D28D9);
    color: #fff;
    box-shadow: 0 0 25px rgba(139,92,246,0.5);
    animation: node-pulse 2s ease-in-out infinite;
}
.step-node.pending {
    background: rgba(255,255,255,0.05);
    color: #475569;
    border: 2px solid rgba(255,255,255,0.08);
}
@keyframes node-pulse {
    0%,100% { box-shadow: 0 0 20px rgba(139,92,246,0.4); transform: scale(1); }
    50% { box-shadow: 0 0 35px rgba(139,92,246,0.6); transform: scale(1.08); }
}
.step-line {
    flex: 1; height: 3px;
    background: rgba(255,255,255,0.06);
    border-radius: 2px;
    position: relative;
    overflow: hidden;
}
.step-line.done-line {
    background: linear-gradient(90deg, #10B981, #34D399);
    box-shadow: 0 0 8px rgba(16,185,129,0.3);
}
.step-line.active-line {
    background: linear-gradient(90deg, #10B981, #8B5CF6);
}
.step-label {
    position: absolute;
    bottom: -22px;
    left: 50%; transform: translateX(-50%);
    font-size: 0.55rem;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    white-space: nowrap;
    color: #64748B;
}
.step-node.active .step-label { color: #C4B5FD; }
.step-node.done .step-label { color: #6EE7B7; }

/* ── HERO SECTION ── */
.hero {
    text-align: center;
    padding: 3rem 2rem 2.5rem;
    margin-bottom: 2rem;
    background: linear-gradient(160deg, #0c0c20 0%, #1a103a 40%, #0d1b30 100%);
    border-radius: 24px;
    border: 1px solid rgba(139,92,246,0.12);
    position: relative;
    overflow: hidden;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05);
}
.hero::before {
    content: '';
    position: absolute;
    top: -100px; right: -100px;
    width: 350px; height: 350px;
    background: radial-gradient(circle, rgba(139,92,246,0.12) 0%, transparent 70%);
    border-radius: 50%;
    animation: float-orb 6s ease-in-out infinite;
}
.hero::after {
    content: '';
    position: absolute;
    bottom: -80px; left: -80px;
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(6,182,212,0.1) 0%, transparent 70%);
    border-radius: 50%;
    animation: float-orb 8s ease-in-out infinite reverse;
}
@keyframes float-orb {
    0%,100% { transform: translate(0,0) scale(1); }
    50% { transform: translate(20px,-15px) scale(1.1); }
}
.hero-icon {
    font-size: 3.5rem;
    display: block;
    margin-bottom: 0.75rem;
    position: relative; z-index: 1;
    filter: drop-shadow(0 0 20px rgba(139,92,246,0.4));
}
.hero h1 {
    font-size: 2.6rem;
    font-weight: 900;
    margin: 0;
    letter-spacing: -1.5px;
    background: linear-gradient(135deg, #E0E7FF 0%, #C4B5FD 40%, #67E8F9 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    position: relative; z-index: 1;
}
.hero p {
    font-size: 1.05rem;
    color: #94A3B8;
    margin: 0.6rem 0 0;
    font-weight: 400;
    position: relative; z-index: 1;
}

/* ── GLASS CARD ── */
.g-card {
    background: linear-gradient(135deg, rgba(15,15,35,0.85), rgba(10,10,25,0.95));
    backdrop-filter: blur(24px);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 18px;
    padding: 1.75rem;
    margin: 0.75rem 0;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04);
    transition: transform 0.35s cubic-bezier(.4,0,.2,1), box-shadow 0.35s ease, border-color 0.35s ease;
}
.g-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 16px 48px rgba(139,92,246,0.1), 0 8px 32px rgba(0,0,0,0.4);
    border-color: rgba(139,92,246,0.15);
}

/* ── FEATURE CARDS (upload page) ── */
.feature-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin: 1.5rem 0;
}
.feature-card {
    background: linear-gradient(135deg, rgba(15,15,35,0.8), rgba(10,10,25,0.9));
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 1.5rem 1.25rem;
    text-align: center;
    transition: all 0.35s ease;
    position: relative;
    overflow: hidden;
}
.feature-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 16px 16px 0 0;
}
.feature-card:nth-child(1)::before { background: linear-gradient(90deg, #8B5CF6, #A78BFA); }
.feature-card:nth-child(2)::before { background: linear-gradient(90deg, #06B6D4, #22D3EE); }
.feature-card:nth-child(3)::before { background: linear-gradient(90deg, #10B981, #34D399); }
.feature-card:nth-child(4)::before { background: linear-gradient(90deg, #F59E0B, #FBBF24); }
.feature-card:nth-child(5)::before { background: linear-gradient(90deg, #EC4899, #F472B6); }
.feature-card:nth-child(6)::before { background: linear-gradient(90deg, #EF4444, #F87171); }
.feature-card:hover {
    transform: translateY(-6px) scale(1.02);
    box-shadow: 0 12px 40px rgba(139,92,246,0.15);
    border-color: rgba(139,92,246,0.2);
}
.feature-card .f-icon { font-size: 2rem; margin-bottom: 0.6rem; display: block; }
.feature-card .f-title { font-weight: 700; font-size: 0.85rem; color: #E2E8F0; margin-bottom: 0.3rem; }
.feature-card .f-desc { font-size: 0.7rem; color: #64748B; line-height: 1.5; }

/* ── METRIC CARDS ── */
.stat-card {
    background: linear-gradient(135deg, rgba(15,15,35,0.9), rgba(10,10,25,0.95));
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 1.5rem 1rem;
    text-align: center;
    position: relative;
    overflow: hidden;
    transition: all 0.35s ease;
}
.stat-card:hover {
    transform: translateY(-5px) scale(1.03);
    box-shadow: 0 12px 40px rgba(0,0,0,0.4);
}
.stat-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 16px 16px 0 0;
}
.stat-card .s-icon { font-size: 1.5rem; margin-bottom: 0.4rem; display: block; }
.stat-card .s-value {
    font-size: 2.2rem;
    font-weight: 900;
    letter-spacing: -1px;
    margin: 0.2rem 0;
}
.stat-card .s-label {
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    font-weight: 700;
    color: #64748B;
}

/* color accents for stat cards */
.stat-violet::before { background: linear-gradient(90deg, #8B5CF6, #A78BFA); }
.stat-violet .s-value { color: #C4B5FD; }
.stat-cyan::before { background: linear-gradient(90deg, #06B6D4, #22D3EE); }
.stat-cyan .s-value { color: #67E8F9; }
.stat-emerald::before { background: linear-gradient(90deg, #10B981, #34D399); }
.stat-emerald .s-value { color: #6EE7B7; }
.stat-amber::before { background: linear-gradient(90deg, #F59E0B, #FBBF24); }
.stat-amber .s-value { color: #FCD34D; }
.stat-rose::before { background: linear-gradient(90deg, #F43F5E, #FB7185); }
.stat-rose .s-value { color: #FDA4AF; }
.stat-blue::before { background: linear-gradient(90deg, #3B82F6, #60A5FA); }
.stat-blue .s-value { color: #93C5FD; }

/* ── QUESTION CARD ── */
.q-card {
    background: linear-gradient(135deg, rgba(15,15,35,0.85), rgba(10,10,25,0.95));
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 18px;
    padding: 2rem;
    margin: 1.25rem 0;
    position: relative;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}
.q-card .q-number {
    position: absolute;
    top: 16px; right: 20px;
    font-size: 3rem;
    font-weight: 900;
    color: rgba(139,92,246,0.08);
    font-family: 'JetBrains Mono', monospace;
    line-height: 1;
}
.q-card .q-text {
    color: #F1F5F9;
    font-size: 1.15rem;
    font-weight: 500;
    line-height: 1.75;
    margin-top: 0.75rem;
}

/* ── BLOOM BADGES ── */
.bloom-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 16px;
    border-radius: 50px;
    font-size: 0.65rem;
    font-weight: 800;
    letter-spacing: 1px;
    text-transform: uppercase;
}
.bp-bl2 { background: linear-gradient(135deg, #1E40AF, #3B82F6); color: #DBEAFE; box-shadow: 0 4px 12px rgba(59,130,246,0.25); }
.bp-bl3 { background: linear-gradient(135deg, #065F46, #10B981); color: #D1FAE5; box-shadow: 0 4px 12px rgba(16,185,129,0.25); }
.bp-bl4 { background: linear-gradient(135deg, #78350F, #F59E0B); color: #FEF3C7; box-shadow: 0 4px 12px rgba(245,158,11,0.25); }
.bp-bl5 { background: linear-gradient(135deg, #7F1D1D, #EF4444); color: #FEE2E2; box-shadow: 0 4px 12px rgba(239,68,68,0.25); }

/* ── SCORE CHIP ── */
.sc {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 6px 18px; border-radius: 50px;
    font-weight: 800; font-size: 0.85rem;
}
.sc-hi { background: linear-gradient(135deg, #065F46, #10B981); color: #ECFDF5; box-shadow: 0 4px 15px rgba(16,185,129,0.3); }
.sc-md { background: linear-gradient(135deg, #78350F, #F59E0B); color: #FFFBEB; box-shadow: 0 4px 15px rgba(245,158,11,0.3); }
.sc-lo { background: linear-gradient(135deg, #7F1D1D, #EF4444); color: #FEF2F2; box-shadow: 0 4px 15px rgba(239,68,68,0.3); }

/* ── RESULT BANNERS ── */
.res-pass {
    background: linear-gradient(135deg, rgba(16,185,129,0.1), rgba(52,211,153,0.05));
    border: 1px solid rgba(16,185,129,0.25);
    border-radius: 20px;
    padding: 2.5rem; text-align: center; margin: 1.5rem 0;
    box-shadow: 0 0 80px rgba(16,185,129,0.08);
    position: relative; overflow: hidden;
}
.res-pass::before {
    content: '🎉'; position: absolute; font-size: 8rem; opacity: 0.05;
    top: -20px; right: -10px; transform: rotate(15deg);
}
.res-pass h1 { color: #34D399; font-size: 3.5rem; font-weight: 900; margin: 0; }
.res-pass p { color: #6EE7B7; font-size: 1.1rem; margin: 0.5rem 0 0; font-weight: 600; }

.res-fail {
    background: linear-gradient(135deg, rgba(244,63,94,0.1), rgba(251,113,133,0.05));
    border: 1px solid rgba(244,63,94,0.25);
    border-radius: 20px;
    padding: 2.5rem; text-align: center; margin: 1.5rem 0;
    box-shadow: 0 0 80px rgba(244,63,94,0.08);
    position: relative; overflow: hidden;
}
.res-fail::before {
    content: '📋'; position: absolute; font-size: 8rem; opacity: 0.05;
    top: -20px; right: -10px; transform: rotate(15deg);
}
.res-fail h1 { color: #FB7185; font-size: 3.5rem; font-weight: 900; margin: 0; }
.res-fail p { color: #FDA4AF; font-size: 1.1rem; margin: 0.5rem 0 0; font-weight: 600; }

/* ── BLOOM STAT CARDS (results) ── */
.bl-card {
    border-radius: 16px;
    padding: 1.3rem;
    text-align: center;
    border: 1px solid rgba(255,255,255,0.08);
    transition: all 0.35s ease;
    position: relative;
    overflow: hidden;
}
.bl-card:hover { transform: translateY(-4px) scale(1.03); }
.bl-card .bl-val { font-size: 2rem; font-weight: 900; letter-spacing: -0.5px; }
.bl-card .bl-lbl { font-size: 0.6rem; text-transform: uppercase; letter-spacing: 1.5px; opacity: 0.7; font-weight: 700; }
.bl-card .bl-pct { font-size: 0.8rem; font-weight: 700; margin-top: 0.25rem; }
.bl-card .bl-bar { height: 4px; border-radius: 2px; margin-top: 0.5rem; background: rgba(255,255,255,0.08); overflow: hidden; }
.bl-card .bl-fill { height: 100%; border-radius: 2px; transition: width 1s ease; }

/* ── SCORE FEEDBACK ── */
.sfb { border-radius: 14px; padding: 1.25rem; margin: 0.5rem 0; border: 1px solid rgba(255,255,255,0.06); }
.sfb-hi { background: linear-gradient(135deg, rgba(16,185,129,0.08), rgba(52,211,153,0.04)); border-color: rgba(16,185,129,0.2); }
.sfb-md { background: linear-gradient(135deg, rgba(245,158,11,0.08), rgba(251,191,36,0.04)); border-color: rgba(245,158,11,0.2); }
.sfb-lo { background: linear-gradient(135deg, rgba(244,63,94,0.08), rgba(251,113,133,0.04)); border-color: rgba(244,63,94,0.2); }

/* ── COUNTER PILL ── */
.counter-pill {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 8px 20px;
    background: rgba(139,92,246,0.08);
    border: 1px solid rgba(139,92,246,0.2);
    border-radius: 50px;
    font-size: 0.8rem; color: #C4B5FD; font-weight: 700;
}

/* ── SIDEBAR ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #06060f 0%, #0a0a1a 50%, #06060f 100%) !important;
    border-right: 1px solid rgba(139,92,246,0.08);
}
section[data-testid="stSidebar"] .stMarkdown { color: #CBD5E1; }

/* ── FORM INPUTS ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: rgba(10,10,25,0.8) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 12px !important;
    color: #E2E8F0 !important;
    font-family: 'Outfit', sans-serif !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: rgba(139,92,246,0.5) !important;
    box-shadow: 0 0 0 3px rgba(139,92,246,0.1), 0 0 20px rgba(139,92,246,0.08) !important;
}

/* ── BUTTONS ── */
.stButton > button {
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-family: 'Outfit', sans-serif !important;
    letter-spacing: 0.3px;
    transition: all 0.3s cubic-bezier(.4,0,.2,1) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 30px rgba(139,92,246,0.2) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #7C3AED, #8B5CF6, #6D28D9) !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 4px 20px rgba(124,58,237,0.3) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 8px 35px rgba(124,58,237,0.5) !important;
}

/* ── DOWNLOAD ── */
.stDownloadButton > button {
    background: linear-gradient(135deg, #7C3AED, #6D28D9) !important;
    color: white !important; border: none !important;
    border-radius: 12px !important; font-weight: 800 !important;
    box-shadow: 0 4px 20px rgba(124,58,237,0.3) !important;
}

/* ── FILE UPLOADER ── */
.stFileUploader > div {
    background: rgba(10,10,25,0.5) !important;
    border: 2px dashed rgba(139,92,246,0.2) !important;
    border-radius: 16px !important;
}
.stFileUploader > div:hover { border-color: rgba(139,92,246,0.5) !important; }

/* ── EXPANDER ── */
details {
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 14px !important;
    background: rgba(10,10,25,0.6) !important;
}

/* ── PROGRESS BAR ── */
.stProgress > div > div { background: linear-gradient(90deg, #7C3AED, #06B6D4) !important; height: 8px !important; border-radius: 8px; }
.stProgress > div { background: rgba(255,255,255,0.04) !important; border-radius: 8px; }

/* ── DIVIDER ── */
.gradient-divider {
    height: 1px; margin: 2rem 0;
    background: linear-gradient(90deg, transparent, rgba(139,92,246,0.2), rgba(6,182,212,0.2), transparent);
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# Session State
# ═══════════════════════════════════════════════════════════════════════════
def init_session_state():
    defaults = {
        "stage": "upload", "pdf_text": None, "pdf_filename": None,
        "student_name": "", "student_id": "", "subject": "", "department": "",
        "faculty_name": "", "report_title": "", "questions": None,
        "eval_results": [], "student_answers": [], "current_question": 0,
        "docx_path": None, "generation_error": None, "evaluation_error": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════
STAGE_LIST = ["upload", "info", "questions", "evaluation", "results"]
STAGE_ICONS = ["📄", "📝", "❓", "✍️", "📊"]
STAGE_NAMES = ["Upload", "Info", "Review", "Answer", "Results"]

def _step_progress():
    """Render horizontal step progress bar at top of every page."""
    cur = STAGE_LIST.index(st.session_state["stage"]) if st.session_state["stage"] in STAGE_LIST else 0
    html = '<div class="step-progress">'
    for i, (icon, name) in enumerate(zip(STAGE_ICONS, STAGE_NAMES)):
        if i < cur:
            cls = "done"
        elif i == cur:
            cls = "active"
        else:
            cls = "pending"
        html += f'<div class="step-node {cls}">{icon}<span class="step-label">{name}</span></div>'
        if i < len(STAGE_LIST) - 1:
            if i < cur:
                lcls = "done-line"
            elif i == cur:
                lcls = "active-line"
            else:
                lcls = ""
            html += f'<div class="step-line {lcls}"></div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)
    st.markdown('<div style="height:1rem;"></div>', unsafe_allow_html=True)


def _bloom_pill(bl, label):
    return f'<span class="bloom-pill bp-{bl.lower()}">{"📘📗📙📕"[["BL2","BL3","BL4","BL5"].index(bl)] if bl in ["BL2","BL3","BL4","BL5"] else "📄"} {bl} · {label}</span>'

def _bloom_icon(bl):
    return {"BL2":"📘","BL3":"📗","BL4":"📙","BL5":"📕"}.get(bl,"📄")

def _sc(score):
    lbl = get_score_label(score)
    cls = "sc-hi" if score >= 4 else ("sc-md" if score >= 2 else "sc-lo")
    return f'<span class="sc {cls}">{score}/5 · {lbl}</span>'

def _sfb_cls(score):
    return "sfb sfb-hi" if score >= 4 else ("sfb sfb-md" if score >= 2 else "sfb sfb-lo")


# ═══════════════════════════════════════════════════════════════════════════
# Sidebar
# ═══════════════════════════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:1.5rem 0 0.75rem;">
            <div style="font-size:3.5rem;filter:drop-shadow(0 0 15px rgba(139,92,246,0.5));">🎓</div>
            <h2 style="margin:0.3rem 0 0;font-weight:900;font-size:1.5rem;
                       background:linear-gradient(135deg,#C4B5FD,#67E8F9);
                       -webkit-background-clip:text;-webkit-text-fill-color:transparent;">VivaAI</h2>
            <p style="color:#475569;font-size:0.6rem;letter-spacing:3px;text-transform:uppercase;margin:4px 0 0;">
                Intelligent Examiner</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)

        cur_idx = STAGE_LIST.index(st.session_state["stage"]) if st.session_state["stage"] in STAGE_LIST else 0
        descs = ["Upload report", "Your details", "Review questions", "Type answers", "Scores & DOCX"]
        for i, (icon, name, desc) in enumerate(zip(STAGE_ICONS, STAGE_NAMES, descs)):
            if i < cur_idx:
                bg = "rgba(16,185,129,0.08)"; bc = "rgba(16,185,129,0.15)"; si = "✅"
            elif i == cur_idx:
                bg = "rgba(139,92,246,0.1)"; bc = "rgba(139,92,246,0.25)"; si = "▶"
            else:
                bg = "rgba(255,255,255,0.02)"; bc = "rgba(255,255,255,0.04)"; si = "○"
            anim = 'animation:node-pulse 2.5s ease-in-out infinite;' if i == cur_idx else ''
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:12px;padding:10px 14px;margin:3px 0;
                        border-radius:12px;background:{bg};border:1px solid {bc};{anim}">
                <span style="font-size:1.1rem;">{icon}</span>
                <div>
                    <div style="font-size:0.78rem;font-weight:700;color:#CBD5E1;">{si} {name}</div>
                    <div style="font-size:0.6rem;color:#475569;margin-top:1px;">{desc}</div>
                </div>
            </div>""", unsafe_allow_html=True)

        st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)

        if st.button("🔄 Start Over", use_container_width=True, type="secondary"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            init_session_state()
            st.rerun()

        st.markdown("""
        <div style="padding:1rem 0 0.5rem;color:#334155;font-size:0.6rem;">
            <div style="display:flex;flex-direction:column;gap:5px;">
                <span>🤖 Groq · Llama 3.3 70B</span>
                <span>📚 Bloom's Taxonomy</span>
                <span>📊 ARC AI2 Few-Shot</span>
                <span>📄 DOCX Score Sheets</span>
            </div>
            <div style="margin-top:1rem;padding-top:0.7rem;border-top:1px solid rgba(255,255,255,0.03);
                        text-align:center;color:#1E293B;font-size:0.55rem;letter-spacing:2px;">
                PS-E7 · GENAI HACKATHON
            </div>
        </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# Stage 1: Upload
# ═══════════════════════════════════════════════════════════════════════════
def render_upload_stage():
    _step_progress()

    st.markdown("""
    <div class="hero">
        <span class="hero-icon">📄</span>
        <h1>Upload Project Report</h1>
        <p>Upload your PDF project report or lab record to begin the AI-powered viva examination</p>
    </div>
    """, unsafe_allow_html=True)

    # Feature cards
    st.markdown("""
    <div class="feature-grid">
        <div class="feature-card">
            <span class="f-icon">🤖</span>
            <div class="f-title">AI Question Generation</div>
            <div class="f-desc">10 Bloom's-mapped questions generated from your report using Llama 3.3 70B</div>
        </div>
        <div class="feature-card">
            <span class="f-icon">📊</span>
            <div class="f-title">Smart Evaluation</div>
            <div class="f-desc">Each answer scored 0-5 with detailed justification by the AI examiner</div>
        </div>
        <div class="feature-card">
            <span class="f-icon">📄</span>
            <div class="f-title">DOCX Score Sheet</div>
            <div class="f-desc">Professional color-coded score sheet with Bloom's breakdown for records</div>
        </div>
        <div class="feature-card">
            <span class="f-icon">📚</span>
            <div class="f-title">Bloom's Taxonomy</div>
            <div class="f-desc">Questions mapped to BL2-BL5: Understand, Apply, Analyze, Evaluate</div>
        </div>
        <div class="feature-card">
            <span class="f-icon">⚡</span>
            <div class="f-title">Few-Shot Prompting</div>
            <div class="f-desc">ARC AI2 dataset examples improve question quality via few-shot injection</div>
        </div>
        <div class="feature-card">
            <span class="f-icon">🎯</span>
            <div class="f-title">Fair Grading</div>
            <div class="f-desc">O to F scale with consistent AI scoring at low temperature for fairness</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"], key="pdf_uploader",
                                         help="Upload your project report or lab record as a PDF file")
        if uploaded_file is not None:
            with st.spinner("📖 Extracting text from PDF..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    result = extract_and_clean(tmp_path)
                    st.session_state["pdf_text"] = result
                    st.session_state["pdf_filename"] = uploaded_file.name
                    os.unlink(tmp_path)
                    st.success("✅ PDF processed successfully!")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    return

            if st.session_state["pdf_text"]:
                r = st.session_state["pdf_text"]
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(f"""<div class="stat-card stat-violet">
                        <span class="s-icon">📑</span>
                        <div class="s-value">{r['page_count']}</div>
                        <div class="s-label">Pages</div></div>""", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"""<div class="stat-card stat-cyan">
                        <span class="s-icon">📝</span>
                        <div class="s-value">{r['word_count']:,}</div>
                        <div class="s-label">Words</div></div>""", unsafe_allow_html=True)
                with c3:
                    st.markdown(f"""<div class="stat-card stat-emerald">
                        <span class="s-icon">🔤</span>
                        <div class="s-value">{r['char_count']:,}</div>
                        <div class="s-label">Characters</div></div>""", unsafe_allow_html=True)

                with st.expander("📖 Preview Extracted Text", expanded=False):
                    st.text(r["cleaned_text"][:2000] + ("..." if len(r["cleaned_text"]) > 2000 else ""))

                st.markdown("")
                if st.button("▶️  Proceed to Student Info", use_container_width=True, type="primary"):
                    st.session_state["stage"] = "info"
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# Stage 2: Info
# ═══════════════════════════════════════════════════════════════════════════
def render_info_stage():
    _step_progress()
    st.markdown("""
    <div class="hero">
        <span class="hero-icon">📝</span>
        <h1>Student Information</h1>
        <p>Fill in your details for the examination record</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("student_info_form"):
            st.markdown("##### 👤 Personal Details")
            c1, c2 = st.columns(2)
            with c1:
                student_name = st.text_input("Student Name *", value=st.session_state.get("student_name", ""),
                                             placeholder="Enter your full name")
            with c2:
                student_id = st.text_input("Student ID *", value=st.session_state.get("student_id", ""),
                                           placeholder="e.g., 2024CS001")
            st.markdown("##### 🏫 Academic Details")
            c3, c4 = st.columns(2)
            with c3:
                subject = st.text_input("Subject *", value=st.session_state.get("subject", ""),
                                        placeholder="e.g., Machine Learning")
            with c4:
                department = st.text_input("Department *", value=st.session_state.get("department", ""),
                                           placeholder="e.g., Computer Science")
            c5, c6 = st.columns(2)
            with c5:
                faculty_name = st.text_input("Faculty Name *", value=st.session_state.get("faculty_name", ""),
                                             placeholder="e.g., Dr. Jane Smith")
            with c6:
                report_title = st.text_input("Report Title *", value=st.session_state.get("report_title", ""),
                                             placeholder="Title of your project report")
            submitted = st.form_submit_button("🚀 Generate Viva Questions", use_container_width=True, type="primary")

            if submitted:
                if not all([student_name, student_id, subject, department, faculty_name, report_title]):
                    st.error("❌ Please fill in all required fields.")
                    return
                st.session_state.update({
                    "student_name": student_name, "student_id": student_id, "subject": subject,
                    "department": department, "faculty_name": faculty_name, "report_title": report_title,
                })

        if submitted and all([student_name, student_id, subject, department, faculty_name, report_title]):
            with st.spinner("🤖 AI is generating your viva questions... This may take 15-30 seconds."):
                try:
                    questions = generate_questions(
                        document_text=st.session_state["pdf_text"]["cleaned_text"], subject=subject)
                    st.session_state["questions"] = questions
                    st.session_state["student_answers"] = [""] * len(questions)
                    st.session_state["eval_results"] = [None] * len(questions)
                    st.session_state["stage"] = "questions"
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Question generation failed: {str(e)}")
                    st.info("💡 Tip: Check your GROQ_API_KEY in the .env file and try again.")


# ═══════════════════════════════════════════════════════════════════════════
# Stage 3: Questions Review
# ═══════════════════════════════════════════════════════════════════════════
def render_questions_stage():
    _step_progress()
    st.markdown("""
    <div class="hero">
        <span class="hero-icon">❓</span>
        <h1>Generated Viva Questions</h1>
        <p>Review the 10 AI-generated questions mapped to Bloom's Taxonomy levels</p>
    </div>
    """, unsafe_allow_html=True)

    questions = st.session_state["questions"]
    if not questions:
        st.error("No questions available.")
        return

    bl_counts = {"BL2": 0, "BL3": 0, "BL4": 0, "BL5": 0}
    for q in questions:
        bl_counts[q.get("bloom_level", "BL2")] += 1

    bl_meta = [
        ("BL2", "Understand", bl_counts["BL2"], "stat-blue"),
        ("BL3", "Apply", bl_counts["BL3"], "stat-emerald"),
        ("BL4", "Analyze", bl_counts["BL4"], "stat-amber"),
        ("BL5", "Evaluate", bl_counts["BL5"], "stat-rose"),
    ]
    cols = st.columns(4)
    for i, (bl, lbl, cnt, css) in enumerate(bl_meta):
        with cols[i]:
            st.markdown(f"""<div class="stat-card {css}">
                <span class="s-icon">{_bloom_icon(bl)}</span>
                <div class="s-value">{cnt}</div>
                <div class="s-label">{bl} · {lbl}</div></div>""", unsafe_allow_html=True)

    st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)

    # Render all questions as styled cards (not expanders)
    _bl_border = {"BL2": "#3B82F6", "BL3": "#10B981", "BL4": "#F59E0B", "BL5": "#EF4444"}
    for q in questions:
        bl = q.get("bloom_level", "BL2")
        bl_label = q.get("bloom_label", "Understand")
        border_color = _bl_border.get(bl, "#8B5CF6")
        pill = _bloom_pill(bl, bl_label)

        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, rgba(15,15,35,0.85), rgba(10,10,25,0.95));
            border: 1px solid rgba(255,255,255,0.06);
            border-left: 4px solid {border_color};
            border-radius: 14px;
            padding: 1.25rem 1.5rem;
            margin: 0.6rem 0;
            display: flex;
            align-items: flex-start;
            gap: 1rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 16px rgba(0,0,0,0.3);
        " onmouseover="this.style.transform='translateX(6px)';this.style.boxShadow='0 6px 24px rgba(139,92,246,0.12)';"
           onmouseout="this.style.transform='translateX(0)';this.style.boxShadow='0 4px 16px rgba(0,0,0,0.3)';">
            <div style="flex-shrink:0;min-width:36px;height:36px;border-radius:10px;
                        background:{border_color}18;display:flex;align-items:center;justify-content:center;
                        font-weight:900;font-size:0.85rem;color:{border_color};
                        font-family:'JetBrains Mono',monospace;border:1px solid {border_color}30;">
                {q['q_number']:02d}
            </div>
            <div style="flex:1;">
                <div style="margin-bottom:0.5rem;">
                    {pill}
                </div>
                <div style="color:#E2E8F0;font-size:0.95rem;line-height:1.7;font-weight:400;">
                    {q['question']}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)

    # Single start button (no regenerate — student dashboard)
    if st.button("✍️  Start Answering", use_container_width=True, type="primary"):
        st.session_state["current_question"] = 0
        st.session_state["stage"] = "evaluation"
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# Stage 4: Answer Collection
# ═══════════════════════════════════════════════════════════════════════════
def render_evaluation_stage():
    _step_progress()

    questions = st.session_state["questions"]
    cur = st.session_state["current_question"]
    total = len(questions)

    if cur >= total:
        st.session_state["stage"] = "results"
        st.rerun()
        return

    cq = questions[cur]
    bl = cq.get("bloom_level", "BL2")
    bl_label = cq.get("bloom_label", "Understand")
    text_color = get_bloom_text_color(bl)
    pill = _bloom_pill(bl, bl_label)

    st.markdown(f"""
    <div class="hero">
        <span class="hero-icon">✍️</span>
        <h1>Question {cur + 1} of {total}</h1>
        <p>Answer each question to the best of your ability</p>
    </div>
    """, unsafe_allow_html=True)

    st.progress(cur / total, text=f"Progress: {cur}/{total} answered")

    st.markdown(f"""
    <div class="q-card" style="border-left: 4px solid {text_color};">
        <span class="q-number">{cur + 1:02d}</span>
        <div style="margin-bottom: 0.5rem;">{pill}</div>
        <div class="q-text">{cq['question']}</div>
    </div>
    """, unsafe_allow_html=True)

    existing = st.session_state["student_answers"][cur] if cur < len(st.session_state["student_answers"]) else ""
    answer = st.text_area("Your Answer", value=existing, height=150,
                          placeholder="Type your answer here... Be as detailed as possible.",
                          key=f"answer_{cur}")

    st.markdown("")
    c1, c2, c3 = st.columns(3)
    with c1:
        if cur > 0 and st.button("⬅️ Previous", use_container_width=True):
            st.session_state["student_answers"][cur] = answer
            st.session_state["current_question"] = cur - 1
            st.rerun()
    with c2:
        if st.button("⏭️ Skip", use_container_width=True, type="secondary"):
            st.session_state["student_answers"][cur] = ""
            st.session_state["current_question"] = cur + 1 if cur + 1 < total else total
            if cur + 1 >= total:
                st.session_state["stage"] = "results"
            st.rerun()
    with c3:
        lbl = "💾 Save & Next" if cur < total - 1 else "🏁 Submit All"
        if st.button(lbl, use_container_width=True, type="primary"):
            st.session_state["student_answers"][cur] = answer
            if cur + 1 >= total:
                st.session_state["stage"] = "results"
            else:
                st.session_state["current_question"] = cur + 1
            st.rerun()

    answered = sum(1 for a in st.session_state["student_answers"] if a.strip())
    st.markdown(f'<div style="text-align:center;margin-top:1.5rem;"><span class="counter-pill">📝 {answered} of {total} answered</span></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# Stage 5: Results
# ═══════════════════════════════════════════════════════════════════════════
def render_results_stage():
    _step_progress()

    questions = st.session_state["questions"]
    eval_results = st.session_state["eval_results"]
    answers = st.session_state["student_answers"]

    # Batch evaluation
    unevaluated = [i for i in range(len(questions)) if i < len(eval_results) and eval_results[i] is None]
    if unevaluated:
        st.markdown("""
        <div class="hero">
            <span class="hero-icon">🤖</span>
            <h1>Evaluating Your Answers</h1>
            <p>AI is scoring all your responses — please wait</p>
        </div>
        """, unsafe_allow_html=True)

        pbar = st.progress(0, text="Starting evaluation...")
        stxt = st.empty()
        for step, idx in enumerate(unevaluated):
            q = questions[idx]
            pbar.progress((step + 1) / len(unevaluated), text=f"Evaluating Q{idx + 1} of {len(questions)}...")
            stxt.markdown(f"⏳ *Scoring: {q['question'][:50]}...*")
            try:
                res = evaluate_answer(question=q["question"], bloom_level=q.get("bloom_level", "BL2"),
                                      student_answer=answers[idx] if idx < len(answers) else "",
                                      document_context=st.session_state["pdf_text"]["cleaned_text"])
                st.session_state["eval_results"][idx] = res
            except Exception as e:
                st.session_state["eval_results"][idx] = {"score": 0, "justification": f"Error: {str(e)[:100]}", "correct_answer_hint": "N/A"}
        pbar.progress(1.0, text="✅ All answers evaluated!")
        stxt.empty()
        eval_results = st.session_state["eval_results"]

    total_score = sum((r.get("score", 0) if r else 0) for r in eval_results)
    grade_info = calculate_grade(total_score)

    st.markdown("""
    <div class="hero">
        <span class="hero-icon">📊</span>
        <h1>Examination Results</h1>
        <p>Your viva voce examination is complete</p>
    </div>
    """, unsafe_allow_html=True)

    # Banner
    if grade_info["passed"]:
        st.markdown(f"""<div class="res-pass">
            <h1>🎉 PASS</h1>
            <p>Congratulations, {st.session_state['student_name']}!</p>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class="res-fail">
            <h1>📋 FAIL</h1>
            <p>{st.session_state['student_name']}, further preparation needed.</p>
        </div>""", unsafe_allow_html=True)

    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""<div class="stat-card stat-violet">
            <span class="s-icon">🏆</span>
            <div class="s-value">{total_score}/50</div>
            <div class="s-label">Total Score</div></div>""", unsafe_allow_html=True)
    with m2:
        st.markdown(f"""<div class="stat-card stat-cyan">
            <span class="s-icon">📈</span>
            <div class="s-value">{grade_info['percentage']}%</div>
            <div class="s-label">Percentage</div></div>""", unsafe_allow_html=True)
    with m3:
        st.markdown(f"""<div class="stat-card stat-amber">
            <span class="s-icon">🎖️</span>
            <div class="s-value">{grade_info['grade'].split('(')[0].strip()}</div>
            <div class="s-label">Grade</div></div>""", unsafe_allow_html=True)
    with m4:
        if grade_info["passed"]:
            st.markdown(f"""<div class="stat-card stat-emerald">
                <span class="s-icon">✅</span>
                <div class="s-value">PASS</div>
                <div class="s-label">Result</div></div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class="stat-card stat-rose">
                <span class="s-icon">❌</span>
                <div class="s-value">FAIL</div>
                <div class="s-label">Result</div></div>""", unsafe_allow_html=True)

    st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)

    # Bloom breakdown with progress bars
    st.markdown("### 📚 Bloom's Taxonomy Breakdown")
    bloom_scores = {"BL2": 0, "BL3": 0, "BL4": 0, "BL5": 0}
    bloom_max = {"BL2": 15, "BL3": 15, "BL4": 10, "BL5": 10}
    for idx, q in enumerate(questions):
        bl = q.get("bloom_level", "BL2")
        if idx < len(eval_results) and eval_results[idx]:
            bloom_scores[bl] += eval_results[idx].get("score", 0)

    bl_info = [
        ("BL2", "Understand", "#3B82F6", "rgba(59,130,246,0.1)"),
        ("BL3", "Apply", "#10B981", "rgba(16,185,129,0.1)"),
        ("BL4", "Analyze", "#F59E0B", "rgba(245,158,11,0.1)"),
        ("BL5", "Evaluate", "#F43F5E", "rgba(244,63,94,0.1)"),
    ]
    bl_cols = st.columns(4)
    for i, (bl, lbl, clr, bg) in enumerate(bl_info):
        s, mx = bloom_scores[bl], bloom_max[bl]
        pct = round((s / mx) * 100) if mx else 0
        with bl_cols[i]:
            st.markdown(f"""<div class="bl-card" style="background:{bg};border-color:{clr}30;">
                <div class="bl-lbl" style="color:{clr};">{_bloom_icon(bl)} {bl} · {lbl}</div>
                <div class="bl-val" style="color:{clr};">{s}/{mx}</div>
                <div class="bl-pct" style="color:{clr};">{pct}%</div>
                <div class="bl-bar"><div class="bl-fill" style="width:{pct}%;background:{clr};"></div></div>
            </div>""", unsafe_allow_html=True)

    # Bar chart
    st.markdown("")
    import pandas as pd
    bloom_labels = {"BL2": "Understand", "BL3": "Apply", "BL4": "Analyze", "BL5": "Evaluate"}
    df = pd.DataFrame({"Bloom Level": list(bloom_labels.values()),
                        "Score": [bloom_scores[bl] for bl in bloom_labels]})
    st.bar_chart(df.set_index("Bloom Level")["Score"], color="#8B5CF6")

    st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)

    # Question-wise
    st.markdown("### 📋 Question-wise Results")
    for idx, q in enumerate(questions):
        bl = q.get("bloom_level", "BL2")
        pill = _bloom_pill(bl, q.get("bloom_label", "N/A"))
        ev = eval_results[idx] if idx < len(eval_results) and eval_results[idx] else {"score": 0, "justification": "N/A", "correct_answer_hint": "N/A"}
        score = ev.get("score", 0)
        chip = _sc(score)
        ans = answers[idx] if idx < len(answers) else ""
        fb = _sfb_cls(score)

        with st.expander(f"Q{q['q_number']}  ·  {q['question'][:55]}...  ·  {score}/5", expanded=False):
            st.markdown(f"{pill}  {chip}", unsafe_allow_html=True)
            st.markdown(f"**Question:** {q['question']}")
            st.markdown(f"**Your Answer:** {ans if ans else '*No answer provided*'}")
            st.markdown(f"""<div class="{fb}">
                <strong style="color:#E2E8F0;">💬 Justification:</strong>
                <span style="color:#CBD5E1;"> {ev.get('justification', 'N/A')}</span>
            </div>""", unsafe_allow_html=True)
            if ev.get("correct_answer_hint"):
                st.info(f"📝 **Model Answer Hint:** {ev['correct_answer_hint']}")

    st.markdown('<div class="gradient-divider"></div>', unsafe_allow_html=True)

    # DOCX
    st.markdown("### 📄 Download Score Sheet")
    if st.button("📥  Generate & Download DOCX Score Sheet", use_container_width=True, type="primary"):
        with st.spinner("📄 Generating professional score sheet..."):
            try:
                docx_results = []
                for idx, ev in enumerate(eval_results):
                    if ev is None:
                        ev = {"score": 0, "justification": "N/A", "correct_answer_hint": "N/A"}
                    c = dict(ev)
                    c["student_answer"] = answers[idx] if idx < len(answers) else ""
                    docx_results.append(c)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                fn = f"scoresheet_{st.session_state['student_id'].replace(' ','_')}_{ts}.docx"
                op = os.path.join(_PROJECT_ROOT, "outputs", "score_sheets", fn)
                gp = generate_score_sheet(
                    student_name=st.session_state["student_name"], student_id=st.session_state["student_id"],
                    subject=st.session_state["subject"], department=st.session_state["department"],
                    report_title=st.session_state["report_title"], faculty_name=st.session_state["faculty_name"],
                    questions_data=questions, eval_results=docx_results, output_path=op)
                st.session_state["docx_path"] = gp
                st.success("✅ Score sheet generated!")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    if st.session_state.get("docx_path") and os.path.isfile(st.session_state["docx_path"]):
        with open(st.session_state["docx_path"], "rb") as f:
            st.download_button("⬇️  Download Score Sheet (.docx)", data=f.read(),
                               file_name=os.path.basename(st.session_state["docx_path"]),
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# Main Router
# ═══════════════════════════════════════════════════════════════════════════
def main():
    render_sidebar()
    stage = st.session_state["stage"]
    {"upload": render_upload_stage, "info": render_info_stage, "questions": render_questions_stage,
     "evaluation": render_evaluation_stage, "results": render_results_stage}.get(stage, render_upload_stage)()

if __name__ == "__main__":
    main()
