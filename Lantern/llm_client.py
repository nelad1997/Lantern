import os
import logging
from dotenv import load_dotenv

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Load environment variables
load_dotenv()

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def call_llm(prompt: str) -> str:
    """
    Sends a prompt to Google Gemini and returns the response text.
    Raises clear errors if something fails.
    """

    # 1. Get API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    # 2. Configure Gemini
    genai.configure(api_key=api_key)

    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    }

    # ✅ מודל תקין
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        safety_settings=safety_settings,
    )

    logger.info("🔥 Calling Gemini API")

    response = model.generate_content(prompt)

    if not response or not response.text:
        raise RuntimeError("Empty response from Gemini")

    return response.text.strip()
