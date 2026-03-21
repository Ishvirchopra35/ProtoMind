import os

from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

_MODEL = "gemini-2.5-flash"


def _should_retry(exc: BaseException) -> bool:
    """Retry on rate limits (429) and transient server errors (500/503)."""
    if isinstance(exc, ClientError):
        return getattr(exc, "code", None) in (429, 500, 503)
    if isinstance(exc, ServerError):
        return True
    return False


def _api_key() -> str:
    key = os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable is not set. "
            "Get a key from aistudio.google.com and add it to .env"
        )
    return key


@retry(
    retry=retry_if_exception(_should_retry),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    stop=stop_after_attempt(6),
)
def call_pro(prompt: str, thinking_budget: int = 0) -> str:
    """Gemini 2.5 Flash for reasoning-heavy steps."""
    client = genai.Client(api_key=_api_key())
    config_kwargs: dict = {"temperature": 0.2}
    if thinking_budget > 0:
        config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=thinking_budget)
    response = client.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(**config_kwargs),
    )
    return response.text


@retry(
    retry=retry_if_exception(_should_retry),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    stop=stop_after_attempt(6),
)
def call_flash_with_search(prompt: str) -> str:
    """Gemini 2.5 Flash with Google Search grounding for sourcing."""
    try:
        client = genai.Client(api_key=_api_key())
        response = client.models.generate_content(
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
            + "\n\nIMPORTANT: Google Search is unavailable. Use your training knowledge "
            "to provide realistic retail price estimates in CAD for each component. "
            "Base prices on typical Amazon.ca or Canadian electronics retailer prices. "
            "NEVER use 0, null, or placeholder values — every price_cad must be a "
            "positive number reflecting a real-world market price (e.g. 8.99, 24.95, 12.50). "
            "Still return the exact JSON format requested."
        )
        client = genai.Client(api_key=_api_key())
        response = client.models.generate_content(
            model=_MODEL,
            contents=fallback_prompt,
            config=types.GenerateContentConfig(temperature=0.2),
        )
        return response.text
