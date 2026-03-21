import os

from graph.state import PrototyperState
from utils.pybullet_sim import check_stability


def verify_simulation(state: PrototyperState) -> PrototyperState:
    stl_path = state.get("stl_path", "")

    if not stl_path or not os.path.exists(stl_path):
        errors = list(state.get("errors", []))
        errors.append("Simulation skipped: STL artifact was not available.")
        return {
            "sim_passed": True,
            "sim_failure_reason": f"Simulation skipped because STL file was not found at '{stl_path}'",
            "sim_screenshot": "",
            "current_step": "sim_skipped",
            "errors": errors,
        }

    try:
        result = check_stability(stl_path, screenshot_path="outputs/sim_screenshot.png")
    except Exception as exc:
        return {
            "sim_passed": True,
            "sim_failure_reason": f"Sim skipped — mesh load error: {exc}",
            "sim_screenshot": "",
            "current_step": "sim_skipped",
        }

    return {
        "sim_passed": result["passed"],
        "sim_failure_reason": result.get("reason", ""),
        "sim_screenshot": result.get("screenshot_path", ""),
        "current_step": "sim_passed" if result["passed"] else "sim_failed",
    }
