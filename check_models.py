import os
from dotenv import load_dotenv
import google.generativeai as genai

# טעינת המפתח
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: API Key not found in .env file!")
else:
    print(f"API Key found: {api_key[:5]}...")  # מדפיס רק את ההתחלה לבדיקה

    try:
        genai.configure(api_key=api_key)

        print("\n--- Available Models for your Key ---")
        found_any = False
        # בקשה מהשרת לקבל את רשימת המודלים
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
                found_any = True

        if not found_any:
            print("No models found that support 'generateContent'.")

    except Exception as e:
        print(f"\nError connecting to Google: {e}")