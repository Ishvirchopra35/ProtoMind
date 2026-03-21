import json
from pathlib import Path

from graph.state import PrototyperState
from utils.code_extractor import extract_code_block
from utils.gemini_client import call_flash_with_search

SOURCING_PROMPT = """
You are a hardware procurement specialist sourcing components for a Canadian maker.

Search Amazon.ca for each component below and return the current listed price in
Canadian dollars (CAD). Use your Google Search tool to look up each item on
amazon.ca right now — do not guess or use placeholder prices.

Components needed:
{components}

Rules:
- Supplier is always "Amazon.ca"
- price_cad must be the real current price in CAD you found, never 0 or null
- If a component has multiple options, pick the cheapest that meets the spec
- qty is the number of units needed for one build

Return ONLY a valid JSON array with no markdown, no explanation:
[
  {{
    "name": "component name",
    "model": "specific model or ASIN",
    "price_cad": 12.99,
    "url": "https://www.amazon.ca/dp/...",
    "qty": 1,
    "supplier": "Amazon.ca",
    "description": "one sentence on why this part fits the spec"
  }}
]
"""


def source_parts(state: PrototyperState) -> PrototyperState:
    components = state["decomposed_tasks"].get("components", [])
    errors = list(state.get("errors", []))

    try:
        raw = call_flash_with_search(
            SOURCING_PROMPT.format(components="\n".join(f"- {c}" for c in components))
        )
        clean = extract_code_block(raw, "json")
        if not clean:
            clean = extract_code_block(raw)
        if not clean:
            clean = raw.strip()

        start = clean.find("[")
        end = clean.rfind("]") + 1
        if start != -1 and end > start:
            clean = clean[start:end]

        parts = json.loads(clean)
    except Exception as exc:
        errors.append(f"Sourcing failed: {exc}")
        parts = [
            {
                "name": component,
                "model": "TBD",
                "price_cad": 0.0,
                "url": "https://www.amazon.ca",
                "qty": 1,
                "supplier": "Amazon.ca",
                "description": "Search failed — verify price manually on Amazon.ca.",
            }
            for component in components
        ]

    output_path = Path("outputs/parts_list.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(parts, indent=2))

    return {"parts_list": parts, "errors": errors}
