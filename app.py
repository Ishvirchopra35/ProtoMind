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


def render_sidebar_timeline(container) -> None:
    container.markdown("**Pipeline steps**")
    steps = [
        ("decompose", "Decompose prompt"),
        ("cad", "Generate CAD (OpenSCAD)"),
        ("firmware", "Generate firmware (Arduino)"),
        ("sourcing", "Source parts (live prices)"),
        ("sim_verify", "Physics simulation"),
    ]
    current = st.session_state.get("current_step", "")
    completed = set(st.session_state.get("completed_steps", []))

    for key, label in steps:
        if key in current:
            container.markdown(f"🟡 **{label}**")
        elif key in completed:
            container.markdown(f"🟢 {label}")
        else:
            container.markdown(f"⚪ {label}")


def render_status_table(container, statuses: dict[str, str]) -> None:
    styles = {
        "pending": ("#3d4451", "#c4c9d4", "Pending"),
        "running": ("#7c5e10", "#ffd76a", "Running"),
        "done": ("#143f2f", "#8af3c4", "Complete"),
        "failed": ("#4b1d1d", "#ff9f9f", "Needs attention"),
    }
    rows = []
    for step in PIPELINE_STEPS:
        state = statuses.get(step, "pending")
        bg, fg, label = styles[state]
        icon = "⏳" if state == "running" else ("✓" if state == "done" else "•")
        rows.append(
            f"""
            <tr>
                <td style="padding:10px 12px;font-weight:600;">{STEP_LABELS[step]}</td>
                <td style="padding:10px 12px;">
                    <span style="background:{bg};color:{fg};padding:4px 10px;border-radius:999px;">
                        {icon} {label}
                    </span>
                </td>
            </tr>
            """
        )
    container.markdown(
        """
        <table style="width:100%;border-collapse:collapse;border:1px solid #2b3240;">
            <thead>
                <tr style="background:#151a21;">
                    <th style="padding:10px 12px;text-align:left;">Node</th>
                    <th style="padding:10px 12px;text-align:left;">Status</th>
                </tr>
            </thead>
            <tbody>
        """
        + "".join(rows)
        + """
            </tbody>
        </table>
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


st.set_page_config(page_title="Autonomous Prototyper", layout="wide")
st.title("Autonomous Prototyper")
st.caption("Multi-agent hardware pipeline powered by Gemini")

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

if run_btn and prompt:
    st.session_state["current_step"] = ""
    st.session_state["completed_steps"] = []
    render_sidebar_timeline(timeline_box)

    if not os.environ.get("GOOGLE_API_KEY") and not use_demo:
        st.error("Set your Google AI API key in the sidebar first, or enable demo mode.")
        st.stop()

    status_box = st.empty()
    statuses = {step: "pending" for step in PIPELINE_STEPS}
    render_status_table(status_box, statuses)

    state: PrototyperState
    elapsed = 0.0

    if use_demo and Path("mock_specs/turret_spec.json").exists():
        state = load_demo_state()
        statuses = {step: "done" for step in PIPELINE_STEPS}
        st.session_state["completed_steps"] = PIPELINE_STEPS.copy()
        st.session_state["current_step"] = "sim_verify"
        render_sidebar_timeline(timeline_box)
        render_status_table(status_box, statuses)
        st.success("Loaded demo data.")
    else:
        initial_state = build_initial_state(prompt)
        # Accumulated state: starts as the full initial state and is updated
        # with each node's partial output as the graph streams.  We NEVER
        # replace it wholesale — graph.stream() yields partial dicts, not the
        # full state, so replacing would discard all previously-written keys.
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

        with st.spinner("Running pipeline..."):
            for step_output in graph.stream(initial_state):
                node_name = list(step_output.keys())[0]
                node_update = list(step_output.values())[0]
                # Merge the partial update into the accumulated state.
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
                        step
                        for step in ("cad", "firmware", "sourcing")
                        if statuses[step] != "done"
                    ]
                    for step in pending_parallel:
                        statuses[step] = "running"
                    if not pending_parallel:
                        statuses["sim_verify"] = "running"

                if node_name == "increment_retry":
                    statuses["cad"] = "running"
                    statuses["sim_verify"] = "pending"

                render_status_table(status_box, statuses)

        elapsed = time.time() - start_time
        statuses = {
            step: ("failed" if step == "sim_verify" and not state.get("sim_passed", False) else "done")
            for step in PIPELINE_STEPS
        }
        render_status_table(status_box, statuses)
        render_sidebar_timeline(timeline_box)

    st.success("Pipeline complete.")
    retries = state.get("retry_count", 0)
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Run time", f"{elapsed:.0f}s")
    col_b.metric("Redesign retries", retries)
    col_c.metric("Est. cost", "~$0.03")
    st.markdown("---")

    tabs = st.tabs(["CAD", "Firmware", "Parts", "Simulation"])

    with tabs[0]:
        st.subheader("Generated OpenSCAD")
        st.code(state.get("cad_code", ""), language="openscad")

    with tabs[1]:
        st.subheader("Arduino Firmware")
        st.code(state.get("firmware_code", ""), language="cpp")

    with tabs[2]:
        st.subheader("Parts List")
        parts = state.get("parts_list", [])
        if parts:
            total = sum(part.get("price_cad", 0) * part.get("qty", 1) for part in parts)
            st.metric("Estimated Total", f"${total:.2f} CAD")
            df = pd.DataFrame(parts)[["name", "model", "price_cad", "qty", "supplier"]]
            df.columns = ["Component", "Model", "Price (CAD)", "Qty", "Supplier"]
            df["Price (CAD)"] = df["Price (CAD)"].apply(lambda x: f"${x:.2f}")
            st.dataframe(df, use_container_width=True, hide_index=True)

    with tabs[3]:
        st.subheader("Physics Simulation")
        if state.get("sim_passed", False):
            st.success(f"Stable, passed all tilt checks ({state.get('retry_count', 0)} redesigns)")
        else:
            st.error(f"Unstable: {state.get('sim_failure_reason', '')}")

        if state.get("retry_count", 0) > 0:
            st.markdown("**Redesign Attempts**")
            for error in state.get("errors", []):
                if error.startswith("Retry "):
                    st.write(f"- {error}")

        screenshot = state.get("sim_screenshot", "")
        if screenshot and Path(screenshot).exists():
            st.image(screenshot)
        else:
            st.info("Simulation screenshot will appear after a live run.")

    # ------------------------------------------------------------------
    # Downloads — all artifact files checked on disk and offered together.
    # Rendered here in the main Streamlit thread after the graph finishes,
    # so st.download_button() always has the correct ScriptRunContext.
    # ------------------------------------------------------------------
    st.markdown("---")
    st.subheader("Downloads")

    artifacts = [
        {
            "label": "OpenSCAD source (.scad)",
            "path": "outputs/turret.scad",
            "file_name": "turret.scad",
            "mime": "text/plain",
            "mode": "r",
            "encoding": "utf-8",
        },
        {
            "label": "STL model (.stl)",
            "path": state.get("stl_path", "") or "outputs/turret.stl",
            "file_name": "turret.stl",
            "mime": "model/stl",
            "mode": "rb",
            "encoding": None,
        },
        {
            "label": "Arduino firmware (.ino)",
            "path": "outputs/firmware.ino",
            "file_name": "firmware.ino",
            "mime": "text/plain",
            "mode": "r",
            "encoding": "utf-8",
        },
        {
            "label": "Parts list (.json)",
            "path": "outputs/parts_list.json",
            "file_name": "parts_list.json",
            "mime": "application/json",
            "mode": "r",
            "encoding": "utf-8",
        },
        {
            "label": "Simulation screenshot (.png)",
            "path": "outputs/sim_screenshot.png",
            "file_name": "sim_screenshot.png",
            "mime": "image/png",
            "mode": "rb",
            "encoding": None,
        },
    ]

    found_any = False
    dl_cols = st.columns(len(artifacts))
    for col, artifact in zip(dl_cols, artifacts):
        p = artifact["path"]
        if p and Path(p).exists():
            found_any = True
            kwargs = {"encoding": artifact["encoding"]} if artifact["encoding"] else {}
            with open(p, artifact["mode"], **kwargs) as fh:
                data = fh.read()
            if isinstance(data, str):
                data = data.encode("utf-8")
            col.download_button(
                label=artifact["label"],
                data=data,
                file_name=artifact["file_name"],
                mime=artifact["mime"],
                use_container_width=True,
            )
        else:
            col.button(artifact["label"], disabled=True, use_container_width=True)

    if not found_any:
        st.info("No output files were found. Run the pipeline with a live API key to generate artifacts.")

    if state.get("errors"):
        st.markdown("---")
        st.subheader("Non-fatal Errors")
        for error in state["errors"]:
            st.write(f"- {error}")

    st.markdown("---")
    st.subheader("Export full build spec")
    if state.get("cad_code") and state.get("firmware_code"):
        full_spec = {
            "prompt": state.get("user_prompt"),
            "goal": state.get("decomposed_tasks", {}).get("goal", ""),
            "parts_count": len(state.get("parts_list", [])),
            "sim_stable": state.get("sim_passed"),
            "retries": state.get("retry_count", 0),
        }
        st.json(full_spec)
        st.caption("Full CAD, firmware, and parts files are available in the Downloads section above.")
