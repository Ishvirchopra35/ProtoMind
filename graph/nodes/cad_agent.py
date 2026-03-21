import time

from graph.state import PrototyperState
from utils.code_extractor import extract_code_block
from utils.gemini_client import call_pro
from utils.openscad_runner import compile_scad_to_stl

CAD_PROMPT = """
You are an expert OpenSCAD programmer. Generate valid OpenSCAD code for this hardware spec.

Geometry specification:
{geometry_spec}

Additional constraint (if any): {cad_constraint}

Rules:
- All dimensions in millimeters
- Use parametric variables at the top (e.g. base_w = 80;)
- Include a module for each major component
- Call all modules at the bottom to render the full assembly
- Ensure base footprint is wide enough for stability: minimum 80mm x 60mm
- Output ONLY the raw OpenSCAD code. No markdown fences, no explanation.
"""


def generate_cad(state: PrototyperState) -> PrototyperState:
    time.sleep(2)   # stagger parallel agent API calls
    spec = state["decomposed_tasks"].get("geometry_spec", {})
    constraint = state.get("cad_constraint", "") or "none"
    raw = call_pro(
        CAD_PROMPT.format(geometry_spec=spec, cad_constraint=constraint),
        thinking_budget=8000,
    )
    code = extract_code_block(raw, "openscad") or extract_code_block(raw)
    stl_path = compile_scad_to_stl(code, "outputs/turret.stl")
    return {"cad_code": code, "stl_path": stl_path}
