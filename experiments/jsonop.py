from dotenv import load_dotenv
load_dotenv()
import os
import json
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

ticket_text = "My login isn't working and I have a demo in 10 minutes!"

response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents=f"Classify this support ticket: {ticket_text}",
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["Access Issue", "Bug", "How-To Question", "Outage", "Other"]
                },
                "priority": {
                    "type": "string",
                    "enum": ["Low", "Medium", "High"]
                },
                "confidence": {"type": "number"},
                "reasoning": {"type": "string"}
            },
            "required": ["category", "priority", "confidence"]
        }
    )
)

data = json.loads(response.text)

print(data["category"])    # Access Issue
print(data["priority"])    # High
print(data["confidence"])  # 0.95