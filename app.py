import json
import os
import time
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
    "decompose": "Decompose",
    "cad": "CAD",
    "firmware": "Firmware",
    "sourcing": "Sourcing",
    "sim_verify": "Simulation",
}


# ---------------------------------------------------------------------------
# Sidebar timeline — pure Streamlit, no HTML
# ---------------------------------------------------------------------------

def render_sidebar_timeline(container) -> None:
    current = st.session_state.get("current_step", "")
    completed = set(st.session_state.get("completed_steps", []))
    steps = [
        ("decompose", "Decompose prompt"),
        ("cad", "Generate CAD"),
        ("firmware", "Generate firmware"),
        ("sourcing", "Source parts"),
        ("sim_verify", "Simulation"),
    ]
    lines = []
    for key, label in steps:
        if key in current:
            lines.append(f"🟡 **{label}**")
        elif key in completed:
            lines.append(f"🟢 {label}")
        else:
            lines.append(f"⚪ {label}")
    container.markdown("**Pipeline**\n\n" + "\n\n".join(lines))


# ---------------------------------------------------------------------------
# Status table — st.status / columns, no HTML
# ---------------------------------------------------------------------------

STATUS_ICON = {"pending": "⚪", "running": "🟡", "done": "✅", "failed": "❌"}
STATUS_LABEL = {"pending": "Pending", "running": "Running", "done": "Complete", "failed": "Failed"}


def render_status_table(container, statuses: dict[str, str]) -> None:
    with container:
        cols = st.columns(len(PIPELINE_STEPS))
        for col, step in zip(cols, PIPELINE_STEPS):
            s = statuses.get(step, "pending")
            col.metric(
                label=STEP_LABELS[step],
                value=f"{STATUS_ICON[s]} {STATUS_LABEL[s]}",
            )


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Autonomous Prototyper", layout="wide")
st.title("Autonomous Prototyper")
st.caption("Multi-agent hardware pipeline powered by Gemini 2.5 Flash")

with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input(
        "Google AI API Key",
        type="password",
        value=os.environ.get("GOOGLE_API_KEY", ""),
    )
    if api_key:
        os.environ["GOOGLE_API_KEY"] = api_key

    use_demo = st.checkbox("Use demo data (skip API calls)")

    st.markdown("---")
    st.markdown("**Example prompts**")
    examples = [
        "Build me a voice-controlled turret that tracks blue balls",
        "Create a pan-tilt camera mount controlled by a joystick",
        "Design a servo-powered robotic arm with 3 degrees of freedom",
    ]
    for example in examples:
        if st.button(example, use_container_width=True):
            st.session_state["prompt"] = example

    st.markdown("---")
    timeline_box = st.empty()
    render_sidebar_timeline(timeline_box)

prompt = st.text_area(
    "Describe your hardware project",
    value=st.session_state.get("prompt", ""),
    height=90,
    placeholder="Build me a voice-controlled turret that tracks blue balls...",
)

run_btn = st.button("Run Pipeline", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------------

if run_btn and prompt:
    st.session_state.pop("pipeline_result", None)
    st.session_state["current_step"] = ""
    st.session_state["completed_steps"] = []
    render_sidebar_timeline(timeline_box)

    if not os.environ.get("GOOGLE_API_KEY") and not use_demo:
        st.error("Set your Google AI API key in the sidebar first, or enable demo mode.")
        st.stop()

    status_box = st.empty()
    statuses = {step: "pending" for step in PIPELINE_STEPS}
    render_status_table(status_box, statuses)

    elapsed = 0.0

    if use_demo and Path("mock_specs/turret_spec.json").exists():
        state = load_demo_state()
        statuses = {step: "done" for step in PIPELINE_STEPS}
        st.session_state["completed_steps"] = PIPELINE_STEPS.copy()
        st.session_state["current_step"] = "sim_verify"
        render_sidebar_timeline(timeline_box)
        render_status_table(status_box, statuses)
        st.success("Loaded demo data.")
        st.session_state["pipeline_result"] = state
        st.session_state["pipeline_elapsed"] = 0.0
    else:
        initial_state = build_initial_state(prompt)
        state = dict(initial_state)
        graph = build_graph()
        start_time = time.time()
        step_map = {
            "decompose": "decompose",
            "cad": "cad",
            "firmware": "firmware",
            "sourcing": "sourcing",
            "sim_verify": "sim_verify",
            "increment_retry": "cad",
        }

        with st.spinner("Running pipeline…"):
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
                    render_status_table(status_box, statuses)
                    continue

                if resolved_step:
                    if resolved_step == "sim_verify" and not node_update.get("sim_passed", True):
                        statuses[resolved_step] = "failed"
                    else:
                        statuses[resolved_step] = "done"

                if node_name in {"cad", "firmware", "sourcing"}:
                    pending_parallel = [
                        s for s in ("cad", "firmware", "sourcing")
                        if statuses[s] != "done"
                    ]
                    for s in pending_parallel:
                        statuses[s] = "running"
                    if not pending_parallel:
                        statuses["sim_verify"] = "running"

                if node_name == "increment_retry":
                    statuses["cad"] = "running"
                    statuses["sim_verify"] = "pending"

                render_status_table(status_box, statuses)

        elapsed = time.time() - start_time
        statuses = {
            s: ("failed" if s == "sim_verify" and not state.get("sim_passed", False) else "done")
            for s in PIPELINE_STEPS
        }
        render_status_table(status_box, statuses)
        render_sidebar_timeline(timeline_box)
        st.session_state["pipeline_result"] = state
        st.session_state["pipeline_elapsed"] = elapsed

# ---------------------------------------------------------------------------
# Results — rendered on every rerun so downloads survive page refresh
# ---------------------------------------------------------------------------

if "pipeline_result" not in st.session_state:
    st.stop()

state = st.session_state["pipeline_result"]
elapsed = st.session_state.get("pipeline_elapsed", 0.0)
tasks = state.get("decomposed_tasks", {})

st.success("Pipeline complete.")
col_a, col_b, col_c = st.columns(3)
col_a.metric("Run time", f"{elapsed:.0f}s")
col_b.metric("Redesign retries", state.get("retry_count", 0))
col_c.metric("Est. cost", "~$0.03")

st.divider()

tab_cad, tab_fw, tab_parts, tab_sim = st.tabs(["🧱 CAD", "⚡ Firmware", "🛒 Parts", "🔬 Simulation"])

# --- CAD tab ---
with tab_cad:
    geo = tasks.get("geometry_spec", {})
    if geo:
        st.subheader(tasks.get("goal", "CAD Design"))
        c1, c2, c3 = st.columns(3)
        dims = geo.get("base_dimensions_mm", {})
        c1.metric("Width", f"{dims.get('width', '—')} mm")
        c2.metric("Depth", f"{dims.get('depth', '—')} mm")
        c3.metric("Height", f"{dims.get('height', '—')} mm")

        st.info(geo.get("description", ""))

        mc1, mc2 = st.columns(2)
        with mc1:
            moving = geo.get("moving_parts", [])
            if moving:
                st.markdown("**Moving parts**")
                for p in moving:
                    st.markdown(f"- {p}")
        with mc2:
            mounts = geo.get("mounting_points", [])
            if mounts:
                st.markdown("**Mounting points**")
                for m in mounts:
                    st.markdown(f"- {m}")

        stability = geo.get("stability_requirement", "")
        if stability:
            st.caption(f"Stability requirement: {stability}")

    stl_path = state.get("stl_path", "") or "outputs/turret.stl"
    scad_path = "outputs/turret.scad"
    if Path(stl_path).exists():
        st.success(f"STL compiled: `{stl_path}`")
    elif Path(scad_path).exists():
        st.warning("OpenSCAD CLI not found — .scad source generated, STL not compiled.")

    with st.expander("View OpenSCAD source"):
        st.code(state.get("cad_code", "— not generated —"), language="openscad")

# --- Firmware tab ---
with tab_fw:
    fw_spec = tasks.get("firmware_spec", {})
    if fw_spec:
        st.subheader(f"Firmware — {fw_spec.get('microcontroller', 'Arduino')}")

        fc1, fc2 = st.columns(2)
        with fc1:
            st.markdown("**Inputs**")
            for inp in fw_spec.get("inputs", []):
                st.markdown(f"- {inp}")
        with fc2:
            st.markdown("**Outputs**")
            for out in fw_spec.get("outputs", []):
                st.markdown(f"- {out}")

        logic = fw_spec.get("control_logic", "")
        if logic:
            st.info(f"Control logic: {logic}")

        libs = fw_spec.get("libraries_needed", [])
        if libs:
            st.markdown("**Libraries**")
            st.code("\n".join(f"#include <{lib}.h>" for lib in libs), language="cpp")

    with st.expander("View full .ino source"):
        st.code(state.get("firmware_code", "— not generated —"), language="cpp")

# --- Parts tab ---
with tab_parts:
    parts = state.get("parts_list", [])
    if not parts:
        st.info("No parts list generated yet.")
    else:
        # Normalise price field
        for part in parts:
            if "price_cad" not in part:
                part["price_cad"] = part.pop("price_usd", 0.0)

        total = sum(part.get("price_cad", 0) * part.get("qty", 1) for part in parts)
        st.metric("Estimated Total", f"${total:.2f} CAD")

        df = pd.DataFrame(parts)
        display_cols = {"name": "Component", "model": "Model", "price_cad": "Price (CAD)",
                        "qty": "Qty", "supplier": "Supplier", "description": "Notes"}
        df = df[[c for c in display_cols if c in df.columns]].rename(columns=display_cols)
        if "Price (CAD)" in df.columns:
            df["Price (CAD)"] = df["Price (CAD)"].apply(lambda x: f"${float(x):.2f}")
        st.dataframe(df, use_container_width=True, hide_index=True)

# --- Simulation tab ---
with tab_sim:
    passed = state.get("sim_passed", False)
    reason = state.get("sim_failure_reason", "")

    if passed:
        st.success(f"✅ Stable — {reason or 'passed all tilt checks'}")
    else:
        st.error(f"❌ Unstable — {reason}")

    if state.get("retry_count", 0) > 0:
        st.markdown(f"**{state['retry_count']} redesign(s) attempted**")
        for err in state.get("errors", []):
            if err.startswith("Retry "):
                st.markdown(f"- {err}")

    screenshot = state.get("sim_screenshot", "")
    if screenshot and Path(screenshot).exists():
        st.image(screenshot, caption="Stability footprint diagram")
    else:
        st.info("Run the pipeline live to generate a simulation diagram.")

# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Downloads")

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
        "label": "Parts list (JSON)",
        "path": "outputs/parts_list.json",
        "file_name": "parts_list.json",
        "mime": "application/json",
        "binary": False,
    },
    {
        "label": "Sim screenshot",
        "path": "outputs/sim_screenshot.png",
        "file_name": "sim_screenshot.png",
        "mime": "image/png",
        "binary": True,
    },
]

dl_cols = st.columns(len(artifacts))
for col, art in zip(dl_cols, artifacts):
    p = art["path"]
    if p and Path(p).exists():
        mode = "rb" if art["binary"] else "r"
        kwargs = {} if art["binary"] else {"encoding": "utf-8"}
        with open(p, mode, **kwargs) as fh:
            data = fh.read()
        if isinstance(data, str):
            data = data.encode("utf-8")
        col.download_button(
            label=art["label"],
            data=data,
            file_name=art["file_name"],
            mime=art["mime"],
            use_container_width=True,
        )
    else:
        col.button(art["label"], disabled=True, use_container_width=True)

# ---------------------------------------------------------------------------
# Errors + build spec
# ---------------------------------------------------------------------------

if state.get("errors"):
    with st.expander(f"⚠️ {len(state['errors'])} non-fatal error(s)"):
        for err in state["errors"]:
            st.markdown(f"- {err}")

if tasks.get("goal"):
    st.divider()
    st.subheader("Build spec summary")
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Goal", tasks.get("goal", "")[:40])
    sc2.metric("Components", len(state.get("parts_list", [])))
    sc3.metric("Sim stable", "Yes" if state.get("sim_passed") else "No")
    sc4.metric("Retries", state.get("retry_count", 0))
