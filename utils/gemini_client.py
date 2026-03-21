import os

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


def _configure_genai() -> None:
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set.")
    genai.configure(api_key=api_key)


@retry(
    retry=retry_if_exception_type(ResourceExhausted),
    wait=wait_exponential(multiplier=1, min=4, max=30),
    stop=stop_after_attempt(4),
)
def call_pro(prompt: str, thinking_budget: int = 0) -> str:
    """Gemini 2.5 Pro for reasoning-heavy steps."""
    _configure_genai()
    config: dict = {"temperature": 0.2}
    if thinking_budget > 0:
        config["thinking_config"] = {"thinking_budget": thinking_budget}
    model = genai.GenerativeModel("gemini-2.5-pro", generation_config=config)
    response = model.generate_content(prompt)
    return response.text


@retry(
    retry=retry_if_exception_type(ResourceExhausted),
    wait=wait_exponential(multiplier=1, min=4, max=30),
    stop=stop_after_attempt(4),
)
def call_flash_with_search(prompt: str) -> str:
    """Gemini 2.0 Flash with Google Search grounding for sourcing."""
    _configure_genai()
    from google.generativeai.types import GoogleSearchRetrieval, Tool

    model = genai.GenerativeModel("gemini-2.0-flash")
    tool = Tool(google_search_retrieval=GoogleSearchRetrieval())
    response = model.generate_content(prompt, tools=[tool])
    return response.text
