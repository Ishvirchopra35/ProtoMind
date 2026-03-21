from langgraph.graph import END, StateGraph

from graph.nodes.cad_agent import generate_cad
from graph.nodes.decompose import decompose_prompt
from graph.nodes.firmware_agent import generate_firmware
from graph.nodes.sim_verifier import verify_simulation
from graph.nodes.sourcing_agent import source_parts
from graph.state import PrototyperState

MAX_RETRIES = 3


def route_after_sim(state: PrototyperState) -> str:
    if not state["sim_passed"] and state.get("retry_count", 0) < MAX_RETRIES:
        return "retry_cad"
    return "done"


def increment_retry(state: PrototyperState) -> dict:
    next_attempt = state.get("retry_count", 0) + 1
    reason = state.get("sim_failure_reason", "")
    errors = list(state.get("errors", []))
    if reason:
        errors.append(f"Retry {next_attempt}: {reason}")
    return {
        "retry_count": next_attempt,
        "cad_constraint": reason,
        "current_step": f"retrying_cad_{next_attempt}",
        "errors": errors,
    }


def build_graph():
    graph = StateGraph(PrototyperState)

    graph.add_node("decompose", decompose_prompt)
    graph.add_node("cad", generate_cad)
    graph.add_node("firmware", generate_firmware)
    graph.add_node("sourcing", source_parts)
    graph.add_node("sim_verify", verify_simulation)
    graph.add_node("increment_retry", increment_retry)

    # Sequential execution: one API call at a time to avoid rate limits
    graph.set_entry_point("decompose")
    graph.add_edge("decompose", "cad")
    graph.add_edge("cad", "firmware")
    graph.add_edge("firmware", "sourcing")
    graph.add_edge("sourcing", "sim_verify")
    graph.add_conditional_edges(
        "sim_verify",
        route_after_sim,
        {"retry_cad": "increment_retry", "done": END},
    )
    graph.add_edge("increment_retry", "cad")

    return graph.compile()
