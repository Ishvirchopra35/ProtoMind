import os

from google import genai
from google.genai import types
from google.api_core.exceptions import ResourceExhausted
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

_MODEL = "gemini-2.5-flash"


def _client() -> genai.Client:
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable is not set. "
            "Get a key from aistudio.google.com and add it to .env"
        )
    return genai.Client(api_key=key)


@retry(
    retry=retry_if_exception_type(ResourceExhausted),
    wait=wait_exponential(multiplier=1, min=4, max=30),
    stop=stop_after_attempt(4),
)
def call_pro(prompt: str, thinking_budget: int = 0) -> str:
    """Gemini 2.5 Flash for reasoning-heavy steps."""
    config_kwargs: dict = {"temperature": 0.2}
    if thinking_budget > 0:
        config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=thinking_budget)
    response = _client().models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(**config_kwargs),
    )
    return response.text


@retry(
    retry=retry_if_exception_type(ResourceExhausted),
    wait=wait_exponential(multiplier=1, min=4, max=30),
    stop=stop_after_attempt(4),
)
def call_flash_with_search(prompt: str) -> str:
    """Gemini 2.5 Flash with Google Search grounding for sourcing."""
    try:
        response = _client().models.generate_content(
            model=_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.1,
            ),
        )
        return response.text
    except Exception:
        fallback_prompt = (
            prompt
            + "\n\nNote: Use your training knowledge for approximate prices. "
            "Still return the exact JSON format requested."
        )
        response = _client().models.generate_content(
            model=_MODEL,
            contents=fallback_prompt,
            config=types.GenerateContentConfig(temperature=0.1),
        )
        return response.text
