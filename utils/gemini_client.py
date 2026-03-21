import os

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

_MODEL = "gemini-2.5-flash"


def _api_key() -> str:
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable is not set. "
            "Get a key from aistudio.google.com and add it to .env"
        )
    return key


def _configure() -> None:
    genai.configure(api_key=_api_key())


@retry(
    retry=retry_if_exception_type(ResourceExhausted),
    wait=wait_exponential(multiplier=1, min=4, max=30),
    stop=stop_after_attempt(4),
)
def call_pro(prompt: str, thinking_budget: int = 0) -> str:
    """Gemini 2.5 Flash for reasoning-heavy steps."""
    _configure()
    config_kwargs: dict = {"temperature": 0.2}
    if thinking_budget > 0:
        config_kwargs["thinking_config"] = {"thinking_budget": thinking_budget}
    model = genai.GenerativeModel(_MODEL, generation_config=config_kwargs)
    response = model.generate_content(prompt)
    return response.text


@retry(
    retry=retry_if_exception_type(ResourceExhausted),
    wait=wait_exponential(multiplier=1, min=4, max=30),
    stop=stop_after_attempt(4),
)
def call_flash_with_search(prompt: str) -> str:
    """Gemini 2.5 Flash with Google Search grounding for sourcing."""
    _configure()
    try:
        from google.generativeai.types import GoogleSearchRetrieval, Tool

        model = genai.GenerativeModel(
            _MODEL,
            generation_config={"temperature": 0.1},
        )
        tool = Tool(google_search_retrieval=GoogleSearchRetrieval())
        response = model.generate_content(prompt, tools=[tool])
        return response.text
    except Exception:
        fallback_prompt = (
            prompt
            + "\n\nNote: Use your training knowledge for approximate prices. "
            "Still return the exact JSON format requested."
        )
        model = genai.GenerativeModel(
            _MODEL,
            generation_config={"temperature": 0.1},
        )
        response = model.generate_content(fallback_prompt)
        return response.text
