import os
import logging
from dotenv import load_dotenv
from typing import Optional

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

    # הגדרת המודל (שימוש ב-Flash 2.5 כפי שקיים אצלך)
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        safety_settings=safety_settings,
    )

    # 3. בניית הפרומפט הסופי בעזרת ה-Prompt Builder
    # ה-Builder משלב את ה-system_instructions בתוך ה-focus או כחלק מההוראות
    prompt = build_prompt(action, focus)

    logger.info(f"🚀 Calling Gemini API for Action: {action.name}")

    try:
        response = model.generate_content(prompt)

        if not response or not response.text:
            logger.warning("Gemini returned an empty response")
            raise RuntimeError("Empty response from Gemini")

        return response.text.strip()

    except Exception as e:
        logger.error(f"Error during Gemini API call: {e}")
        raise e


# פונקציית עזר למקרה שצריך קריאה ישירה (תאימות לאחור)
def call_llm(prompt: str) -> str:
    """קריאה ישירה למודל עם פרומפט מוכן"""
    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)
    return response.text.strip()