import re


def extract_code_block(text: str, language: str = "") -> str:
    """
    Extract code from markdown fences.
    Tries a language-specific fence first, then any fence, then returns raw text.
    """
    if language:
        pattern = rf"```{language}\s*\n(.*?)```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()

    pattern = r"```(?:\w+)?\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()

    return text.strip()
