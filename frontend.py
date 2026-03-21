"""
Autonomous Prototyper — ReactPy + FastAPI frontend
Run:  python frontend.py
Open: http://localhost:8000
"""

import asyncio
import json
import os
import threading
import time
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from reactpy import component, html, use_state
from reactpy.backend.fastapi import configure

load_dotenv()
Path("outputs").mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PIPELINE_STEPS = ["decompose", "cad", "firmware", "sourcing", "sim_verify"]
STEP_LABELS    = {"decompose": "Decompose", "cad": "CAD", "firmware": "Firmware",
                  "sourcing": "Sourcing", "sim_verify": "Simulation"}
STEP_ICONS     = {"decompose": "🧠", "cad": "📐", "firmware": "⚡",
                  "sourcing": "🛒", "sim_verify": "🔬"}
STEP_MAP       = {"decompose": "decompose", "cad": "cad", "firmware": "firmware",
                  "sourcing": "sourcing", "sim_verify": "sim_verify", "increment_retry": "cad"}

EXAMPLES = [
    "Build a voice-controlled turret that tracks blue balls",
    "Create a pan-tilt camera mount controlled by a joystick",
    "Design a servo-powered robotic arm with 3 degrees of freedom",
]

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

BG       = "#080f1c"
SURFACE  = "#0d1a2e"
SURFACE2 = "#112240"
BORDER   = "#1a3456"
GOLD     = "#c9a843"
GOLD_LT  = "#e8c56e"
TEXT     = "#e2e8f0"
TEXT2    = "#8bacc8"
TEXT3    = "#4a6080"
SUCCESS  = "#10b981"
ERROR    = "#ef4444"
WARNING  = "#f59e0b"

# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------

CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}

:root{{
  --bg:{BG};--surface:{SURFACE};--surface2:{SURFACE2};--border:{BORDER};
  --gold:{GOLD};--gold-lt:{GOLD_LT};--text:{TEXT};--text2:{TEXT2};--text3:{TEXT3};
  --success:{SUCCESS};--error:{ERROR};--warning:{WARNING};
  --r:10px;--t:0.18s ease;
}}

html,body{{font-family:'Inter',-apple-system,sans-serif;background:var(--bg);color:var(--text);
  font-size:14px;line-height:1.6;-webkit-font-smoothing:antialiased;min-height:100vh}}

/* Layout */
.app{{display:grid;grid-template-columns:264px 1fr;min-height:100vh}}
.sidebar{{background:var(--surface);border-right:1px solid var(--border);padding:24px 16px;
  display:flex;flex-direction:column;gap:18px;position:sticky;top:0;height:100vh;overflow-y:auto}}
.main{{padding:36px 44px;max-width:1060px}}

/* Brand */
.brand{{padding-bottom:18px;border-bottom:1px solid var(--border)}}
.brand-name{{font-size:16px;font-weight:800;color:var(--gold);letter-spacing:-0.3px}}
.brand-sub{{font-size:11px;color:var(--text3);margin-top:2px}}

/* Sidebar sections */
.sb-section{{display:flex;flex-direction:column;gap:6px}}
.sb-label{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.9px;
  color:var(--text3);margin-bottom:2px}}

/* Inputs */
input,textarea{{width:100%;background:var(--surface2);border:1px solid var(--border);
  border-radius:8px;color:var(--text);font-family:inherit;font-size:13px;
  padding:9px 12px;outline:none;transition:border var(--t),box-shadow var(--t);resize:vertical}}
input:focus,textarea:focus{{border-color:var(--gold);box-shadow:0 0 0 3px rgba(201,168,67,.1)}}
input::placeholder,textarea::placeholder{{color:var(--text3)}}

/* Checkbox */
.checkbox-row{{display:flex;align-items:center;gap:8px;cursor:pointer}}
.checkbox-row input[type=checkbox]{{width:auto;cursor:pointer}}
.checkbox-row span{{font-size:12px;color:var(--text2)}}

/* Buttons */
.btn{{border:none;border-radius:8px;cursor:pointer;font-family:inherit;
  font-size:13px;font-weight:600;padding:9px 14px;transition:all var(--t);width:100%}}
.btn-primary{{background:linear-gradient(135deg,var(--gold),var(--gold-lt));color:var(--bg);
  font-size:15px;padding:13px;letter-spacing:.3px;
  box-shadow:0 4px 20px rgba(201,168,67,.3)}}
.btn-primary:hover{{box-shadow:0 6px 30px rgba(201,168,67,.5);transform:translateY(-1px)}}
.btn-primary:disabled{{opacity:.45;cursor:not-allowed;transform:none;box-shadow:none}}
.btn-ghost{{background:var(--surface2);color:var(--text2);border:1px solid var(--border);
  text-align:left;font-size:12px;font-weight:500;padding:8px 12px}}
.btn-ghost:hover{{border-color:var(--gold);color:var(--gold);background:rgba(201,168,67,.05)}}

/* Pipeline sidebar steps */
.pipeline-list{{display:flex;flex-direction:column;gap:4px}}
.p-item{{display:flex;align-items:center;gap:9px;padding:7px 9px;border-radius:7px;
  transition:background var(--t)}}
.p-item.running{{background:rgba(245,158,11,.06)}}
.p-item.done{{background:rgba(16,185,129,.05)}}
.dot{{width:7px;height:7px;border-radius:50%;flex-shrink:0}}
.dot-pending{{background:var(--text3)}}
.dot-running{{background:var(--warning);animation:pulse 1s ease-in-out infinite}}
.dot-done{{background:var(--success)}}
.dot-failed{{background:var(--error)}}
.p-name{{font-size:12px;font-weight:500;color:var(--text2)}}
.p-item.done .p-name{{color:var(--text)}}
.p-item.running .p-name{{color:var(--warning);font-weight:600}}

/* Hero */
.hero{{margin-bottom:32px}}
.hero-title{{font-size:2.1rem;font-weight:800;line-height:1.15;margin-bottom:8px;
  background:linear-gradient(135deg,var(--gold) 0%,var(--gold-lt) 55%,#e2e8f0 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.hero-sub{{font-size:14px;color:var(--text2)}}

/* Prompt */
.prompt-wrap{{margin-bottom:20px}}
.field-label{{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.8px;
  color:var(--text3);margin-bottom:7px}}

/* Status grid */
.status-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:32px}}
.status-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);
  padding:14px 12px;transition:border-color var(--t),background var(--t)}}
.status-card.running{{border-color:rgba(245,158,11,.4);background:rgba(245,158,11,.04)}}
.status-card.done{{border-color:rgba(16,185,129,.3);background:rgba(16,185,129,.03)}}
.status-card.failed{{border-color:rgba(239,68,68,.35);background:rgba(239,68,68,.03)}}
.sc-icon{{font-size:22px;margin-bottom:6px}}
.sc-name{{font-size:12px;font-weight:600;color:var(--text);margin-bottom:3px}}
.sc-state{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--text3)}}
.status-card.running .sc-state{{color:var(--warning)}}
.status-card.done .sc-state{{color:var(--success)}}
.status-card.failed .sc-state{{color:var(--error)}}

/* Metric row */
.metric-row{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:28px}}
.m-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);
  padding:16px;position:relative;overflow:hidden}}
.m-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;
  background:linear-gradient(90deg,var(--gold),var(--gold-lt))}}
.m-label{{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.8px;
  color:var(--text3);margin-bottom:6px}}
.m-value{{font-size:1.45rem;font-weight:800;color:var(--gold);line-height:1}}
.m-sub{{font-size:10px;color:var(--text3);margin-top:4px}}

/* Tabs */
.tab-bar{{display:flex;border-bottom:1px solid var(--border);gap:2px;margin-bottom:0}}
.tab-btn{{background:transparent;border:none;border-bottom:2px solid transparent;
  color:var(--text2);cursor:pointer;font-family:inherit;font-size:13px;font-weight:500;
  padding:10px 20px;transition:all var(--t);margin-bottom:-1px}}
.tab-btn:hover{{color:var(--gold-lt);background:rgba(201,168,67,.04)}}
.tab-btn.active{{color:var(--gold);border-bottom-color:var(--gold);background:rgba(201,168,67,.06)}}
.tab-panel{{background:var(--surface);border:1px solid var(--border);border-top:none;
  border-radius:0 0 var(--r) var(--r);padding:24px;margin-bottom:24px;
  animation:fadeIn .2s ease forwards}}

/* Section header */
.s-head{{margin-bottom:16px}}
.s-title{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.9px;color:var(--gold)}}
.s-sub{{font-size:12px;color:var(--text3);margin-top:2px}}

/* Spec card */
.spec-card{{background:var(--surface2);border:1px solid var(--border);border-radius:var(--r);
  overflow:hidden;margin-bottom:16px}}
.spec-head{{background:linear-gradient(135deg,var(--surface2),var(--surface));
  border-bottom:1px solid var(--border);padding:9px 14px;
  font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--gold)}}
.spec-row{{display:flex;justify-content:space-between;align-items:flex-start;
  padding:9px 14px;border-bottom:1px solid rgba(26,52,86,.4);gap:16px}}
.spec-row:last-child{{border-bottom:none}}
.spec-k{{font-size:12px;color:var(--text2);font-weight:500;flex-shrink:0}}
.spec-v{{font-size:12px;color:var(--text);text-align:right;max-width:65%}}

/* Chips */
.chips-wrap{{margin-bottom:16px}}
.chips{{display:flex;flex-wrap:wrap;gap:6px;margin-top:7px}}
.chip{{background:rgba(201,168,67,.1);border:1px solid rgba(201,168,67,.25);
  border-radius:6px;color:var(--gold);font-size:12px;font-weight:500;padding:4px 10px}}

/* Code block */
.code-wrap{{background:#040a14;border:1px solid var(--border);border-radius:8px;
  padding:16px;overflow-x:auto;margin-top:8px}}
.code-wrap pre{{font-family:'JetBrains Mono','Fira Code',monospace;font-size:12.5px;
  line-height:1.65;color:#c5d0e0;white-space:pre}}

/* Table */
.tbl{{width:100%;border-collapse:collapse;font-size:13px}}
.tbl th{{background:var(--surface2);border-bottom:1px solid var(--border);color:var(--text3);
  font-size:10px;font-weight:700;letter-spacing:.8px;padding:10px 14px;text-align:left;
  text-transform:uppercase}}
.tbl td{{border-bottom:1px solid rgba(26,52,86,.35);color:var(--text);padding:10px 14px;
  vertical-align:top}}
.tbl tr:last-child td{{border-bottom:none}}
.tbl tbody tr:hover td{{background:rgba(201,168,67,.025)}}

/* Sim result */
.sim-box{{display:flex;gap:14px;align-items:flex-start;padding:16px;border-left:3px solid;
  border-radius:var(--r);margin-bottom:16px}}
.sim-box.pass{{background:rgba(16,185,129,.06);border-color:var(--success)}}
.sim-box.fail{{background:rgba(239,68,68,.06);border-color:var(--error)}}
.sim-icon{{font-size:20px;flex-shrink:0;margin-top:1px}}
.sim-badge{{font-size:10px;font-weight:800;letter-spacing:1px;text-transform:uppercase;
  margin-bottom:4px}}
.sim-box.pass .sim-badge{{color:var(--success)}}
.sim-box.fail .sim-badge{{color:var(--error)}}
.sim-reason{{font-size:13px;color:var(--text);line-height:1.5}}

/* Downloads */
.dl-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}}
.dl-btn{{display:block;background:var(--surface2);border:1px solid var(--border);
  border-radius:8px;color:var(--text2);font-family:inherit;font-size:12px;font-weight:500;
  padding:11px 10px;text-align:center;text-decoration:none;
  transition:all var(--t);cursor:pointer}}
.dl-btn:hover{{border-color:var(--gold);color:var(--gold);background:rgba(201,168,67,.05);
  transform:translateY(-1px)}}
.dl-btn.off{{opacity:.3;cursor:not-allowed;pointer-events:none}}

/* Alert / info */
.alert{{border-left:3px solid;border-radius:8px;font-size:13px;padding:12px 16px;
  margin-bottom:14px}}
.alert-error{{background:rgba(239,68,68,.07);border-color:var(--error);color:#fca5a5}}
.alert-warn{{background:rgba(245,158,11,.07);border-color:var(--warning);color:#fcd34d}}
.alert-info{{background:rgba(201,168,67,.07);border-color:var(--gold);color:var(--gold)}}
.alert-ok{{background:rgba(16,185,129,.07);border-color:var(--success);color:#6ee7b7}}

/* Spinner */
.spinner{{display:inline-block;width:13px;height:13px;border:2px solid rgba(201,168,67,.2);
  border-top-color:var(--gold);border-radius:50%;animation:spin .75s linear infinite;
  margin-right:7px;vertical-align:middle}}

/* Divider */
.divider{{border:none;border-top:1px solid var(--border);margin:24px 0}}
.section-gap{{margin-bottom:28px}}

/* Animations */
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.3}}}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:translateY(0)}}}}
.fade-in{{animation:fadeIn .25s ease forwards}}

/* Scrollbar */
::-webkit-scrollbar{{width:5px;height:5px}}
::-webkit-scrollbar-track{{background:var(--bg)}}
::-webkit-scrollbar-thumb{{background:var(--border);border-radius:3px}}
::-webkit-scrollbar-thumb:hover{{background:var(--gold)}}
"""

# ---------------------------------------------------------------------------
# Pipeline helpers
# ---------------------------------------------------------------------------

def build_initial_state(prompt: str) -> dict:
    return {"user_prompt": prompt, "decomposed_tasks": {}, "cad_code": "",
            "stl_path": "", "firmware_code": "", "parts_list": [],
            "sim_passed": False, "sim_screenshot": "", "sim_failure_reason": "",
            "retry_count": 0, "cad_constraint": "", "current_step": "starting", "errors": []}


def _new_statuses(node_name: str, prev: dict, node_update: dict) -> dict:
    s = dict(prev)
    resolved = STEP_MAP.get(node_name)
    if node_name == "decompose":
        s.update({"decompose": "done", "cad": "running", "firmware": "running", "sourcing": "running"})
    elif resolved:
        s[resolved] = "failed" if resolved == "sim_verify" and not node_update.get("sim_passed", True) else "done"
    if node_name in {"cad", "firmware", "sourcing"}:
        pending = [x for x in ("cad", "firmware", "sourcing") if s[x] != "done"]
        for x in pending:
            s[x] = "running"
        if not pending:
            s["sim_verify"] = "running"
    if node_name == "increment_retry":
        s["cad"] = "running"
        s["sim_verify"] = "pending"
    return s

# ---------------------------------------------------------------------------
# Reusable UI helpers (return ReactPy vnodes)
# ---------------------------------------------------------------------------

def _section_header(title: str, subtitle: str = ""):
    sub = html.p({"class_name": "s-sub"}, subtitle) if subtitle else html.span({})
    return html.div({"class_name": "s-head"},
                    html.p({"class_name": "s-title"}, title), sub)


def _spec_card(title: str, rows: list[tuple[str, str]]):
    return html.div(
        {"class_name": "spec-card"},
        html.div({"class_name": "spec-head"}, title),
        *[html.div({"class_name": "spec-row", "key": k},
                   html.span({"class_name": "spec-k"}, k),
                   html.span({"class_name": "spec-v"}, v))
          for k, v in rows],
    )


def _chip_list(label: str, items: list[str]):
    if not items:
        return html.span({})
    return html.div(
        {"class_name": "chips-wrap"},
        html.div({"class_name": "sb-label"}, label),
        html.div({"class_name": "chips"},
                 *[html.span({"class_name": "chip", "key": str(i)}, item)
                   for i, item in enumerate(items)]),
    )


def _code_block(code: str):
    return html.div({"class_name": "code-wrap"},
                    html.pre({}, html.code({}, code or "# not generated")))


def _divider():
    return html.hr({"class_name": "divider"})


def _alert(msg: str, kind: str = "info"):
    return html.div({"class_name": f"alert alert-{kind}"}, msg)

# ---------------------------------------------------------------------------
# Sub-components
# ---------------------------------------------------------------------------

@component
def Sidebar(api_key, use_demo, step_statuses, on_api_key_change, on_demo_change, on_example_click):
    return html.aside(
        {"class_name": "sidebar"},
        # Brand
        html.div({"class_name": "brand"},
                 html.div({"class_name": "brand-name"}, "⚙️  Autonomous Prototyper"),
                 html.div({"class_name": "brand-sub"}, "Gemini 2.5 Flash · Hardware Pipeline")),
        # API key
        html.div({"class_name": "sb-section"},
                 html.div({"class_name": "sb-label"}, "Google AI API Key"),
                 html.input({"type": "password", "placeholder": "AIza...",
                             "value": api_key,
                             "on_change": lambda e: on_api_key_change(e["target"]["value"])})),
        # Demo toggle
        html.label(
            {"class_name": "checkbox-row"},
            html.input({"type": "checkbox", "checked": use_demo,
                        "on_change": lambda e: on_demo_change(e["target"]["checked"])}),
            html.span({}, "Use demo data (skip API)")),
        _divider(),
        # Examples
        html.div({"class_name": "sb-section"},
                 html.div({"class_name": "sb-label"}, "Example prompts"),
                 *[html.button({"class_name": "btn btn-ghost", "key": str(i),
                                "on_click": lambda _e, ex=ex: on_example_click(ex)},
                               f"↗  {ex}")
                   for i, ex in enumerate(EXAMPLES)]),
        _divider(),
        # Pipeline progress
        html.div({"class_name": "sb-section"},
                 html.div({"class_name": "sb-label"}, "Pipeline progress"),
                 html.div({"class_name": "pipeline-list"},
                          *[html.div(
                              {"class_name": f"p-item {step_statuses.get(step, 'pending')}", "key": step},
                              html.div({"class_name": f"dot dot-{step_statuses.get(step, 'pending')}"}),
                              html.span({"class_name": "p-name"},
                                        f"{STEP_ICONS[step]}  {STEP_LABELS[step]}"))
                            for step in PIPELINE_STEPS])),
    )


@component
def StatusGrid(statuses):
    STATE_LABEL = {"pending": "Waiting", "running": "Running", "done": "Complete", "failed": "Failed"}
    return html.div(
        {"class_name": "status-grid"},
        *[html.div(
            {"class_name": f"status-card {statuses.get(step, 'pending')}", "key": step},
            html.div({"class_name": "sc-icon"}, STEP_ICONS[step]),
            html.div({"class_name": "sc-name"}, STEP_LABELS[step]),
            html.div({"class_name": "sc-state"}, STATE_LABEL[statuses.get(step, "pending")]))
          for step in PIPELINE_STEPS],
    )


@component
def MetricRow(elapsed, parts_count, total_cad, sim_passed, retries):
    metrics = [
        ("Run time",    f"{elapsed:.0f}s",         "wall-clock"),
        ("Components",  str(parts_count),           "in parts list"),
        ("Est. total",  f"${total_cad:.2f} CAD",   "Amazon.ca"),
        ("Simulation",  "✓ Stable" if sim_passed else "✗ Unstable", "tilt test"),
        ("Retries",     str(retries),               "CAD redesigns"),
    ]
    return html.div(
        {"class_name": "metric-row"},
        *[html.div(
            {"class_name": "m-card", "key": label},
            html.div({"class_name": "m-label"}, label),
            html.div({"class_name": "m-value"}, value),
            html.div({"class_name": "m-sub"}, sub))
          for label, value, sub in metrics],
    )


@component
def CadTab(result):
    tasks = result.get("decomposed_tasks", {})
    geo   = tasks.get("geometry_spec", {})
    dims  = geo.get("base_dimensions_mm", {})

    spec_rows = []
    if geo.get("description"):
        spec_rows.append(("Description", geo["description"]))
    spec_rows += [
        ("Width",    f"{dims.get('width', '—')} mm"),
        ("Depth",    f"{dims.get('depth', '—')} mm"),
        ("Height",   f"{dims.get('height', '—')} mm"),
        ("Stability", geo.get("stability_requirement", "—")),
    ]

    stl_path  = result.get("stl_path", "") or "outputs/turret.stl"
    scad_path = "outputs/turret.scad"
    if Path(stl_path).exists():
        status_el = _alert(f"STL compiled → {stl_path}", "ok")
    elif Path(scad_path).exists():
        status_el = _alert("OpenSCAD CLI not found — .scad generated, STL skipped.", "warn")
    else:
        status_el = html.span({})

    return html.div(
        {},
        _section_header(tasks.get("goal", "CAD Design"), "Geometry spec derived from your prompt"),
        html.div({"style": {"height": "16px"}}),
        html.div(
            {"style": {"display": "grid", "grid-template-columns": "1fr 1fr", "gap": "16px"}},
            _spec_card("Geometry Specification", spec_rows),
            html.div(
                {},
                _chip_list("Moving Parts",    geo.get("moving_parts", [])),
                _chip_list("Mounting Points", geo.get("mounting_points", [])),
            ),
        ),
        html.div({"style": {"height": "16px"}}),
        status_el,
        html.div({"style": {"height": "16px"}}),
        html.div({"class_name": "sb-label"}, "OpenSCAD Source"),
        _code_block(result.get("cad_code", "")),
    )


@component
def FirmwareTab(result):
    tasks   = result.get("decomposed_tasks", {})
    fw_spec = tasks.get("firmware_spec", {})
    mcu     = fw_spec.get("microcontroller", "Arduino")

    spec_rows = [("Microcontroller", mcu)]
    if fw_spec.get("control_logic"):
        spec_rows.append(("Control logic", fw_spec["control_logic"]))

    libs = fw_spec.get("libraries_needed", [])
    lib_code = "\n".join(f"#include <{lib}.h>" for lib in libs) if libs else ""

    return html.div(
        {},
        _section_header(f"Firmware — {mcu}", "Auto-generated Arduino sketch"),
        html.div({"style": {"height": "16px"}}),
        html.div(
            {"style": {"display": "grid", "grid-template-columns": "1fr 1fr 1fr", "gap": "16px"}},
            _spec_card("Firmware Spec", spec_rows),
            _chip_list("Inputs",  fw_spec.get("inputs",  [])),
            _chip_list("Outputs", fw_spec.get("outputs", [])),
        ),
        html.div({"style": {"height": "4px"}}),
        *([ html.div({"class_name": "sb-label", "style": {"margin-bottom": "4px"}}, "Required Libraries"),
            _code_block(lib_code)] if lib_code else []),
        html.div({"style": {"height": "16px"}}),
        html.div({"class_name": "sb-label"}, "Full .ino Source"),
        _code_block(result.get("firmware_code", "")),
    )


@component
def PartsTab(result):
    parts = list(result.get("parts_list", []))
    for p in parts:
        if "price_cad" not in p:
            p["price_cad"] = p.pop("price_usd", 0.0)

    if not parts:
        return _alert("No parts list generated yet.", "info")

    total = sum(p.get("price_cad", 0) * p.get("qty", 1) for p in parts)

    cols = ["name", "model", "price_cad", "qty", "supplier", "description"]
    headers = ["Component", "Model", "Price (CAD)", "Qty", "Supplier", "Notes"]

    def _cell(part, col):
        val = part.get(col, "—")
        if col == "price_cad":
            try:
                val = f"${float(val):.2f}"
            except Exception:
                val = str(val)
        return html.td({"key": col}, str(val) if val is not None else "—")

    return html.div(
        {},
        _section_header("Parts List", f"Sourced from Amazon.ca · {len(parts)} components"),
        html.div({"style": {"margin": "12px 0"}},
                 html.div({"class_name": "m-card",
                           "style": {"display": "inline-block", "min-width": "200px"}},
                          html.div({"class_name": "m-label"}, "Estimated Total"),
                          html.div({"class_name": "m-value"}, f"${total:.2f} CAD"))),
        html.div({"style": {"height": "16px"}}),
        html.div(
            {"style": {"overflow-x": "auto", "border": f"1px solid {BORDER}",
                       "border-radius": "10px"}},
            html.table(
                {"class_name": "tbl"},
                html.thead(html.tr(
                    *[html.th({"key": h}, h) for h in headers])),
                html.tbody(
                    *[html.tr({"key": str(i)},
                              *[_cell(p, c) for c in cols])
                      for i, p in enumerate(parts)]),
            ),
        ),
    )


@component
def SimTab(result):
    passed     = result.get("sim_passed", False)
    reason     = result.get("sim_failure_reason", "")
    screenshot = result.get("sim_screenshot", "")
    retries    = result.get("retry_count", 0)
    errors     = [e for e in result.get("errors", []) if e.startswith("Retry ")]

    sim_class = "sim-box pass" if passed else "sim-box fail"
    sim_icon  = "✓" if passed else "✕"
    sim_badge = "STABLE" if passed else "UNSTABLE"
    sim_msg   = reason or ("Passed all stability checks." if passed else "Failed stability check.")

    retry_section = html.span({})
    if retries > 0:
        retry_section = html.div(
            {"style": {"margin-top": "16px"}},
            html.div({"class_name": "sb-label"}, f"{retries} Redesign Attempt(s)"),
            html.ul(
                {"style": {"padding-left": "18px", "margin-top": "8px"}},
                *[html.li({"key": str(i), "style": {"color": TEXT2, "font-size": "13px",
                                                     "margin-bottom": "4px"}}, e)
                  for i, e in enumerate(errors)]),
        )

    img_el = html.span({})
    if screenshot and Path(screenshot).exists():
        img_el = html.div(
            {"style": {"margin-top": "20px"}},
            html.div({"class_name": "sb-label", "style": {"margin-bottom": "8px"}},
                     "Stability Diagram"),
            html.img({"src": f"/files/{Path(screenshot).name}",
                      "style": {"max-width": "100%", "border-radius": "8px",
                                "border": f"1px solid {BORDER}"}}),
        )

    return html.div(
        {},
        _section_header("Physics Simulation", "Geometric stability check at 15°, 30°, 45° tilt"),
        html.div({"style": {"height": "16px"}}),
        html.div(
            {"class_name": sim_class},
            html.div({"class_name": "sim-icon"}, sim_icon),
            html.div(
                {},
                html.div({"class_name": "sim-badge"}, sim_badge),
                html.div({"class_name": "sim-reason"}, sim_msg),
            ),
        ),
        retry_section,
        img_el,
    )


@component
def ResultsTabs(result):
    active, set_active = use_state("cad")

    tab_defs = [("cad", "📐  CAD"), ("fw", "⚡  Firmware"),
                ("parts", "🛒  Parts"), ("sim", "🔬  Simulation")]

    panels = {
        "cad":   CadTab(result),
        "fw":    FirmwareTab(result),
        "parts": PartsTab(result),
        "sim":   SimTab(result),
    }

    return html.div(
        {},
        html.div(
            {"class_name": "tab-bar"},
            *[html.button(
                {"class_name": f"tab-btn {'active' if active == tid else ''}",
                 "key": tid,
                 "on_click": lambda _e, t=tid: set_active(t)},
                label)
              for tid, label in tab_defs],
        ),
        html.div({"class_name": "tab-panel"}, panels[active]),
    )


@component
def Downloads(result):
    stl = result.get("stl_path", "") or "outputs/turret.stl"
    artifacts = [
        ("OpenSCAD (.scad)",   "outputs/turret.scad",       "turret.scad"),
        ("STL model (.stl)",   stl,                          "turret.stl"),
        ("Firmware (.ino)",    "outputs/firmware.ino",       "firmware.ino"),
        ("Parts list (.json)", "outputs/parts_list.json",    "parts_list.json"),
        ("Sim diagram (.png)", "outputs/sim_screenshot.png", "sim_screenshot.png"),
    ]

    def _dl(label, path, fname):
        exists = path and Path(path).exists()
        if exists:
            return html.a(
                {"class_name": "dl-btn", "key": label,
                 "href": f"/files/{fname}", "download": fname},
                f"⬇  {label}",
            )
        return html.span({"class_name": "dl-btn off", "key": label}, f"⬇  {label}")

    return html.div(
        {},
        _section_header("Downloads", "All generated build artifacts"),
        html.div({"style": {"height": "12px"}}),
        html.div({"class_name": "dl-grid"},
                 *[_dl(label, path, fname) for label, path, fname in artifacts]),
    )

# ---------------------------------------------------------------------------
# Root App component
# ---------------------------------------------------------------------------

@component
def App():
    api_key,       set_api_key       = use_state(os.environ.get("GOOGLE_API_KEY", ""))
    use_demo,      set_use_demo      = use_state(False)
    prompt,        set_prompt        = use_state("")
    status,        set_status        = use_state("idle")   # idle | running | done | error
    node_statuses, set_node_statuses = use_state({s: "pending" for s in PIPELINE_STEPS})
    result,        set_result        = use_state({})
    elapsed,       set_elapsed       = use_state(0.0)
    error_msg,     set_error_msg     = use_state("")

    async def handle_run(_event):
        if not prompt.strip() or status == "running":
            return
        if not api_key and not use_demo:
            set_error_msg("Set your Google AI API key in the sidebar first.")
            return

        # Reset
        set_error_msg("")
        set_status("running")
        set_node_statuses({s: "pending" for s in PIPELINE_STEPS})
        set_result({})
        set_elapsed(0.0)

        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key

        if use_demo and Path("mock_specs/turret_spec.json").exists():
            demo = json.loads(Path("mock_specs/turret_spec.json").read_text())
            set_node_statuses({s: "done" for s in PIPELINE_STEPS})
            set_result(demo)
            set_status("done")
            return

        loop  = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def run_pipeline():
            from graph.graph import build_graph
            try:
                initial    = build_initial_state(prompt.strip())
                accumulated = dict(initial)
                graph      = build_graph()
                statuses_local = {s: "pending" for s in PIPELINE_STEPS}
                start      = time.time()

                for step_output in graph.stream(initial):
                    node_name   = list(step_output.keys())[0]
                    node_update = list(step_output.values())[0]
                    accumulated.update(node_update)
                    statuses_local = _new_statuses(node_name, statuses_local, node_update)
                    asyncio.run_coroutine_threadsafe(
                        queue.put(("step", dict(statuses_local), dict(accumulated))), loop)

                asyncio.run_coroutine_threadsafe(
                    queue.put(("done", dict(accumulated), time.time() - start)), loop)
            except Exception as exc:
                asyncio.run_coroutine_threadsafe(queue.put(("error", str(exc))), loop)

        threading.Thread(target=run_pipeline, daemon=True).start()

        while True:
            msg = await queue.get()
            if msg[0] == "step":
                _, s_update, acc = msg
                set_node_statuses(s_update)
                set_result(acc)
            elif msg[0] == "done":
                _, acc, t = msg
                set_result(acc)
                set_elapsed(t)
                set_status("done")
                break
            elif msg[0] == "error":
                set_error_msg(msg[1])
                set_status("error")
                break

    def on_example_click(ex):
        set_prompt(ex)

    # Derive parts total for metric row
    parts = result.get("parts_list", [])
    for p in parts:
        if "price_cad" not in p:
            p["price_cad"] = p.pop("price_usd", 0.0)
    total_cad = sum(p.get("price_cad", 0) * p.get("qty", 1) for p in parts)

    run_disabled = status == "running" or not prompt.strip()

    return html.div(
        {"class_name": "app"},
        # Inject CSS once
        html.style({}, CSS),
        # Sidebar
        Sidebar(
            api_key=api_key,
            use_demo=use_demo,
            step_statuses=node_statuses,
            on_api_key_change=set_api_key,
            on_demo_change=set_use_demo,
            on_example_click=on_example_click,
        ),
        # Main
        html.main(
            {"class_name": "main"},
            # Hero
            html.div(
                {"class_name": "hero"},
                html.h1({"class_name": "hero-title"}, "Autonomous Prototyper"),
                html.p({"class_name": "hero-sub"},
                       "Describe a hardware project — get CAD, firmware, parts list and simulation."),
            ),
            # Prompt
            html.div(
                {"class_name": "prompt-wrap"},
                html.div({"class_name": "field-label"}, "Your project"),
                html.textarea({
                    "rows": "4",
                    "placeholder": "e.g. Build a voice-controlled turret that tracks blue balls…",
                    "value": prompt,
                    "on_change": lambda e: set_prompt(e["target"]["value"]),
                    "style": {"margin-bottom": "12px"},
                }),
                html.button(
                    {"class_name": "btn btn-primary",
                     "on_click": handle_run,
                     "disabled": run_disabled},
                    html.span({"class_name": "spinner"}) if status == "running" else html.span({}),
                    "Running pipeline…" if status == "running" else "⚡  Run Pipeline",
                ),
            ),
            # Error banner
            html.div({}, _alert(error_msg, "error")) if error_msg else html.span({}),
            # Status grid (shown once pipeline has been triggered)
            StatusGrid(node_statuses) if status != "idle" else html.span({}),
            # Results (shown after done)
            html.div(
                {"class_name": "fade-in"},
                MetricRow(elapsed, len(parts), total_cad,
                          result.get("sim_passed", False), result.get("retry_count", 0)),
                ResultsTabs(result),
                _divider(),
                Downloads(result),
                # Non-fatal errors
                *([ _divider(),
                    _section_header(f"⚠️  {len(result['errors'])} non-fatal error(s)"),
                    html.ul({"style": {"padding-left": "18px", "margin-top": "8px"}},
                            *[html.li({"key": str(i), "style": {"color": TEXT2, "font-size": "13px",
                                                                 "margin-bottom": "4px"}}, e)
                              for i, e in enumerate(result["errors"])])]
                  if result.get("errors") else []),
            ) if status == "done" else html.span({}),
        ),
    )

# ---------------------------------------------------------------------------
# FastAPI + file serving
# ---------------------------------------------------------------------------

fastapi_app = FastAPI()

@fastapi_app.get("/files/{filename}")
async def serve_file(filename: str):
    path = Path("outputs") / filename
    if path.exists():
        return FileResponse(path)
    return {"error": "file not found"}

# Mount ReactPy app at /app
from reactpy.backend.fastapi import Options
from fastapi.responses import HTMLResponse

configure(fastapi_app, App, options=Options(url_prefix="/app"))

LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Autonomous Prototyper</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#080f1c;--surface:#0d1a2e;--surface2:#112240;--border:#1a3456;
  --gold:#c9a843;--gold-lt:#e8c56e;--gold-dim:rgba(201,168,67,.12);
  --text:#e2e8f0;--text2:#8bacc8;--text3:#4a6080;
  --success:#10b981;--r:12px;
}
html,body{font-family:'Inter',-apple-system,sans-serif;background:var(--bg);
  color:var(--text);-webkit-font-smoothing:antialiased;min-height:100vh;overflow-x:hidden}

/* ── NAV ─────────────────────────────────────────── */
nav{display:flex;align-items:center;justify-content:space-between;
  padding:18px 60px;border-bottom:1px solid var(--border);
  position:sticky;top:0;z-index:50;
  background:rgba(8,15,28,.85);backdrop-filter:blur(12px)}
.nav-brand{font-size:15px;font-weight:800;color:var(--gold);letter-spacing:-.3px}
.nav-cta{background:linear-gradient(135deg,var(--gold),var(--gold-lt));color:var(--bg);
  border:none;border-radius:8px;cursor:pointer;font-family:inherit;
  font-size:13px;font-weight:700;padding:9px 22px;text-decoration:none;
  transition:box-shadow .18s,transform .18s;
  box-shadow:0 4px 20px rgba(201,168,67,.3)}
.nav-cta:hover{box-shadow:0 6px 30px rgba(201,168,67,.55);transform:translateY(-1px)}

/* ── HERO ─────────────────────────────────────────── */
.hero{text-align:center;padding:100px 24px 80px;position:relative;overflow:hidden}
.hero::before{content:'';position:absolute;inset:0;
  background:radial-gradient(ellipse 70% 50% at 50% 0%,rgba(201,168,67,.08) 0%,transparent 70%);
  pointer-events:none}
.badge{display:inline-flex;align-items:center;gap:7px;
  background:var(--gold-dim);border:1px solid rgba(201,168,67,.3);
  border-radius:100px;color:var(--gold);font-size:12px;font-weight:600;
  letter-spacing:.4px;padding:5px 14px;margin-bottom:28px}
.badge-dot{width:6px;height:6px;border-radius:50%;background:var(--gold);
  animation:pulse 1.6s ease-in-out infinite}
.hero-title{font-size:clamp(2.4rem,5vw,4rem);font-weight:900;line-height:1.1;
  margin-bottom:22px;letter-spacing:-1.5px;
  background:linear-gradient(135deg,var(--gold) 0%,var(--gold-lt) 45%,#e2e8f0 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.hero-sub{font-size:1.15rem;color:var(--text2);max-width:580px;margin:0 auto 44px;
  line-height:1.7;font-weight:400}
.hero-btn{display:inline-flex;align-items:center;gap:10px;
  background:linear-gradient(135deg,var(--gold),var(--gold-lt));color:var(--bg);
  border:none;border-radius:10px;cursor:pointer;font-family:inherit;
  font-size:16px;font-weight:800;padding:16px 36px;text-decoration:none;
  letter-spacing:.2px;
  box-shadow:0 8px 32px rgba(201,168,67,.4);
  transition:box-shadow .2s,transform .2s}
.hero-btn:hover{box-shadow:0 12px 48px rgba(201,168,67,.6);transform:translateY(-2px)}
.hero-btn svg{width:18px;height:18px}
.hero-note{margin-top:18px;font-size:12px;color:var(--text3)}

/* ── STATS STRIP ──────────────────────────────────── */
.stats{display:flex;justify-content:center;gap:0;border-top:1px solid var(--border);
  border-bottom:1px solid var(--border);background:var(--surface)}
.stat{flex:1;max-width:220px;padding:28px 20px;text-align:center;
  border-right:1px solid var(--border)}
.stat:last-child{border-right:none}
.stat-val{font-size:1.9rem;font-weight:800;color:var(--gold);line-height:1}
.stat-label{font-size:11px;color:var(--text3);margin-top:6px;
  font-weight:600;text-transform:uppercase;letter-spacing:.7px}

/* ── HOW IT WORKS ─────────────────────────────────── */
.section{padding:80px 60px;max-width:1100px;margin:0 auto}
.s-eyebrow{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1.2px;
  color:var(--gold);margin-bottom:12px}
.s-title{font-size:clamp(1.5rem,2.5vw,2rem);font-weight:800;color:var(--text);
  line-height:1.25;margin-bottom:14px;letter-spacing:-.5px}
.s-body{font-size:15px;color:var(--text2);line-height:1.7;max-width:520px}

.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
  gap:14px;margin-top:48px}
.step{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);
  padding:24px 20px;position:relative;transition:border-color .2s,transform .2s}
.step:hover{border-color:rgba(201,168,67,.35);transform:translateY(-3px)}
.step-num{font-size:10px;font-weight:800;color:var(--text3);letter-spacing:1.5px;
  text-transform:uppercase;margin-bottom:12px}
.step-icon{font-size:28px;margin-bottom:10px}
.step-name{font-size:14px;font-weight:700;color:var(--text);margin-bottom:6px}
.step-desc{font-size:12px;color:var(--text3);line-height:1.6}
.step-line{position:absolute;top:36px;right:-8px;width:15px;height:1px;
  background:var(--border);z-index:1}
.step:last-child .step-line{display:none}

/* ── FEATURES ─────────────────────────────────────── */
.features{background:var(--surface);border-top:1px solid var(--border);
  border-bottom:1px solid var(--border);padding:80px 60px}
.features-inner{max-width:1100px;margin:0 auto}
.feature-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));
  gap:20px;margin-top:48px}
.feat{background:var(--bg);border:1px solid var(--border);border-radius:var(--r);
  padding:28px;transition:border-color .2s}
.feat:hover{border-color:rgba(201,168,67,.3)}
.feat-icon{font-size:24px;margin-bottom:14px}
.feat-name{font-size:14px;font-weight:700;color:var(--text);margin-bottom:8px}
.feat-desc{font-size:13px;color:var(--text2);line-height:1.65}

/* ── CODE SNIPPETS ────────────────────────────────── */
.snippets{padding:80px 60px;max-width:1100px;margin:0 auto}
.snippet-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:48px}
@media(max-width:780px){.snippet-grid{grid-template-columns:1fr}}
.snippet{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);
  overflow:hidden}
.snippet-head{background:var(--surface2);border-bottom:1px solid var(--border);
  padding:10px 16px;display:flex;align-items:center;gap:8px}
.snippet-title{font-size:11px;font-weight:700;text-transform:uppercase;
  letter-spacing:.9px;color:var(--gold)}
.snippet-tag{font-size:10px;font-weight:600;color:var(--text3);
  background:var(--bg);border:1px solid var(--border);
  border-radius:4px;padding:2px 7px}
.snippet-body{padding:16px;background:#040a14;overflow-x:auto}
.snippet-body pre{font-family:'JetBrains Mono','Fira Code',monospace;
  font-size:12px;line-height:1.7;color:#c5d0e0;white-space:pre}
.kw{color:#c792ea}.fn{color:#82aaff}.str{color:#c3e88d}
.cm{color:#546e7a;font-style:italic}.num{color:#f78c6c}
.ty{color:#ffcb6b}

/* ── OUTPUT PREVIEW ───────────────────────────────── */
.preview-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
  gap:14px;margin-top:48px}
.preview-card{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--r);overflow:hidden;transition:border-color .2s,transform .2s}
.preview-card:hover{border-color:rgba(201,168,67,.3);transform:translateY(-3px)}
.pc-header{background:var(--surface2);border-bottom:1px solid var(--border);
  padding:10px 14px;font-size:10px;font-weight:700;text-transform:uppercase;
  letter-spacing:.9px;color:var(--gold)}
.pc-body{padding:16px}
.pc-line{display:flex;justify-content:space-between;align-items:center;
  padding:5px 0;border-bottom:1px solid rgba(26,52,86,.3);
  font-size:12px}
.pc-line:last-child{border-bottom:none}
.pc-k{color:var(--text2)}
.pc-v{color:var(--text);font-weight:500;font-family:'JetBrains Mono',monospace;font-size:11px}
.pc-badge{font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px}
.pc-badge-ok{background:rgba(16,185,129,.15);color:#10b981}
.pc-badge-warn{background:rgba(245,158,11,.15);color:#f59e0b}
.pc-metric{text-align:center;padding:8px 0}
.pc-mval{font-size:1.6rem;font-weight:800;color:var(--gold)}
.pc-msub{font-size:10px;color:var(--text3);margin-top:3px;text-transform:uppercase;letter-spacing:.5px}

/* ── CTA BANNER ───────────────────────────────────── */
.cta-banner{text-align:center;padding:80px 24px;position:relative;overflow:hidden}
.cta-banner::before{content:'';position:absolute;inset:0;
  background:radial-gradient(ellipse 60% 60% at 50% 100%,rgba(201,168,67,.07),transparent 70%)}
.cta-title{font-size:clamp(1.8rem,3vw,2.5rem);font-weight:800;
  letter-spacing:-.5px;margin-bottom:16px;
  background:linear-gradient(135deg,var(--gold),var(--gold-lt),#e2e8f0);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.cta-sub{font-size:15px;color:var(--text2);margin-bottom:36px;line-height:1.6}

/* ── FOOTER ───────────────────────────────────────── */
footer{border-top:1px solid var(--border);padding:28px 60px;
  display:flex;align-items:center;justify-content:space-between}
.footer-brand{font-size:13px;font-weight:700;color:var(--gold)}
.footer-note{font-size:12px;color:var(--text3)}

/* ── ANIMATIONS ───────────────────────────────────── */
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
@keyframes fadeUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
.fade-up{animation:fadeUp .6s ease forwards}
.delay-1{animation-delay:.1s;opacity:0}
.delay-2{animation-delay:.2s;opacity:0}
.delay-3{animation-delay:.3s;opacity:0}

/* ── SCROLLBAR ────────────────────────────────────── */
::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:var(--gold)}
</style>
</head>
<body>

<!-- NAV -->
<nav>
  <div class="nav-brand">⚙️&nbsp; Autonomous Prototyper</div>
  <a class="nav-cta" href="/app">Launch App &rarr;</a>
</nav>

<!-- HERO -->
<section class="hero">
  <div class="badge fade-up">
    <span class="badge-dot"></span>
    Powered by Gemini 2.5 Flash
  </div>
  <h1 class="hero-title fade-up delay-1">Turn a prompt into<br/>a hardware prototype</h1>
  <p class="hero-sub fade-up delay-2">
    Describe any hardware project in plain English. The multi-agent AI pipeline
    generates CAD files, Arduino firmware, a sourced parts list, and a physics
    simulation — automatically.
  </p>
  <a class="hero-btn fade-up delay-3" href="/app">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
      <polygon points="5 3 19 12 5 21 5 3"/>
    </svg>
    Start Prototyping
  </a>
  <p class="hero-note fade-up delay-3">Free to use &nbsp;·&nbsp; Requires a Google AI API key</p>
</section>

<!-- STATS -->
<div class="stats">
  <div class="stat"><div class="stat-val">5</div><div class="stat-label">AI Agents</div></div>
  <div class="stat"><div class="stat-val">4</div><div class="stat-label">Output formats</div></div>
  <div class="stat"><div class="stat-val">3</div><div class="stat-label">Retry loops</div></div>
  <div class="stat"><div class="stat-val">2.5</div><div class="stat-label">Gemini Flash</div></div>
</div>

<!-- HOW IT WORKS -->
<section class="section">
  <div class="s-eyebrow">How it works</div>
  <h2 class="s-title">Five agents, one pipeline</h2>
  <p class="s-body">Each stage is a specialized AI agent. They run concurrently where possible,
    share a common state graph, and retry automatically when the physics simulation flags a design flaw.</p>

  <div class="steps">
    <div class="step">
      <div class="step-num">Step 01</div>
      <div class="step-icon">🧠</div>
      <div class="step-name">Decompose</div>
      <div class="step-desc">Breaks your prompt into geometry specs, firmware requirements, and a component list.</div>
      <div class="step-line"></div>
    </div>
    <div class="step">
      <div class="step-num">Step 02</div>
      <div class="step-icon">📐</div>
      <div class="step-name">CAD</div>
      <div class="step-desc">Generates parametric OpenSCAD source and compiles it to an STL mesh.</div>
      <div class="step-line"></div>
    </div>
    <div class="step">
      <div class="step-num">Step 03</div>
      <div class="step-icon">⚡</div>
      <div class="step-name">Firmware</div>
      <div class="step-desc">Writes a complete Arduino <code style="font-family:monospace;font-size:11px;color:var(--gold)">.ino</code> sketch with pin mappings and control logic.</div>
      <div class="step-line"></div>
    </div>
    <div class="step">
      <div class="step-num">Step 04</div>
      <div class="step-icon">🛒</div>
      <div class="step-name">Sourcing</div>
      <div class="step-desc">Searches Amazon.ca for each component and returns live prices in CAD.</div>
      <div class="step-line"></div>
    </div>
    <div class="step">
      <div class="step-num">Step 05</div>
      <div class="step-icon">🔬</div>
      <div class="step-name">Simulation</div>
      <div class="step-desc">Parses the STL and checks tilt stability at 15°, 30°, and 45°. Triggers a CAD redesign if it fails.</div>
    </div>
  </div>
</section>

<!-- FEATURES -->
<div class="features">
  <div class="features-inner">
    <div class="s-eyebrow">Features</div>
    <h2 class="s-title">Everything you need to build</h2>
    <div class="feature-grid">
      <div class="feat">
        <div class="feat-icon">🗂️</div>
        <div class="feat-name">Structured State Graph</div>
        <div class="feat-desc">Built on LangGraph — each agent owns its slice of state, enabling safe parallel execution and clean retry loops.</div>
      </div>
      <div class="feat">
        <div class="feat-icon">📦</div>
        <div class="feat-name">Downloadable Artifacts</div>
        <div class="feat-desc">Every run produces a <code style="font-family:monospace;font-size:11px;color:var(--gold)">.scad</code>, <code style="font-family:monospace;font-size:11px;color:var(--gold)">.stl</code>, <code style="font-family:monospace;font-size:11px;color:var(--gold)">.ino</code>, parts JSON, and simulation diagram — ready to download instantly.</div>
      </div>
      <div class="feat">
        <div class="feat-icon">🔁</div>
        <div class="feat-name">Automatic Redesign Loop</div>
        <div class="feat-desc">If the stability check fails, the CAD agent receives the failure reason and regenerates the design — up to 3 times.</div>
      </div>
      <div class="feat">
        <div class="feat-icon">💰</div>
        <div class="feat-name">Live Canadian Pricing</div>
        <div class="feat-desc">The sourcing agent uses Gemini's Google Search grounding to pull real Amazon.ca prices at the time of your run.</div>
      </div>
      <div class="feat">
        <div class="feat-icon">🌊</div>
        <div class="feat-name">Real-time Streaming UI</div>
        <div class="feat-desc">Watch each agent's status update live as the pipeline runs — no polling, no page reloads.</div>
      </div>
      <div class="feat">
        <div class="feat-icon">🛡️</div>
        <div class="feat-name">Physics-verified Output</div>
        <div class="feat-desc">Geometric tilt-stability analysis on the STL mesh ensures the design won't tip before you print it.</div>
      </div>
    </div>
  </div>
</div>

<!-- CODE SNIPPETS -->
<section class="snippets">
  <div class="s-eyebrow">Under the hood</div>
  <h2 class="s-title">What gets generated</h2>
  <div class="snippet-grid">

    <div class="snippet">
      <div class="snippet-head">
        <span class="snippet-title">OpenSCAD CAD</span>
        <span class="snippet-tag">.scad</span>
      </div>
      <div class="snippet-body"><pre><span class="cm">// Auto-generated — Turret base plate</span>
<span class="kw">module</span> <span class="fn">base_plate</span>() {
  <span class="fn">difference</span>() {
    <span class="fn">cube</span>([<span class="num">120</span>, <span class="num">120</span>, <span class="num">8</span>], center=<span class="kw">true</span>);
    <span class="kw">for</span> (pos = [
      [<span class="num">-45</span>,<span class="num">-45</span>,<span class="num">0</span>],[<span class="num">45</span>,<span class="num">-45</span>,<span class="num">0</span>],
      [<span class="num">-45</span>,<span class="num">45</span>,<span class="num">0</span>],[<span class="num">45</span>,<span class="num">45</span>,<span class="num">0</span>]])
      <span class="fn">translate</span>(pos)
        <span class="fn">cylinder</span>(h=<span class="num">10</span>, r=<span class="num">2.2</span>,
                 center=<span class="kw">true</span>, $fn=<span class="num">32</span>);
  }
}
<span class="fn">base_plate</span>();</pre></div>
    </div>

    <div class="snippet">
      <div class="snippet-head">
        <span class="snippet-title">Arduino Firmware</span>
        <span class="snippet-tag">.ino</span>
      </div>
      <div class="snippet-body"><pre><span class="cm">// Auto-generated — Pan-tilt servo control</span>
<span class="kw">#include</span> <span class="str">&lt;Servo.h&gt;</span>

<span class="ty">Servo</span> panServo, tiltServo;
<span class="kw">const int</span> PAN_PIN = <span class="num">9</span>, TILT_PIN = <span class="num">10</span>;
<span class="kw">const int</span> JOY_X = <span class="num">A0</span>, JOY_Y = <span class="num">A1</span>;

<span class="kw">void</span> <span class="fn">setup</span>() {
  panServo.<span class="fn">attach</span>(PAN_PIN);
  tiltServo.<span class="fn">attach</span>(TILT_PIN);
}
<span class="kw">void</span> <span class="fn">loop</span>() {
  panServo.<span class="fn">write</span>(<span class="fn">map</span>(
    <span class="fn">analogRead</span>(JOY_X),<span class="num">0</span>,<span class="num">1023</span>,<span class="num">0</span>,<span class="num">180</span>));
}</pre></div>
    </div>

    <div class="snippet">
      <div class="snippet-head">
        <span class="snippet-title">Parts List</span>
        <span class="snippet-tag">.json</span>
      </div>
      <div class="snippet-body"><pre>[
  {
    <span class="str">"name"</span>: <span class="str">"SG90 Micro Servo"</span>,
    <span class="str">"model"</span>: <span class="str">"Tower Pro SG90"</span>,
    <span class="str">"price_cad"</span>: <span class="num">8.99</span>,
    <span class="str">"qty"</span>: <span class="num">2</span>,
    <span class="str">"supplier"</span>: <span class="str">"Amazon.ca"</span>
  },
  {
    <span class="str">"name"</span>: <span class="str">"Arduino Uno R3"</span>,
    <span class="str">"model"</span>: <span class="str">"A000066"</span>,
    <span class="str">"price_cad"</span>: <span class="num">29.95</span>,
    <span class="str">"qty"</span>: <span class="num">1</span>,
    <span class="str">"supplier"</span>: <span class="str">"Amazon.ca"</span>
  }
]</pre></div>
    </div>

    <div class="snippet">
      <div class="snippet-head">
        <span class="snippet-title">Stability Check</span>
        <span class="snippet-tag">result</span>
      </div>
      <div class="snippet-body"><pre><span class="cm"># Geometric tilt simulation output</span>
{
  <span class="str">"passed"</span>: <span class="kw">true</span>,
  <span class="str">"reason"</span>: <span class="str">"Stable at 15, 30,
             and 45 degree tilt"</span>,
  <span class="str">"footprint_mm"</span>: <span class="str">"120 x 120"</span>,
  <span class="str">"com_offset"</span>: <span class="str">"centred"</span>,
  <span class="str">"screenshot"</span>:
    <span class="str">"outputs/sim_screenshot.png"</span>
}</pre></div>
    </div>

  </div>
</section>

<!-- OUTPUT PREVIEW -->
<section class="section" style="padding-top:0">
  <div class="s-eyebrow">Example output</div>
  <h2 class="s-title">Voice-controlled turret run</h2>
  <div class="preview-grid">

    <div class="preview-card">
      <div class="pc-header">Pipeline Status</div>
      <div class="pc-body">
        <div class="pc-line"><span class="pc-k">🧠 Decompose</span><span class="pc-badge pc-badge-ok">Done</span></div>
        <div class="pc-line"><span class="pc-k">📐 CAD</span><span class="pc-badge pc-badge-ok">Done</span></div>
        <div class="pc-line"><span class="pc-k">⚡ Firmware</span><span class="pc-badge pc-badge-ok">Done</span></div>
        <div class="pc-line"><span class="pc-k">🛒 Sourcing</span><span class="pc-badge pc-badge-ok">Done</span></div>
        <div class="pc-line"><span class="pc-k">🔬 Simulation</span><span class="pc-badge pc-badge-ok">Stable</span></div>
      </div>
    </div>

    <div class="preview-card">
      <div class="pc-header">Geometry Spec</div>
      <div class="pc-body">
        <div class="pc-line"><span class="pc-k">Width</span><span class="pc-v">120 mm</span></div>
        <div class="pc-line"><span class="pc-k">Depth</span><span class="pc-v">120 mm</span></div>
        <div class="pc-line"><span class="pc-k">Height</span><span class="pc-v">180 mm</span></div>
        <div class="pc-line"><span class="pc-k">Moving parts</span><span class="pc-v">Pan · Tilt</span></div>
        <div class="pc-line"><span class="pc-k">Stability</span><span class="pc-v">Wide base</span></div>
      </div>
    </div>

    <div class="preview-card">
      <div class="pc-header">Build Cost</div>
      <div class="pc-body">
        <div class="pc-metric">
          <div class="pc-mval">$62.40</div>
          <div class="pc-msub">CAD · Amazon.ca</div>
        </div>
        <div class="pc-line"><span class="pc-k">SG90 Servo ×2</span><span class="pc-v">$17.98</span></div>
        <div class="pc-line"><span class="pc-k">Arduino Uno</span><span class="pc-v">$29.95</span></div>
        <div class="pc-line"><span class="pc-k">Mic module</span><span class="pc-v">$14.47</span></div>
      </div>
    </div>

    <div class="preview-card">
      <div class="pc-header">Downloads</div>
      <div class="pc-body">
        <div class="pc-line"><span class="pc-k">turret.scad</span><span class="pc-badge pc-badge-ok">Ready</span></div>
        <div class="pc-line"><span class="pc-k">turret.stl</span><span class="pc-badge pc-badge-ok">Ready</span></div>
        <div class="pc-line"><span class="pc-k">firmware.ino</span><span class="pc-badge pc-badge-ok">Ready</span></div>
        <div class="pc-line"><span class="pc-k">parts_list.json</span><span class="pc-badge pc-badge-ok">Ready</span></div>
        <div class="pc-line"><span class="pc-k">sim_screenshot.png</span><span class="pc-badge pc-badge-ok">Ready</span></div>
      </div>
    </div>

  </div>
</section>

<!-- CTA BANNER -->
<section class="cta-banner">
  <h2 class="cta-title">Ready to build something?</h2>
  <p class="cta-sub">Paste your idea, hit run, and have a full prototype spec in minutes.</p>
  <a class="hero-btn" href="/app">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" width="18" height="18">
      <polygon points="5 3 19 12 5 21 5 3"/>
    </svg>
    Open the App
  </a>
</section>

<!-- FOOTER -->
<footer>
  <div class="footer-brand">⚙️  Autonomous Prototyper</div>
  <div class="footer-note">Built with LangGraph · Gemini 2.5 Flash · ReactPy</div>
</footer>

</body>
</html>"""

@fastapi_app.get("/")
async def landing():
    return HTMLResponse(LANDING_HTML)

if __name__ == "__main__":
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000, log_level="info")
