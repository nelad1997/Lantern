import os
from typing import Optional

try:
    import google.generativeai as genai
except ImportError:
    genai = None


def call_llm(prompt: str) -> str:
    """
    Send a prompt to the LLM and return the raw text response.

    This function is intentionally thin and contains no business logic.
    It can be swapped or mocked easily.

    Args:
        prompt (str): The prompt to send to the LLM.

    Returns:
        str: The LLM's textual response.
    """
    if genai is None:
        return _mock_response()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    genai.configure(api_key=api_key)

    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)

    return response.text


def _mock_response() -> str:
    """
    Mock response used when Gemini is unavailable.
    Useful for development and debugging.
    """
    return (
        "Option 1: Develop the argument from a theoretical perspective.\n"
        "Option 2: Focus on empirical evidence and case studies.\n"
        "Option 3: Critically examine counterarguments."
    )
