import json
import time
from pathlib import Path

from graph.state import PrototyperState
from utils.code_extractor import extract_code_block
from utils.gemini_client import call_flash_with_search, call_pro

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

PRICE_ESTIMATE_PROMPT = """
You are a hardware pricing expert. Provide realistic Canadian retail price estimates
for these electronics/maker components as sold on Amazon.ca.

Components:
{components}

Use your knowledge of typical Canadian market prices. Be accurate — these are
common maker/hobbyist components with well-known price ranges.

CRITICAL rules:
- price_cad must be a positive decimal (e.g. 8.99, 24.95) — NEVER 0 or null
- Use realistic prices: Arduino Uno ~$29, SG90 servo ~$8, HC-SR04 ~$7, etc.
- qty is the number needed for one build (usually 1–4)
- Supplier is "Amazon.ca"

Return ONLY a valid JSON array, no markdown, no explanation:
[
  {{
    "name": "component name",
    "model": "specific model",
    "price_cad": 12.99,
    "url": "https://www.amazon.ca",
    "qty": 1,
    "supplier": "Amazon.ca",
    "description": "one sentence on why this part fits the spec"
  }}
]
"""


def _parse_parts(raw: str) -> list:
    clean = extract_code_block(raw, "json")
    if not clean:
        clean = extract_code_block(raw)
    if not clean:
        clean = raw.strip()
    start = clean.find("[")
    end = clean.rfind("]") + 1
    if start != -1 and end > start:
        clean = clean[start:end]
    return json.loads(clean)


def _has_real_prices(parts: list) -> bool:
    """Return True if at least half the parts have a non-zero price."""
    if not parts:
        return False
    priced = sum(1 for p in parts if float(p.get("price_cad", 0) or 0) > 0)
    return priced >= len(parts) / 2


def source_parts(state: PrototyperState) -> PrototyperState:
    time.sleep(14)  # stagger parallel agent API calls
    components = state["decomposed_tasks"].get("components", [])
    errors = list(state.get("errors", []))
    component_str = "\n".join(f"- {c}" for c in components)

    parts = []

    # Attempt 1: search-grounded call
    try:
        raw = call_flash_with_search(SOURCING_PROMPT.format(components=component_str))
        parts = _parse_parts(raw)
    except Exception as exc:
        errors.append(f"Sourcing (search) failed: {exc}")

    # Attempt 2: if prices came back as zero, retry with a dedicated estimation prompt
    if not _has_real_prices(parts):
        try:
            raw2 = call_pro(PRICE_ESTIMATE_PROMPT.format(components=component_str))
            parts2 = _parse_parts(raw2)
            if _has_real_prices(parts2):
                parts = parts2
        except Exception as exc:
            errors.append(f"Sourcing (estimate fallback) failed: {exc}")

    # Last resort: structural fallback so the UI always has something to show
    if not parts:
        parts = [
            {
                "name": c,
                "model": "TBD",
                "price_cad": 0.0,
                "url": "https://www.amazon.ca",
                "qty": 1,
                "supplier": "Amazon.ca",
                "description": "Could not retrieve price — check Amazon.ca manually.",
            }
            for c in components
        ]

    output_path = Path("outputs/parts_list.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(parts, indent=2))

    return {"parts_list": parts, "errors": errors}
