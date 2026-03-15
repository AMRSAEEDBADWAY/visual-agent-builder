import os
import google.generativeai as genai

genai.configure(api_key="AIzaSyB5Ed6m4-L1hd4viTqrioMZfktj92x5WUE")

for m in genai.list_models():
    if "generateContent" in m.supported_generation_methods and ("vision" in m.name.lower() or "1.5" in m.name.lower() or "flash" in m.name.lower() or "pro" in m.name.lower()):
        print(m.name)
