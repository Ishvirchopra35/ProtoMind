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

FIX_PROMPT = """
The following OpenSCAD code produced a syntax error when compiled:

--- CODE ---
{code}

--- ERROR ---
{error}

Fix ALL syntax errors and return ONLY the corrected raw OpenSCAD code.
No markdown fences, no explanation.
"""


def _try_compile(code: str) -> tuple[str, str]:
    """Returns (stl_path, error). One of them will be empty."""
    try:
        stl_path = compile_scad_to_stl(code, "outputs/turret.stl")
        return stl_path, ""
    except RuntimeError as exc:
        return "", str(exc)


def generate_cad(state: PrototyperState) -> PrototyperState:
    spec = state["decomposed_tasks"].get("geometry_spec", {})
    constraint = state.get("cad_constraint", "") or "none"

    raw = call_pro(CAD_PROMPT.format(geometry_spec=spec, cad_constraint=constraint))
    code = extract_code_block(raw, "openscad") or extract_code_block(raw)

    stl_path, err = _try_compile(code)

    # If compilation failed, ask Gemini to fix the syntax error (one retry)
    if err:
        fix_raw = call_pro(FIX_PROMPT.format(code=code, error=err))
        code = extract_code_block(fix_raw, "openscad") or extract_code_block(fix_raw)
        stl_path, _ = _try_compile(code)
        # If still failing, stl_path stays empty — pipeline continues without STL

    return {"cad_code": code, "stl_path": stl_path}
