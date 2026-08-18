from dotenv import load_dotenv
load_dotenv()
import os
from google import genai

# Reads the key from the environment variable you set in step 4
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents="A customer wrote: 'My login isn't working and I have a demo in 10 minutes!' What category and priority should this support ticket get?"
)

print(response.text)