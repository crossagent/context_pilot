
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

print(f"SDK Version: {genai.__version__}")

model_name = "models/gemini-embedding-001"
print(f"Testing Model: {model_name}")

try:
    result = genai.embed_content(
        model=model_name,
        content="Hello world"
    )
    embedding = result['embedding']
    print(f"Dimension: {len(embedding)}")
except Exception as e:
    print(f"Error: {e}")

# Also test without 'models/' prefix just in case
model_name_2 = "gemini-embedding-001"
print(f"Testing Model: {model_name_2}")
try:
    result = genai.embed_content(
        model=model_name_2,
        content="Hello world"
    )
    embedding = result['embedding']
    print(f"Dimension: {len(embedding)}")
except Exception as e:
    print(f"Error: {e}")
