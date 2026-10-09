import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
 
# Load environment variables from .env
load_dotenv()

# Initialize the Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Generate the response
response = client.models.generate_content(
    model="gemini-1.5-flash",
    contents="what is coding",
    config=types.GenerateContentConfig(
        system_instruction="You are a virtual assistant named alfred skilled in general tasks like Alexa and Google Cloud"
    )
)

print(response.text)