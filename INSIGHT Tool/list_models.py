import os
import google.generativeai as genai
from config import Config

api_key = os.getenv('GEMINI_API_KEY') or Config.GEMINI_API_KEY

if not api_key:
    print("No API Key found!")
else:
    genai.configure(api_key=api_key)
    try:
        with open("models_utf8.txt", "w", encoding="utf-8") as f:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    f.write(f"{m.name}\n")
                    print(f"- {m.name}")
    except Exception as e:
        print(f"Error listing models: {e}")
