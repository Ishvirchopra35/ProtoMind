from typing import TypedDict


class PrototyperState(TypedDict):
    user_prompt: str
    decomposed_tasks: dict
    cad_code: str
    stl_path: str
    firmware_code: str
    parts_list: list[dict]
    sim_passed: bool
    sim_screenshot: str
    sim_failure_reason: str
    retry_count: int
    cad_constraint: str
    current_step: str
    errors: list[str]
