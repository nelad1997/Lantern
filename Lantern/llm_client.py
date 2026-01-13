import os
import logging

# Load environment variables (for local development)
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    load_dotenv = None

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the official Google Generative AI library
try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError:
    genai = None
    HarmCategory = None
    HarmBlockThreshold = None


def call_llm(prompt: str) -> str:
    """
    Sends a prompt to Google Gemini via the official library.
    """
    # 1. Check if the library is installed
    if genai is None:
        logger.warning("google-generativeai library not installed. Using mock response.")
        return _mock_response()

    # 2. Retrieve the API Key (from .env or Cloud Secrets)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
                api_key = st.secrets["GEMINI_API_KEY"]
        except:
            pass

    if not api_key:
        logger.error("GEMINI_API_KEY is missing.")
        return "Error: GEMINI_API_KEY is not set."

    try:
        # 3. Configure the model
        genai.configure(api_key=api_key)

        # Safety settings (configured to prevent unnecessary blocking)
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        }

        # Create the model - using the official name for your key
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            safety_settings=safety_settings
        )

        # 4. Send the request
        response = model.generate_content(prompt)

        # 5. Validate the response
        if response.prompt_feedback and response.prompt_feedback.block_reason:
            return f"Error: Blocked by safety filters. Reason: {response.prompt_feedback.block_reason}"

        return response.text

    except Exception as e:
        logger.error(f"Failed to call Gemini API: {e}")
        return f"System Error: {str(e)}"


def _mock_response() -> str:
    return "Option 1: [Mock] Idea A\nOption 2: [Mock] Idea B"