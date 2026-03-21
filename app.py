import json
import os
import time
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from graph.graph import build_graph
from graph.state import PrototyperState

load_dotenv()
Path("outputs").mkdir(exist_ok=True)
Path("mock_specs").mkdir(exist_ok=True)

PIPELINE_STEPS = ["decompose", "cad", "firmware", "sourcing", "sim_verify"]
STEP_LABELS = {
    "decompose": "Prompt Breakdown",
    "cad": "CAD Generation",
    "firmware": "Firmware",
    "sourcing": "Parts Sourcing",
    "sim_verify": "Simulation",
}
STEP_DETAILS = {
    "decompose": "Convert intent into a hardware spec.",
    "cad": "Generate OpenSCAD and compile printable geometry.",
    "firmware": "Write Arduino control logic and pin mapping.",
    "sourcing": "Assemble the BOM with pricing and suppliers.",
    "sim_verify": "Check stability and capture a verification artifact.",
}
STATUS_ICON = {"pending": "○", "running": "◔", "done": "●", "failed": "✕"}
STATUS_LABEL = {
    "pending": "Pending",
    "running": "Running",
    "done": "Complete",
    "failed": "Needs attention",
}


def inject_theme() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

        :root {
            --bg: #f4efe6;
            --surface: rgba(255, 252, 247, 0.92);
            --surface-strong: #fffaf1;
            --ink: #132a24;
            --muted: #53615d;
            --line: rgba(19, 42, 36, 0.12);
            --accent: #d65d2d;
            --accent-soft: rgba(214, 93, 45, 0.12);
            --signal: #0f6b57;
            --gold: #d6a24f;
            --pending: #c8beb0;
            --failed: #9b3d2f;
            --shadow: 0 18px 40px rgba(27, 37, 33, 0.08);
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(214, 93, 45, 0.14), transparent 24%),
                radial-gradient(circle at top right, rgba(15, 107, 87, 0.10), transparent 26%),
                linear-gradient(180deg, #f8f3ec 0%, var(--bg) 38%, #efe6da 100%);
            color: var(--ink);
            font-family: 'Space Grotesk', sans-serif;
        }

        [data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(15, 27, 24, 0.96) 0%, rgba(24, 42, 37, 0.96) 100%);
            border-right: 1px solid rgba(255, 255, 255, 0.06);
        }

        [data-testid="stSidebar"] * {
            color: #f6f1e9;
        }

        h1, h2, h3, h4 {
            font-family: 'Space Grotesk', sans-serif;
            letter-spacing: -0.03em;
            color: var(--ink);
        }

        p, li, label, .stCaption {
            color: var(--muted);
        }

        .stTextArea textarea, .stTextInput input {
            background: rgba(255, 250, 241, 0.88);
            border: 1px solid rgba(19, 42, 36, 0.10);
            border-radius: 18px;
            color: var(--ink);
            font-size: 1rem;
        }

        .stButton > button, .stDownloadButton > button {
            border-radius: 999px;
            border: 1px solid transparent;
            min-height: 2.8rem;
            font-weight: 600;
            transition: transform 120ms ease, box-shadow 120ms ease, border-color 120ms ease;
            box-shadow: none;
        }

        .stButton > button[kind="primary"], .stDownloadButton > button {
            background: linear-gradient(135deg, var(--accent) 0%, #eb8e3d 100%);
            color: white;
            box-shadow: 0 12px 24px rgba(214, 93, 45, 0.18);
        }

        .stButton > button:hover, .stDownloadButton > button:hover {
            transform: translateY(-1px);
            border-color: rgba(19, 42, 36, 0.08);
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
            background: rgba(255, 252, 247, 0.65);
            padding: 0.35rem;
            border: 1px solid var(--line);
            border-radius: 18px;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 14px;
            min-height: 3rem;
            font-weight: 600;
        }

        .stTabs [aria-selected="true"] {
            background: var(--surface-strong);
            box-shadow: var(--shadow);
        }

        [data-testid="stMetric"] {
            background: rgba(255, 252, 247, 0.84);
            border: 1px solid var(--line);
            border-radius: 20px;
            padding: 0.8rem 1rem;
            box-shadow: var(--shadow);
        }

        [data-testid="stCodeBlock"], .stDataFrame, .stExpander {
            border-radius: 20px;
        }

        .hero-shell {
            padding: 1.7rem 1.8rem;
            border: 1px solid rgba(255,255,255,0.28);
            border-radius: 28px;
            background:
                radial-gradient(circle at top right, rgba(255,255,255,0.18), transparent 28%),
                linear-gradient(135deg, rgba(16, 47, 40, 0.98) 0%, rgba(13, 79, 66, 0.94) 45%, rgba(214, 93, 45, 0.92) 100%);
            box-shadow: 0 22px 54px rgba(16, 33, 29, 0.18);
            color: #fff7ef;
            overflow: hidden;
            position: relative;
        }

        .hero-shell::after {
            content: "";
            position: absolute;
            inset: auto -8% -35% auto;
            width: 240px;
            height: 240px;
            border-radius: 999px;
            background: rgba(255, 245, 228, 0.15);
            filter: blur(4px);
        }

        .eyebrow {
            display: inline-flex;
            gap: 0.45rem;
            align-items: center;
            font-size: 0.78rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: rgba(255, 247, 239, 0.8);
            margin-bottom: 0.9rem;
        }

        .hero-title {
            margin: 0;
            font-size: 3rem;
            line-height: 0.95;
            color: #fffaf2;
            max-width: 16ch;
        }

        .hero-copy {
            margin: 0.9rem 0 0;
            max-width: 54ch;
            color: rgba(255, 247, 239, 0.88);
            font-size: 1rem;
        }

        .badge-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.6rem;
            margin-top: 1.15rem;
        }

        .hero-badge, .signal-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.52rem 0.82rem;
            border-radius: 999px;
            font-size: 0.86rem;
            border: 1px solid rgba(255,255,255,0.18);
            background: rgba(255, 250, 241, 0.12);
            color: #fff6ec;
        }

        .signal-card {
            background: rgba(255, 252, 247, 0.84);
            border: 1px solid var(--line);
            border-radius: 24px;
            box-shadow: var(--shadow);
            padding: 1rem 1.1rem;
            margin-bottom: 0.9rem;
        }

        .signal-kicker {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.14em;
            color: var(--accent);
            margin-bottom: 0.45rem;
        }

        .signal-title {
            margin: 0;
            font-size: 1.25rem;
            color: var(--ink);
        }

        .signal-copy {
            margin: 0.5rem 0 0;
            color: var(--muted);
            line-height: 1.55;
        }

        .status-grid {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 0.7rem;
            margin: 0.4rem 0 1rem;
        }

        .status-card {
            border-radius: 22px;
            padding: 0.9rem 0.95rem;
            border: 1px solid var(--line);
            background: rgba(255, 252, 247, 0.84);
            box-shadow: var(--shadow);
        }

        .status-card.running {
            background: linear-gradient(180deg, rgba(214, 162, 79, 0.18), rgba(255, 252, 247, 0.92));
            border-color: rgba(214, 162, 79, 0.35);
        }

        .status-card.done {
            background: linear-gradient(180deg, rgba(15, 107, 87, 0.14), rgba(255, 252, 247, 0.92));
            border-color: rgba(15, 107, 87, 0.22);
        }

        .status-card.failed {
            background: linear-gradient(180deg, rgba(155, 61, 47, 0.16), rgba(255, 252, 247, 0.92));
            border-color: rgba(155, 61, 47, 0.26);
        }

        .status-step {
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--muted);
        }

        .status-state {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-top: 0.55rem;
            font-weight: 700;
            color: var(--ink);
        }

        .status-detail {
            margin-top: 0.45rem;
            font-size: 0.82rem;
            line-height: 1.45;
            color: var(--muted);
        }

        .side-rail {
            display: grid;
            gap: 0.55rem;
        }

        .rail-step {
            border-radius: 16px;
            padding: 0.72rem 0.8rem;
            border: 1px solid rgba(255,255,255,0.10);
            background: rgba(255,255,255,0.06);
        }

        .rail-step.active {
            background: linear-gradient(135deg, rgba(214, 162, 79, 0.32), rgba(214, 93, 45, 0.22));
            border-color: rgba(255, 219, 171, 0.22);
        }

        .rail-step.done {
            background: rgba(113, 212, 182, 0.10);
            border-color: rgba(113, 212, 182, 0.16);
        }

        .rail-index {
            font-size: 0.72rem;
            opacity: 0.75;
            letter-spacing: 0.14em;
            text-transform: uppercase;
        }

        .rail-label {
            margin-top: 0.2rem;
            font-weight: 600;
            color: #fff7ef;
        }

        .empty-state {
            text-align: center;
            padding: 2rem 1.2rem 1rem;
            color: var(--muted);
        }

        .artifact-grid {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 0.75rem;
            margin-top: 0.6rem;
        }

        .artifact-card {
            border-radius: 20px;
            padding: 0.95rem;
            background: rgba(255, 252, 247, 0.82);
            border: 1px solid var(--line);
            box-shadow: var(--shadow);
        }

        .artifact-label {
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.11em;
            color: var(--muted);
        }

        .artifact-value {
            margin-top: 0.55rem;
            font-weight: 700;
            color: var(--ink);
        }

        .mono {
            font-family: 'IBM Plex Mono', monospace;
        }

        @media (max-width: 1100px) {
            .status-grid, .artifact-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .hero-title {
                font-size: 2.35rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_timeline(container) -> None:
    current = st.session_state.get("current_step", "")
    completed = set(st.session_state.get("completed_steps", []))
    steps = [
        ("decompose", "Decompose prompt"),
        ("cad", "Generate CAD"),
        ("firmware", "Generate firmware"),
        ("sourcing", "Source parts"),
        ("sim_verify", "Run simulation"),
    ]
    cards = []
    for index, (key, label) in enumerate(steps, start=1):
        class_name = "rail-step"
        state_label = "Queued"
        if key in current:
            class_name += " active"
            state_label = "Live"
        elif key in completed:
            class_name += " done"
            state_label = "Done"
        cards.append(
            f"""
            <div class="{class_name}">
                <div class="rail-index">{index:02d} · {state_label}</div>
                <div class="rail-label">{escape(label)}</div>
            </div>
            """
        )
    container.markdown(
        '<div class="side-rail">' + "".join(cards) + "</div>",
        unsafe_allow_html=True,
    )


def render_status_table(container, statuses: dict[str, str]) -> None:
    cards = []
    for step in PIPELINE_STEPS:
        state = statuses.get(step, "pending")
        cards.append(
            f"""
            <div class="status-card {state}">
                <div class="status-step">{escape(STEP_LABELS[step])}</div>
                <div class="status-state">
                    <span>{STATUS_ICON[state]}</span>
                    <span>{escape(STATUS_LABEL[state])}</span>
                </div>
                <div class="status-detail">{escape(STEP_DETAILS[step])}</div>
            </div>
            """
        )
    container.markdown(
        '<div class="status-grid">' + "".join(cards) + "</div>",
        unsafe_allow_html=True,
    )


def render_signal_card(title: str, body: str, kicker: str) -> None:
    st.markdown(
        f"""
        <div class="signal-card">
            <div class="signal-kicker">{escape(kicker)}</div>
            <h3 class="signal-title">{escape(title)}</h3>
            <p class="signal-copy">{escape(body)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    st.markdown(
        """
        <section class="hero-shell">
            <div class="eyebrow">Autonomous Prototyper · Multi-agent hardware pipeline</div>
            <h1 class="hero-title">From one prompt to printable hardware.</h1>
            <p class="hero-copy">
                Generate CAD, firmware, sourcing, and simulation evidence from a single idea.
                This interface is tuned for fast demos: clear stages, visible artifacts, and a
                control-room feel while the pipeline runs.
            </p>
            <div class="badge-row">
                <span class="hero-badge">LangGraph orchestration</span>
                <span class="hero-badge">Gemini-generated outputs</span>
                <span class="hero-badge">OpenSCAD + Arduino + BOM + Sim</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_result_artifacts(state: PrototyperState) -> None:
    parts = state.get("parts_list", [])
    screenshot = state.get("sim_screenshot", "")
    st.markdown(
        f"""
        <div class="artifact-grid">
            <div class="artifact-card">
                <div class="artifact-label">Prompt</div>
                <div class="artifact-value">{escape((state.get("user_prompt", "") or "—")[:70])}</div>
            </div>
            <div class="artifact-card">
                <div class="artifact-label">Artifacts</div>
                <div class="artifact-value">{len([p for p in ['cad_code', 'firmware_code', 'parts_list'] if state.get(p)])} core outputs</div>
            </div>
            <div class="artifact-card">
                <div class="artifact-label">Parts</div>
                <div class="artifact-value">{len(parts)} sourced components</div>
            </div>
            <div class="artifact-card">
                <div class="artifact-label">Simulation</div>
                <div class="artifact-value">{'Stable' if state.get('sim_passed') else 'Needs revision'}</div>
            </div>
            <div class="artifact-card">
                <div class="artifact-label">Visual proof</div>
                <div class="artifact-value">{'Ready' if screenshot and Path(screenshot).exists() else 'Pending'}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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


inject_theme()
st.set_page_config(page_title="Autonomous Prototyper", layout="wide")

with st.sidebar:
    st.markdown("### Control Deck")
    api_key = st.text_input(
        "Google AI API Key",
        type="password",
        value=os.environ.get("GOOGLE_API_KEY", ""),
        help="Stored in memory for this session. You can also set it in .env.",
    )
    if api_key:
        os.environ["GOOGLE_API_KEY"] = api_key

    use_demo = st.checkbox("Use demo data", help="Skip API calls and load the turret example.")
    st.caption("Demo mode is ideal for UI walkthroughs and rehearsals.")

    st.markdown("#### Prompt presets")
    examples = [
        "Build me a voice-controlled turret that tracks blue balls",
        "Create a pan-tilt camera mount controlled by a joystick",
        "Design a servo-powered robotic arm with 3 degrees of freedom",
    ]
    for example in examples:
        if st.button(example, use_container_width=True):
            st.session_state["prompt"] = example

    st.markdown("#### Live pipeline")
    timeline_box = st.empty()
    render_sidebar_timeline(timeline_box)


render_hero()
st.markdown("")

intro_left, intro_right = st.columns([1.55, 0.95], gap="large")

with intro_left:
    st.markdown("### Describe the build")
    prompt = st.text_area(
        "Describe your hardware project",
        label_visibility="collapsed",
        value=st.session_state.get("prompt", ""),
        height=140,
        placeholder="Build a compact two-servo pan-tilt bracket for a lightweight camera with a stable printable base...",
    )
    run_btn = st.button("Run the full pipeline", type="primary", use_container_width=True)

with intro_right:
    render_signal_card(
        "What this run will produce",
        "A printable CAD model, Arduino firmware, a sourced parts list, and a simulation verification artifact.",
        "Outputs",
    )
    render_signal_card(
        "Best prompt strategy",
        "Keep the first run narrow and physical. Clear dimensions, motion goals, and component constraints produce cleaner artifacts.",
        "Prompting note",
    )

status_box = st.empty()
statuses = st.session_state.get("pipeline_statuses", {step: "pending" for step in PIPELINE_STEPS})
render_status_table(status_box, statuses)

if run_btn and prompt:
    st.session_state.pop("pipeline_result", None)
    st.session_state["current_step"] = ""
    st.session_state["completed_steps"] = []
    st.session_state["pipeline_statuses"] = {step: "pending" for step in PIPELINE_STEPS}
    render_sidebar_timeline(timeline_box)
    render_status_table(status_box, st.session_state["pipeline_statuses"])

    if not os.environ.get("GOOGLE_API_KEY") and not use_demo:
        st.error("Set your Google AI API key in the sidebar first, or enable demo mode.")
        st.stop()

    elapsed = 0.0

    if use_demo and Path("mock_specs/turret_spec.json").exists():
        state = load_demo_state()
        statuses = {step: "done" for step in PIPELINE_STEPS}
        st.session_state["completed_steps"] = PIPELINE_STEPS.copy()
        st.session_state["current_step"] = "sim_verify"
        st.session_state["pipeline_statuses"] = statuses
        render_sidebar_timeline(timeline_box)
        render_status_table(status_box, statuses)
        st.session_state["pipeline_result"] = state
        st.session_state["pipeline_elapsed"] = 0.0
        st.success("Loaded the demo pipeline state.")
    else:
        initial_state = build_initial_state(prompt)
        graph = build_graph()
        state = dict(initial_state)
        start_time = time.time()
        step_map = {
            "decompose": "decompose",
            "cad": "cad",
            "firmware": "firmware",
            "sourcing": "sourcing",
            "sim_verify": "sim_verify",
            "increment_retry": "cad",
        }
        statuses = {step: "pending" for step in PIPELINE_STEPS}

        with st.spinner("Agents are running across the pipeline..."):
            for step_output in graph.stream(initial_state):
                node_name = list(step_output.keys())[0]
                node_update = list(step_output.values())[0]
                state.update(node_update)
                resolved_step = step_map.get(node_name)

                st.session_state["current_step"] = node_name
                completed_steps = list(st.session_state.get("completed_steps", []))
                if node_name not in completed_steps:
                    completed_steps.append(node_name)
                st.session_state["completed_steps"] = completed_steps
                render_sidebar_timeline(timeline_box)

                if node_name == "decompose":
                    statuses["decompose"] = "done"
                    statuses["cad"] = "running"
                    statuses["firmware"] = "running"
                    statuses["sourcing"] = "running"
                    st.session_state["pipeline_statuses"] = dict(statuses)
                    render_status_table(status_box, statuses)
                    continue

                if resolved_step:
                    if resolved_step == "sim_verify" and not node_update.get("sim_passed", True):
                        statuses[resolved_step] = "failed"
                    else:
                        statuses[resolved_step] = "done"

                if node_name in {"cad", "firmware", "sourcing"}:
                    pending_parallel = [
                        step for step in ("cad", "firmware", "sourcing")
                        if statuses[step] != "done"
                    ]
                    for step in pending_parallel:
                        statuses[step] = "running"
                    if not pending_parallel:
                        statuses["sim_verify"] = "running"

                if node_name == "increment_retry":
                    statuses["cad"] = "running"
                    statuses["sim_verify"] = "pending"

                st.session_state["pipeline_statuses"] = dict(statuses)
                render_status_table(status_box, statuses)

        elapsed = time.time() - start_time
        statuses = {
            step: ("failed" if step == "sim_verify" and not state.get("sim_passed", False) else "done")
            for step in PIPELINE_STEPS
        }
        st.session_state["pipeline_statuses"] = statuses
        render_status_table(status_box, statuses)
        render_sidebar_timeline(timeline_box)
        st.session_state["pipeline_result"] = state
        st.session_state["pipeline_elapsed"] = elapsed

if "pipeline_result" not in st.session_state:
    st.markdown(
        """
        <div class="empty-state">
            <h3>Ready for a hardware concept.</h3>
            <p>Run the demo mode for a fast walkthrough, or use a live Gemini key to generate a new design.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    state = st.session_state["pipeline_result"]
    elapsed = st.session_state.get("pipeline_elapsed", 0.0)
    tasks = state.get("decomposed_tasks", {})

    st.markdown("### Mission Output")
    render_result_artifacts(state)
    st.markdown("")

    metric_a, metric_b, metric_c = st.columns(3)
    metric_a.metric("Run time", f"{elapsed:.0f}s")
    metric_b.metric("Redesign retries", state.get("retry_count", 0))
    metric_c.metric("Est. cost", "~$0.03")

    tab_cad, tab_fw, tab_parts, tab_sim = st.tabs(
        ["Design Deck", "Control Logic", "Procurement", "Stability Proof"]
    )

    with tab_cad:
        geo = tasks.get("geometry_spec", {})
        top_left, top_right = st.columns([0.9, 1.1], gap="large")
        with top_left:
            render_signal_card(
                tasks.get("goal", "CAD output"),
                geo.get("description", "Geometry spec will appear here after the run."),
                "Geometry",
            )
            dims = geo.get("base_dimensions_mm", {})
            d1, d2, d3 = st.columns(3)
            d1.metric("Width", f"{dims.get('width', '—')} mm")
            d2.metric("Depth", f"{dims.get('depth', '—')} mm")
            d3.metric("Height", f"{dims.get('height', '—')} mm")
            moving = geo.get("moving_parts", [])
            mounts = geo.get("mounting_points", [])
            if moving:
                st.markdown("**Moving assemblies**")
                for part in moving:
                    st.markdown(f"- {part}")
            if mounts:
                st.markdown("**Mounting points**")
                for point in mounts:
                    st.markdown(f"- {point}")
        with top_right:
            st.markdown("#### OpenSCAD source")
            st.code(state.get("cad_code", "— not generated —"), language="openscad")
            stl_path = state.get("stl_path", "") or "outputs/turret.stl"
            scad_path = "outputs/turret.scad"
            if Path(stl_path).exists():
                st.success(f"Compiled STL ready at `{stl_path}`")
            elif Path(scad_path).exists():
                st.warning("OpenSCAD source is ready, but STL compilation was skipped or unavailable.")

    with tab_fw:
        fw_spec = tasks.get("firmware_spec", {})
        fw_left, fw_right = st.columns([0.85, 1.15], gap="large")
        with fw_left:
            render_signal_card(
                fw_spec.get("microcontroller", "Arduino target"),
                fw_spec.get("control_logic", "Control loop details will appear after generation."),
                "Firmware",
            )
            c_inputs, c_outputs = st.columns(2)
            with c_inputs:
                st.markdown("**Inputs**")
                for item in fw_spec.get("inputs", []):
                    st.markdown(f"- {item}")
            with c_outputs:
                st.markdown("**Outputs**")
                for item in fw_spec.get("outputs", []):
                    st.markdown(f"- {item}")
            libraries = fw_spec.get("libraries_needed", [])
            if libraries:
                st.markdown("**Libraries**")
                for library in libraries:
                    st.markdown(f"- `{library}`")
        with fw_right:
            st.markdown("#### Full firmware source")
            st.code(state.get("firmware_code", "— not generated —"), language="cpp")

    with tab_parts:
        parts = list(state.get("parts_list", []))
        if not parts:
            st.info("No parts list generated yet.")
        else:
            for part in parts:
                if "price_cad" not in part:
                    part["price_cad"] = part.pop("price_usd", 0.0)

            total = sum(part.get("price_cad", 0) * part.get("qty", 1) for part in parts)
            supplier_count = len({part.get("supplier", "Unknown") for part in parts})
            p1, p2, p3 = st.columns(3)
            p1.metric("Estimated total", f"${total:.2f} CAD")
            p2.metric("Components", len(parts))
            p3.metric("Suppliers", supplier_count)

            st.markdown("#### Procurement board")
            df = pd.DataFrame(parts)
            display_cols = {
                "name": "Component",
                "model": "Model",
                "price_cad": "Price (CAD)",
                "qty": "Qty",
                "supplier": "Supplier",
                "description": "Notes",
            }
            df = df[[col for col in display_cols if col in df.columns]].rename(columns=display_cols)
            if "Price (CAD)" in df.columns:
                df["Price (CAD)"] = df["Price (CAD)"].apply(lambda value: f"${float(value):.2f}")
            st.dataframe(df, use_container_width=True, hide_index=True)

    with tab_sim:
        sim_left, sim_right = st.columns([1.15, 0.85], gap="large")
        with sim_left:
            screenshot = state.get("sim_screenshot", "")
            if screenshot and Path(screenshot).exists():
                st.image(screenshot, caption="Stability verification artifact", use_container_width=True)
            else:
                st.info("Run the pipeline live to generate a simulation diagram.")
        with sim_right:
            if state.get("sim_passed", False):
                render_signal_card(
                    "Simulation passed",
                    state.get("sim_failure_reason", "Stable across the configured tilt checks."),
                    "Verification",
                )
            else:
                render_signal_card(
                    "Simulation needs revision",
                    state.get("sim_failure_reason", "The current design failed the stability check."),
                    "Verification",
                )
            if state.get("retry_count", 0) > 0:
                st.markdown(f"**{state['retry_count']} redesign attempt(s)**")
                for error in state.get("errors", []):
                    if error.startswith("Retry "):
                        st.markdown(f"- {error}")

    st.divider()
    st.markdown("### Export Artifacts")

    artifacts = [
    {
        "label": "OpenSCAD source",
        "path": "outputs/turret.scad",
        "file_name": "turret.scad",
        "mime": "text/plain",
        "binary": False,
    },
    {
        "label": "STL model",
        "path": state.get("stl_path", "") or "outputs/turret.stl",
        "file_name": "turret.stl",
        "mime": "model/stl",
        "binary": True,
    },
    {
        "label": "Arduino firmware",
        "path": "outputs/firmware.ino",
        "file_name": "firmware.ino",
        "mime": "text/plain",
        "binary": False,
    },
    {
        "label": "Parts list JSON",
        "path": "outputs/parts_list.json",
        "file_name": "parts_list.json",
        "mime": "application/json",
        "binary": False,
    },
    {
        "label": "Simulation image",
        "path": "outputs/sim_screenshot.png",
        "file_name": "sim_screenshot.png",
        "mime": "image/png",
        "binary": True,
    },
    ]

    download_cols = st.columns(len(artifacts))
    for col, artifact in zip(download_cols, artifacts):
        file_path = artifact["path"]
        if file_path and Path(file_path).exists():
            mode = "rb" if artifact["binary"] else "r"
            kwargs = {} if artifact["binary"] else {"encoding": "utf-8"}
            with open(file_path, mode, **kwargs) as handle:
                payload = handle.read()
            if isinstance(payload, str):
                payload = payload.encode("utf-8")
            col.download_button(
                label=artifact["label"],
                data=payload,
                file_name=artifact["file_name"],
                mime=artifact["mime"],
                use_container_width=True,
            )
        else:
            col.button(artifact["label"], disabled=True, use_container_width=True)

    if state.get("errors"):
        with st.expander(f"Non-fatal issues ({len(state['errors'])})"):
            for error in state["errors"]:
                st.markdown(f"- {error}")

    if tasks.get("goal"):
        st.divider()
        st.markdown("### Build Summary")
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Goal", tasks.get("goal", "")[:32] or "—")
        s2.metric("Components", len(state.get("parts_list", [])))
        s3.metric("Stable", "Yes" if state.get("sim_passed") else "No")
        s4.metric("Retries", state.get("retry_count", 0))
