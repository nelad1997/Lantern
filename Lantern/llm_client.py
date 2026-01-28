import os
import logging
from dotenv import load_dotenv
from typing import Optional
import time

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# ייבוא הגדרות הפרויקט
from definitions import ActionType
from prompt_builder import build_prompt

# טעינת משתני סביבה
load_dotenv(override=True)

# הגדרת לוגר
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Rate Limiter ---
import threading

class RateLimiter:
    def __init__(self, cooldown_seconds=5.0):
        self.cooldown = cooldown_seconds
        self.last_call_time = 0
        self.lock = threading.Lock()

    def wait_if_needed(self):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_call_time
            if elapsed < self.cooldown:
                wait_time = self.cooldown - elapsed
                logger.warning(f"⏳ Rate Limit: Waiting {wait_time:.1f}s before next call...")
                time.sleep(wait_time)
            self.last_call_time = time.time()

_limiter = RateLimiter(cooldown_seconds=8.0)



def call_llm(prompt: str) -> str:
    """
    Robust call to Gemini API with retries, rate limiting, and error handling.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is not set in environment variables")
        raise RuntimeError("GEMINI_API_KEY is not set")

    # Safe logging to verify the key being used
    key_display = f"{api_key[:4]}...{api_key[-4:]}"
    logger.info(f"🔑 Using API Key: {key_display}")

    genai.configure(api_key=api_key)

    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    }

    # model: Gemini 2.0 Flash (Stable and fast)
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        safety_settings=safety_settings,
    )

    # Enforce Rate Limit
    _limiter.wait_if_needed()

    max_retries = 3
    retry_delay = 2 # seconds

    for attempt in range(max_retries):
        try:
            logger.info(f"🚀 Calling Gemini API (Attempt {attempt + 1})...")
            response = model.generate_content(prompt)

            if not response or not hasattr(response, 'text') or not response.text:
                # Check for blocked content
                if hasattr(response, 'candidates') and response.candidates:
                    finish_reason = response.candidates[0].finish_reason
                    if finish_reason == 3: # SAFETY
                         raise RuntimeError("The request was blocked by safety filters. Please try rephrasing.")
                
                logger.warning(f"Gemini returned an empty or blocked response. Reason: {getattr(response, 'candidates', [None])[0]}")
                raise RuntimeError("Empty response from Gemini")

            return response.text.strip()

        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "ResourceExhausted" in err_msg or "Quota" in err_msg:
                if attempt < max_retries - 1:
                    logger.warning(f"Rate limit hit. Retrying in {retry_delay}s... (Attempt {attempt + 1})")
                    time.sleep(retry_delay)
                    retry_delay *= 4 # Aggressive backoff for quota
                    continue
                else:
                    logger.error("Rate limit exceeded consistently.")
                    raise RuntimeError("מכסת הקריאות (Quota/TPM) הסתיימה לבינתיים. אנא המתן כדקה ונסה שוב.")
            
            if "400" in err_msg and "model" in err_msg.lower():
                 logger.error(f"Invalid model name or configuration: {e}")
                 raise RuntimeError("שגיאת תצורה במודל הבינה המלאכותית (Invalid Model).")

            logger.error(f"Error during Gemini API call: {e}")
            raise e

# Legacy compatibility
def generate_content(action: ActionType, focus: str, system_instructions: str = "") -> str:
    """Wrapper for call_llm using the old signature if needed."""
    from prompt_builder import build_prompt
    prompt = build_prompt(action, focus)
    return call_llm(prompt)
