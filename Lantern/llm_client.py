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
class RateLimiter:
    def __init__(self, cooldown_seconds=7.0):
        self.cooldown = cooldown_seconds
        self.last_call_time = 0

    def wait_if_needed(self):
        now = time.time()
        elapsed = now - self.last_call_time
        if elapsed < self.cooldown:
            wait_time = self.cooldown - elapsed
            logger.warning(f"⏳ Rate Limit: Waiting {wait_time:.1f}s before next call...")
            time.sleep(wait_time)
        self.last_call_time = time.time()

_limiter = RateLimiter(cooldown_seconds=3.0)



def generate_content(action: ActionType, focus: str, system_instructions: str = "") -> str:
    """
    בונה פרומפט מורכב ושולחת אותו ל-Gemini.
    מקבלת: סוג פעולה, טקסט פוקוס, ועקרונות מערכת (Markdown).
    """

    # 1. קבלת מפתח API
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is not set in environment variables")
        raise RuntimeError("GEMINI_API_KEY is not set")

    # 2. הגדרת Gemini
    genai.configure(api_key=api_key)

    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    }

    # הגדרת המודל (שימוש ב-Flash 2.0)
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        safety_settings=safety_settings,
    )

    # 3. בניית הפרומפט הסופי בעזרת ה-Prompt Builder
    prompt = build_prompt(action, focus)

    logger.info(f"🚀 Calling Gemini API for Action: {action.name}")
    
    # Enforce Rate Limit before call
    _limiter.wait_if_needed()

    max_retries = 3
    retry_delay = 2 # seconds

    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)

            if not response or not response.text:
                logger.warning("Gemini returned an empty response")
                raise RuntimeError("Empty response from Gemini")

            return response.text.strip()

        except Exception as e:
            if "429" in str(e) or "ResourceExhausted" in str(e):
                if attempt < max_retries - 1:
                    logger.warning(f"Rate limit hit. Retrying in {retry_delay}s... (Attempt {attempt + 1})")
                    time.sleep(retry_delay)
                    retry_delay *= 2 # Exponential backoff
                    continue
                else:
                    logger.error("Rate limit exceeded consistently. Please wait a minute.")
                    raise RuntimeError("מכסת הקריאות ל-API הסתיימה לבינתיים. אנא המתן דקה ונסה שוב.")
            
            logger.error(f"Error during Gemini API call: {e}")
            raise e


# פונקציית עזר למקרה שצריך קריאה ישירה (תאימות לאחור)
def call_llm(prompt: str) -> str:
    """קריאה ישירה למודל עם פרומפט מוכן"""
    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    
    # Enforce Rate Limit
    _limiter.wait_if_needed()
    
    response = model.generate_content(prompt)
    return response.text.strip()