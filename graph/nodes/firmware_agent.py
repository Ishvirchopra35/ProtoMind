from pathlib import Path

from graph.state import PrototyperState
from utils.code_extractor import extract_code_block
from utils.gemini_client import call_pro

FIRMWARE_PROMPT = """
You are an embedded systems engineer. Write complete, ready-to-flash Arduino C++ firmware.

Firmware specification:
{firmware_spec}

Target microcontroller: {microcontroller}

Rules:
- Include all #include statements for required libraries
- Define all pin constants at the top
- Implement setup() and loop() functions
- Add brief inline comments explaining the control logic
- Handle edge cases (sensor out of range, servo limits)
- Output ONLY the raw .ino code. No markdown fences, no explanation.
"""


def generate_firmware(state: PrototyperState) -> PrototyperState:
    spec = state["decomposed_tasks"].get("firmware_spec", {})
    mcu = spec.get("microcontroller", "Arduino Uno")
    raw = call_pro(
        FIRMWARE_PROMPT.format(firmware_spec=spec, microcontroller=mcu),
        thinking_budget=6000,
    )
    code = (
        extract_code_block(raw, "cpp")
        or extract_code_block(raw, "ino")
        or extract_code_block(raw)
    )

    output_path = Path("outputs/firmware.ino")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(code)

    return {"firmware_code": code}
