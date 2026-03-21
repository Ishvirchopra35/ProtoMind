import json
from pathlib import Path

from graph.state import PrototyperState
from utils.code_extractor import extract_code_block
from utils.gemini_client import call_flash_with_search

SOURCING_PROMPT = """
You are a hardware procurement specialist. Find the cheapest currently available
components for this build using Google Shopping.

Components needed:
{components}

Search DigiKey, Mouser, Amazon, Adafruit, and SparkFun for the best prices.

Return ONLY a valid JSON array:
[
  {{
    "name": "component name",
    "model": "specific model number",
    "price_usd": 0.00,
    "url": "direct product URL",
    "qty": 1,
    "supplier": "supplier name",
    "description": "one sentence on why this fits the spec"
  }}
]

No markdown, no explanation, just the raw JSON array.
"""


def source_parts(state: PrototyperState) -> PrototyperState:
    components = state["decomposed_tasks"].get("components", [])
    errors = list(state.get("errors", []))

    try:
        raw = call_flash_with_search(
            SOURCING_PROMPT.format(components="\n".join(f"- {c}" for c in components))
        )
        clean = extract_code_block(raw, "json")
        parts = json.loads(clean)
    except Exception as exc:
        errors.append(f"Sourcing failed: {exc}")
        parts = [
            {
                "name": component,
                "model": "TBD",
                "price_usd": 0.0,
                "url": "",
                "qty": 1,
                "supplier": "TBD",
                "description": "Search failed, verify manually.",
            }
            for component in components
        ]

    output_path = Path("outputs/parts_list.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(parts, indent=2))

    return {**state, "parts_list": parts, "errors": errors}
