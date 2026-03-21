import json

from graph.state import PrototyperState
from utils.code_extractor import extract_code_block
from utils.gemini_client import call_pro

DECOMPOSE_PROMPT = """
You are a hardware engineering planner. A user wants to build a physical device.
Break their request into a precise build specification for downstream engineering agents.

User request: {user_prompt}

Return ONLY a valid JSON object with exactly these keys:
{{
  "goal": "one sentence description of what the device does",
  "geometry_spec": {{
    "description": "plain English description of the physical structure",
    "base_dimensions_mm": {{"width": 0, "depth": 0, "height": 0}},
    "moving_parts": ["list of moving components"],
    "mounting_points": ["list of attachment points"],
    "stability_requirement": "must remain stable under X degrees tilt"
  }},
  "firmware_spec": {{
    "microcontroller": "Arduino Uno | Nano | Mega",
    "inputs": ["list of sensors/inputs"],
    "outputs": ["list of actuators/outputs"],
    "control_logic": "plain English description of the control loop",
    "libraries_needed": ["list of Arduino libraries"]
  }},
  "components": ["list of physical components needed, be specific with model numbers where possible"]
}}

No markdown, no explanation, just the raw JSON object.
"""


def decompose_prompt(state: PrototyperState) -> PrototyperState:
    raw = call_pro(
        DECOMPOSE_PROMPT.format(user_prompt=state["user_prompt"]),
        thinking_budget=4000,
    )
    clean = extract_code_block(raw, "json")
    tasks = json.loads(clean)
    return {**state, "decomposed_tasks": tasks, "current_step": "decomposed"}
