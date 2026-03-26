import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))

try:
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content("Say test")
    print("SUCCESS:", response.text)
except Exception as e:
    print("ERROR:")
    print(e)
