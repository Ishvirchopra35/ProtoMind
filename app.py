import json
import os
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from graph.graph import build_graph
from graph.state import PrototyperState

load_dotenv()
Path("outputs").mkdir(exist_ok=True)
Path("mock_specs").mkdir(exist_ok=True)

PIPELINE_STEPS = ["decompose", "cad", "firmware", "sourcing", "sim_verify"]
STEP_LABELS = {
    "decompose": "Decompose",
    "cad": "CAD",
    "firmware": "Firmware",
    "sourcing": "Sourcing",
    "sim_verify": "Simulation",
}
STEP_ICONS = {
    "decompose": "🧠",
    "cad": "📐",
    "firmware": "⚡",
    "sourcing": "🛒",
    "sim_verify": "🔬",
}

# ── Design tokens ────────────────────────────────────────────────────────────
BG        = "#080f1c"
SURFACE   = "#0d1a2e"
SURFACE2  = "#112240"
BORDER    = "#1a3456"
GOLD      = "#c9a843"
GOLD_LT   = "#e8c56e"
GOLD_DIM  = "rgba(201,168,67,0.12)"
TEXT      = "#e2e8f0"
TEXT_2    = "#8bacc8"
TEXT_3    = "#4a6080"
SUCCESS   = "#10b981"
ERROR     = "#ef4444"
WARNING   = "#f59e0b"

# ── Global CSS (injected once) ───────────────────────────────────────────────
GLOBAL_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

html, body, .stApp {{
    font-family: 'Inter', sans-serif !important;
    background-color: {BG} !important;
    color: {TEXT} !important;
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background-color: {SURFACE} !important;
    border-right: 1px solid {BORDER} !important;
}}
[data-testid="stSidebar"] * {{ color: {TEXT} !important; }}
[data-testid="stSidebar"] hr {{ border-color: {BORDER} !important; }}

/* ── Typography ── */
h1 {{ color: {GOLD} !important; font-size: 2rem !important; font-weight: 800 !important; letter-spacing: -0.5px; }}
h2 {{ color: {GOLD_LT} !important; font-size: 1.3rem !important; font-weight: 700 !important; }}
h3 {{ color: {TEXT} !important; font-size: 1.1rem !important; font-weight: 600 !important; }}
p, li, label, span {{ color: {TEXT} !important; }}
.stCaption > * {{ color: {TEXT_2} !important; font-size: 0.8rem !important; }}

/* ── Primary button ── */
.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {GOLD} 0%, {GOLD_LT} 100%) !important;
    color: {BG} !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    padding: 0.6rem 1.2rem !important;
    letter-spacing: 0.3px;
    box-shadow: 0 4px 20px rgba(201,168,67,0.3) !important;
    transition: all 0.2s ease !important;
}}
.stButton > button[kind="primary"]:hover {{
    box-shadow: 0 6px 28px rgba(201,168,67,0.5) !important;
    transform: translateY(-1px);
}}

/* ── Secondary / sidebar buttons ── */
.stButton > button:not([kind="primary"]) {{
    background-color: {SURFACE2} !important;
    color: {GOLD} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}}
.stButton > button:not([kind="primary"]):hover {{
    border-color: {GOLD} !important;
    background-color: {GOLD_DIM} !important;
}}

/* ── Download buttons ── */
.stDownloadButton > button {{
    background: linear-gradient(135deg, {GOLD} 0%, {GOLD_LT} 100%) !important;
    color: {BG} !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 12px rgba(201,168,67,0.25) !important;
    transition: all 0.2s ease !important;
}}
.stDownloadButton > button:hover {{
    box-shadow: 0 4px 20px rgba(201,168,67,0.45) !important;
    transform: translateY(-1px);
}}
.stButton > button:disabled {{
    background-color: {SURFACE2} !important;
    color: {TEXT_3} !important;
    border: 1px solid {BORDER} !important;
    box-shadow: none !important;
}}

/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea textarea,
[type="password"] {{
    background-color: {SURFACE2} !important;
    color: {TEXT} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    transition: border-color 0.2s !important;
}}
.stTextInput > div > div > input:focus,
.stTextArea textarea:focus {{
    border-color: {GOLD} !important;
    box-shadow: 0 0 0 3px rgba(201,168,67,0.15) !important;
    outline: none !important;
}}

/* ── Metrics ── */
[data-testid="stMetric"] {{
    background-color: {SURFACE} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 12px !important;
    padding: 16px 20px !important;
}}
[data-testid="stMetricLabel"] > div {{
    color: {TEXT_2} !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
}}
[data-testid="stMetricValue"] > div {{
    color: {GOLD} !important;
    font-size: 1.4rem !important;
    font-weight: 700 !important;
}}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {{
    background: transparent !important;
    border-bottom: 1px solid {BORDER} !important;
    gap: 0 !important;
}}
.stTabs [data-baseweb="tab"] {{
    background: transparent !important;
    color: {TEXT_2} !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    padding: 10px 20px !important;
    font-weight: 500 !important;
    font-family: 'Inter', sans-serif !important;
    transition: all 0.2s !important;
}}
.stTabs [data-baseweb="tab"]:hover {{
    color: {GOLD_LT} !important;
    background: {GOLD_DIM} !important;
}}
.stTabs [aria-selected="true"] {{
    color: {GOLD} !important;
    border-bottom: 2px solid {GOLD} !important;
    background: {GOLD_DIM} !important;
}}
.stTabs [data-baseweb="tab-panel"] {{
    background: {SURFACE} !important;
    border: 1px solid {BORDER} !important;
    border-top: none !important;
    border-radius: 0 0 12px 12px !important;
    padding: 24px !important;
}}

/* ── Expanders ── */
[data-testid="stExpander"] details {{
    background: {SURFACE2} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}}
[data-testid="stExpander"] summary {{
    color: {TEXT_2} !important;
    font-weight: 500 !important;
    padding: 12px 16px !important;
    font-family: 'Inter', sans-serif !important;
}}
[data-testid="stExpander"] summary:hover {{ color: {GOLD} !important; }}
[data-testid="stExpander"] summary svg {{ fill: {GOLD} !important; }}

/* ── Code blocks ── */
[data-testid="stCode"] pre, .stCode pre, pre {{
    background-color: #040a14 !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
    font-size: 0.82rem !important;
}}
code {{ color: {GOLD_LT} !important; }}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}}

/* ── Alerts ── */
[data-testid="stAlert"] {{
    border-radius: 10px !important;
    border-left-width: 3px !important;
    font-family: 'Inter', sans-serif !important;
}}

/* ── Divider ── */
hr {{ border: none !important; border-top: 1px solid {BORDER} !important; }}

/* ── Spinner ── */
[data-testid="stSpinner"] > div > div {{ border-top-color: {GOLD} !important; }}

/* ── Checkbox ── */
[data-testid="stCheckbox"] p {{ color: {TEXT} !important; }}

/* ── Scrollbar ── */
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: {BG}; }}
::-webkit-scrollbar-thumb {{ background: {BORDER}; border-radius: 4px; }}
::-webkit-scrollbar-thumb:hover {{ background: {GOLD}; }}

/* ── iframe wrappers (components.html) ── */
iframe {{ border: none !important; }}
</style>
"""


# ── HTML component helpers ───────────────────────────────────────────────────

def _base_html(body: str, extra_css: str = "", height: int = 100) -> None:
    """Render an HTML component with the shared design tokens baked in."""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
        font-family: 'Inter', sans-serif;
        background: transparent;
        color: {TEXT};
        font-size: 14px;
        line-height: 1.5;
        -webkit-font-smoothing: antialiased;
    }}
    {extra_css}
    </style>
    </head>
    <body>{body}</body>
    </html>
    """
    components.html(html, height=height, scrolling=False)


def render_pipeline_status(statuses: dict) -> None:
    STATUS_META = {
        "pending": ("○", TEXT_3,  SURFACE,  "Pending"),
        "running": ("◉", WARNING,  f"rgba(245,158,11,0.1)", "Running"),
        "done":    ("✓", SUCCESS,  f"rgba(16,185,129,0.1)", "Done"),
        "failed":  ("✕", ERROR,    f"rgba(239,68,68,0.1)",  "Failed"),
    }
    cards = ""
    for step in PIPELINE_STEPS:
        s = statuses.get(step, "pending")
        icon, color, bg, slabel = STATUS_META[s]
        pulse = "animation: pulse 1.2s ease-in-out infinite;" if s == "running" else ""
        cards += f"""
        <div class="card" style="border-color:{color}20; background:{bg};">
            <div class="icon" style="color:{color}; {pulse}">{icon}</div>
            <div class="info">
                <div class="name">{STEP_ICONS[step]} {STEP_LABELS[step]}</div>
                <div class="status" style="color:{color}">{slabel}</div>
            </div>
        </div>
        """
    css = f"""
    .grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; padding: 4px 0; }}
    .card {{
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 14px 12px;
        display: flex;
        align-items: center;
        gap: 10px;
        transition: border-color 0.3s;
    }}
    .icon {{ font-size: 18px; flex-shrink: 0; }}
    .name {{ font-size: 12px; font-weight: 600; color: {TEXT}; }}
    .status {{ font-size: 11px; font-weight: 500; margin-top: 2px; text-transform: uppercase; letter-spacing: 0.5px; }}
    @keyframes pulse {{ 0%,100% {{ opacity:1 }} 50% {{ opacity:0.4 }} }}
    """
    _base_html(f'<div class="grid">{cards}</div>', css, height=90)


def render_spec_card(title: str, items: list[tuple[str, str]], accent: str = GOLD) -> None:
    """Render a key-value spec card."""
    rows = "".join(
        f'<div class="row"><span class="key">{k}</span><span class="val">{v}</span></div>'
        for k, v in items
    )
    css = f"""
    .card {{
        background: {SURFACE2};
        border: 1px solid {BORDER};
        border-radius: 12px;
        overflow: hidden;
    }}
    .header {{
        background: linear-gradient(135deg, {SURFACE2}, {SURFACE});
        border-bottom: 1px solid {BORDER};
        padding: 12px 16px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: {accent};
    }}
    .body {{ padding: 4px 0; }}
    .row {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding: 9px 16px;
        border-bottom: 1px solid {BORDER}18;
        gap: 16px;
    }}
    .row:last-child {{ border-bottom: none; }}
    .key {{ font-size: 12px; color: {TEXT_2}; font-weight: 500; flex-shrink: 0; }}
    .val {{ font-size: 12px; color: {TEXT}; font-weight: 400; text-align: right; }}
    """
    height = 48 + len(items) * 38
    _base_html(f'<div class="card"><div class="header">{title}</div><div class="body">{rows}</div></div>', css, height)


def render_chip_list(title: str, items: list[str], color: str = GOLD) -> None:
    if not items:
        return
    chips = "".join(f'<span class="chip">{i}</span>' for i in items)
    css = f"""
    .wrap {{ margin-bottom: 4px; }}
    .label {{ font-size: 11px; font-weight: 700; text-transform: uppercase;
               letter-spacing: 0.8px; color: {TEXT_2}; margin-bottom: 8px; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .chip {{
        background: {GOLD_DIM};
        border: 1px solid {color}40;
        color: {color};
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 12px;
        font-weight: 500;
    }}
    """
    height = 32 + max(1, (len(items) // 4 + 1)) * 36
    _base_html(f'<div class="wrap"><div class="label">{title}</div><div class="chips">{chips}</div></div>', css, height)


def render_hero_metric_row(metrics: list[tuple[str, str, str]]) -> None:
    """metrics = list of (label, value, sublabel)"""
    cards = "".join(f"""
    <div class="card">
        <div class="label">{label}</div>
        <div class="value">{value}</div>
        <div class="sub">{sub}</div>
    </div>""" for label, value, sub in metrics)
    css = f"""
    .row {{ display: grid; grid-template-columns: repeat({len(metrics)}, 1fr); gap: 12px; }}
    .card {{
        background: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 18px 20px;
        position: relative;
        overflow: hidden;
    }}
    .card::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, {GOLD}, {GOLD_LT});
    }}
    .label {{ font-size: 11px; font-weight: 600; text-transform: uppercase;
               letter-spacing: 0.8px; color: {TEXT_2}; margin-bottom: 6px; }}
    .value {{ font-size: 1.6rem; font-weight: 800; color: {GOLD}; line-height: 1; }}
    .sub {{ font-size: 11px; color: {TEXT_3}; margin-top: 4px; }}
    """
    _base_html(f'<div class="row">{cards}</div>', css, height=110)


def render_section_header(title: str, subtitle: str = "") -> None:
    sub_html = f'<p class="sub">{subtitle}</p>' if subtitle else ""
    css = f"""
    .wrap {{ padding: 6px 0 2px; border-bottom: 1px solid {BORDER}; margin-bottom: 4px; }}
    h2 {{ font-size: 1.1rem; font-weight: 700; color: {GOLD}; }}
    .sub {{ font-size: 12px; color: {TEXT_2}; margin-top: 3px; }}
    """
    _base_html(f'<div class="wrap"><h2>{title}</h2>{sub_html}</div>', css, height=50 if subtitle else 38)


def render_sim_result(passed: bool, reason: str) -> None:
    color = SUCCESS if passed else ERROR
    icon  = "✓" if passed else "✕"
    label = "STABLE" if passed else "UNSTABLE"
    css = f"""
    .box {{
        background: {'rgba(16,185,129,0.08)' if passed else 'rgba(239,68,68,0.08)'};
        border: 1px solid {color}40;
        border-left: 4px solid {color};
        border-radius: 10px;
        padding: 16px 20px;
        display: flex;
        align-items: flex-start;
        gap: 14px;
    }}
    .icon {{ font-size: 22px; color: {color}; flex-shrink: 0; margin-top: 1px; }}
    .badge {{ font-size: 10px; font-weight: 800; text-transform: uppercase;
               letter-spacing: 1px; color: {color}; margin-bottom: 4px; }}
    .reason {{ font-size: 13px; color: {TEXT}; line-height: 1.5; }}
    """
    _base_html(f"""
    <div class="box">
        <div class="icon">{icon}</div>
        <div>
            <div class="badge">{label}</div>
            <div class="reason">{reason or "Passed all stability checks."}</div>
        </div>
    </div>""", css, height=90)


# ── State helpers ────────────────────────────────────────────────────────────

def build_initial_state(prompt: str) -> PrototyperState:
    return {
        "user_prompt": prompt,
        "decomposed_tasks": {},
        "cad_code": "",
        "stl_path": "",
        "firmware_code": "",
        "parts_list": [],
        "sim_passed": False,
        "sim_screenshot": "",
        "sim_failure_reason": "",
        "retry_count": 0,
        "cad_constraint": "",
        "current_step": "starting",
        "errors": [],
    }


def load_demo_state() -> PrototyperState:
    return json.loads(Path("mock_specs/turret_spec.json").read_text())


# ── Sidebar timeline (pure Streamlit) ────────────────────────────────────────

def render_sidebar_timeline(container) -> None:
    current   = st.session_state.get("current_step", "")
    completed = set(st.session_state.get("completed_steps", []))
    lines = []
    for key, label in [
        ("decompose", "Decompose prompt"),
        ("cad",       "Generate CAD"),
        ("firmware",  "Generate firmware"),
        ("sourcing",  "Source parts"),
        ("sim_verify","Simulation"),
    ]:
        if key in current:
            lines.append(f"🟡 **{label}**")
        elif key in completed:
            lines.append(f"🟢 {label}")
        else:
            lines.append(f"⚪ {label}")
    container.markdown("**Pipeline**\n\n" + "\n\n".join(lines))


# ── Page setup ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="Autonomous Prototyper", layout="wide", page_icon="⚙️")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"## ⚙️ Autonomous Prototyper")
    st.caption("Gemini-powered hardware pipeline")
    st.divider()

    api_key = st.text_input("Google AI API Key", type="password",
                             value=os.environ.get("GOOGLE_API_KEY", ""),
                             placeholder="AIza...")
    if api_key:
        os.environ["GOOGLE_API_KEY"] = api_key

    use_demo = st.checkbox("Use demo data (skip API calls)")
    st.divider()

    st.markdown("**Examples**")
    for example in [
        "Voice-controlled turret that tracks blue balls",
        "Pan-tilt camera mount with joystick",
        "3-DOF servo robotic arm",
    ]:
        if st.button(example, use_container_width=True):
            st.session_state["prompt"] = example

    st.divider()
    timeline_box = st.empty()
    render_sidebar_timeline(timeline_box)

# ── Main header ──────────────────────────────────────────────────────────────

_base_html(f"""
<div style="padding: 8px 0 16px;">
  <h1 style="font-size:2rem;font-weight:800;
             background: linear-gradient(135deg, {GOLD} 0%, {GOLD_LT} 60%, #fff 100%);
             -webkit-background-clip: text; -webkit-text-fill-color: transparent;
             margin-bottom: 6px; letter-spacing: -0.5px;">
    Autonomous Prototyper
  </h1>
  <p style="color:{TEXT_2}; font-size:14px; font-weight:400;">
    Describe a hardware project — Gemini 2.5 Flash generates CAD, firmware, parts list and simulation.
  </p>
</div>
""", height=90)

prompt = st.text_area(
    "Describe your hardware project",
    value=st.session_state.get("prompt", ""),
    height=90,
    placeholder="e.g. Build a voice-controlled turret that tracks blue balls…",
    label_visibility="collapsed",
)
run_btn = st.button("⚡  Run Pipeline", type="primary", use_container_width=True)

# ── Pipeline execution ───────────────────────────────────────────────────────

if run_btn and prompt:
    st.session_state.pop("pipeline_result", None)
    st.session_state["current_step"] = ""
    st.session_state["completed_steps"] = []
    render_sidebar_timeline(timeline_box)

    if not os.environ.get("GOOGLE_API_KEY") and not use_demo:
        st.error("Set your Google AI API key in the sidebar first, or enable demo mode.")
        st.stop()

    statuses = {step: "pending" for step in PIPELINE_STEPS}
    status_box = st.empty()
    with status_box:
        render_pipeline_status(statuses)

    elapsed = 0.0

    if use_demo and Path("mock_specs/turret_spec.json").exists():
        state = load_demo_state()
        statuses = {step: "done" for step in PIPELINE_STEPS}
        st.session_state["completed_steps"] = PIPELINE_STEPS.copy()
        st.session_state["current_step"] = "sim_verify"
        render_sidebar_timeline(timeline_box)
        with status_box:
            render_pipeline_status(statuses)
        st.success("Loaded demo data.")
        st.session_state["pipeline_result"] = state
        st.session_state["pipeline_elapsed"] = 0.0
    else:
        initial_state = build_initial_state(prompt)
        state = dict(initial_state)
        graph = build_graph()
        start_time = time.time()
        step_map = {
            "decompose": "decompose", "cad": "cad", "firmware": "firmware",
            "sourcing": "sourcing",   "sim_verify": "sim_verify", "increment_retry": "cad",
        }

        with st.spinner("Pipeline running…"):
            for step_output in graph.stream(initial_state):
                node_name  = list(step_output.keys())[0]
                node_update = list(step_output.values())[0]
                state.update(node_update)
                resolved = step_map.get(node_name)

                st.session_state["current_step"] = node_name
                done = list(st.session_state.get("completed_steps", []))
                if node_name not in done:
                    done.append(node_name)
                st.session_state["completed_steps"] = done
                render_sidebar_timeline(timeline_box)

                if node_name == "decompose":
                    statuses.update({"decompose":"done","cad":"running","firmware":"running","sourcing":"running"})
                    with status_box: render_pipeline_status(statuses)
                    continue

                if resolved:
                    if resolved == "sim_verify" and not node_update.get("sim_passed", True):
                        statuses[resolved] = "failed"
                    else:
                        statuses[resolved] = "done"

                if node_name in {"cad", "firmware", "sourcing"}:
                    pending = [s for s in ("cad","firmware","sourcing") if statuses[s] != "done"]
                    for s in pending: statuses[s] = "running"
                    if not pending: statuses["sim_verify"] = "running"

                if node_name == "increment_retry":
                    statuses["cad"] = "running"
                    statuses["sim_verify"] = "pending"

                with status_box: render_pipeline_status(statuses)

        elapsed = time.time() - start_time
        statuses = {
            s: ("failed" if s == "sim_verify" and not state.get("sim_passed", False) else "done")
            for s in PIPELINE_STEPS
        }
        with status_box: render_pipeline_status(statuses)
        render_sidebar_timeline(timeline_box)
        st.session_state["pipeline_result"]  = state
        st.session_state["pipeline_elapsed"] = elapsed

# ── Results ──────────────────────────────────────────────────────────────────

if "pipeline_result" not in st.session_state:
    st.stop()

state   = st.session_state["pipeline_result"]
elapsed = st.session_state.get("pipeline_elapsed", 0.0)
tasks   = state.get("decomposed_tasks", {})
geo     = tasks.get("geometry_spec", {})
fw_spec = tasks.get("firmware_spec", {})
parts   = state.get("parts_list", [])

st.divider()

# Summary metric row
for part in parts:
    if "price_cad" not in part:
        part["price_cad"] = part.pop("price_usd", 0.0)
total_cad = sum(p.get("price_cad", 0) * p.get("qty", 1) for p in parts)

render_hero_metric_row([
    ("Run time",     f"{elapsed:.0f}s",          "wall-clock"),
    ("Components",   str(len(parts)),             "in parts list"),
    ("Est. total",   f"${total_cad:.2f}",        "Canadian dollars"),
    ("Simulation",   "Stable" if state.get("sim_passed") else "Unstable", "tilt test"),
    ("Retries",      str(state.get("retry_count", 0)),  "CAD redesigns"),
])

st.divider()

# Tabs
tab_cad, tab_fw, tab_parts, tab_sim = st.tabs(
    ["  📐  CAD  ", "  ⚡  Firmware  ", "  🛒  Parts  ", "  🔬  Simulation  "]
)

# ── CAD tab ──────────────────────────────────────────────────────────────────
with tab_cad:
    if geo:
        render_section_header(tasks.get("goal", "CAD Design"),
                              "Geometry specification derived from your prompt")
        st.write("")

        dims = geo.get("base_dimensions_mm", {})
        spec_items = [
            ("Width",    f"{dims.get('width', '—')} mm"),
            ("Depth",    f"{dims.get('depth', '—')} mm"),
            ("Height",   f"{dims.get('height', '—')} mm"),
            ("Stability", geo.get("stability_requirement", "—")),
        ]
        if geo.get("description"):
            spec_items.insert(0, ("Description", geo["description"]))
        render_spec_card("Geometry Spec", spec_items)
        st.write("")

        col1, col2 = st.columns(2)
        with col1:
            render_chip_list("Moving Parts",    geo.get("moving_parts", []), GOLD)
        with col2:
            render_chip_list("Mounting Points", geo.get("mounting_points", []), GOLD_LT)

    stl_path  = state.get("stl_path", "") or "outputs/turret.stl"
    scad_path = "outputs/turret.scad"
    st.write("")
    if Path(stl_path).exists():
        st.success(f"STL compiled successfully → `{stl_path}`")
    elif Path(scad_path).exists():
        st.warning("OpenSCAD CLI not found — .scad source generated, STL skipped.")

    with st.expander("View OpenSCAD source code"):
        st.code(state.get("cad_code", "# not generated"), language="openscad")

# ── Firmware tab ─────────────────────────────────────────────────────────────
with tab_fw:
    if fw_spec:
        mcu = fw_spec.get("microcontroller", "Arduino")
        render_section_header(f"Firmware — {mcu}", "Auto-generated Arduino sketch")
        st.write("")

        spec_items = [("Microcontroller", mcu)]
        if fw_spec.get("control_logic"):
            spec_items.append(("Control logic", fw_spec["control_logic"]))
        render_spec_card("Firmware Spec", spec_items)
        st.write("")

        col1, col2 = st.columns(2)
        with col1:
            render_chip_list("Inputs",  fw_spec.get("inputs",  []), GOLD)
        with col2:
            render_chip_list("Outputs", fw_spec.get("outputs", []), GOLD_LT)

        libs = fw_spec.get("libraries_needed", [])
        if libs:
            st.write("")
            with st.expander("Required Arduino libraries"):
                st.code("\n".join(f"#include <{lib}.h>" for lib in libs), language="cpp")

    with st.expander("View full .ino source code"):
        st.code(state.get("firmware_code", "// not generated"), language="cpp")

# ── Parts tab ─────────────────────────────────────────────────────────────────
with tab_parts:
    if not parts:
        st.info("No parts list generated yet.")
    else:
        render_section_header("Parts List", f"Sourced from Amazon.ca · {len(parts)} components")
        st.write("")

        col_m, _ = st.columns([1, 3])
        col_m.metric("Estimated Total", f"${total_cad:.2f} CAD")
        st.write("")

        df = pd.DataFrame(parts)
        display_cols = {
            "name":      "Component",
            "model":     "Model",
            "price_cad": "Price (CAD)",
            "qty":       "Qty",
            "supplier":  "Supplier",
            "description": "Notes",
        }
        df = df[[c for c in display_cols if c in df.columns]].rename(columns=display_cols)
        if "Price (CAD)" in df.columns:
            df["Price (CAD)"] = df["Price (CAD)"].apply(lambda x: f"${float(x):.2f}")
        st.dataframe(df, use_container_width=True, hide_index=True)

# ── Simulation tab ────────────────────────────────────────────────────────────
with tab_sim:
    render_section_header("Physics Simulation", "Geometric stability check at 15°, 30°, 45° tilt")
    st.write("")
    render_sim_result(state.get("sim_passed", False), state.get("sim_failure_reason", ""))

    if state.get("retry_count", 0) > 0:
        st.write("")
        with st.expander(f"{state['retry_count']} redesign attempt(s)"):
            for err in state.get("errors", []):
                if err.startswith("Retry "):
                    st.markdown(f"- {err}")

    screenshot = state.get("sim_screenshot", "")
    if screenshot and Path(screenshot).exists():
        st.write("")
        st.image(screenshot, caption="Stability footprint — centre of mass vs. base footprint")
    else:
        st.write("")
        st.info("Run the pipeline with a live API key to generate the simulation diagram.")

# ── Downloads ─────────────────────────────────────────────────────────────────
st.divider()
render_section_header("Downloads", "All generated artifacts — click to save")
st.write("")

artifacts = [
    {"label": "OpenSCAD (.scad)",  "path": "outputs/turret.scad",       "file": "turret.scad",       "mime": "text/plain",        "binary": False},
    {"label": "STL model (.stl)",  "path": state.get("stl_path","") or "outputs/turret.stl",
                                                                          "file": "turret.stl",        "mime": "model/stl",         "binary": True},
    {"label": "Firmware (.ino)",   "path": "outputs/firmware.ino",       "file": "firmware.ino",      "mime": "text/plain",        "binary": False},
    {"label": "Parts list (.json)","path": "outputs/parts_list.json",    "file": "parts_list.json",   "mime": "application/json",  "binary": False},
    {"label": "Simulation (.png)", "path": "outputs/sim_screenshot.png", "file": "sim_screenshot.png","mime": "image/png",         "binary": True},
]

dl_cols = st.columns(len(artifacts))
for col, art in zip(dl_cols, artifacts):
    p = art["path"]
    if p and Path(p).exists():
        mode   = "rb" if art["binary"] else "r"
        kwargs = {} if art["binary"] else {"encoding": "utf-8"}
        with open(p, mode, **kwargs) as fh:
            data = fh.read()
        if isinstance(data, str):
            data = data.encode("utf-8")
        col.download_button(art["label"], data=data, file_name=art["file"],
                            mime=art["mime"], use_container_width=True)
    else:
        col.button(art["label"], disabled=True, use_container_width=True)

# ── Errors ────────────────────────────────────────────────────────────────────
if state.get("errors"):
    st.divider()
    with st.expander(f"⚠️  {len(state['errors'])} non-fatal error(s)"):
        for err in state["errors"]:
            st.markdown(f"- {err}")
