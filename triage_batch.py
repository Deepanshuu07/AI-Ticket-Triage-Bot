from dotenv import load_dotenv
load_dotenv()
import os
import json
import time
import pandas as pd
from google import genai
from google.genai import types
from google.genai.errors import ClientError

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

schema = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": ["Access Issue", "Bug", "Billing", "How-To Question", "Outage", "Other"]
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

def classify_ticket(ticket_text, retries=3):
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=f"Classify this support ticket: {ticket_text}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema
                )
            )
            return json.loads(response.text)
        except ClientError as e:
            if "RESOURCE_EXHAUSTED" in str(e):
                wait = 15 * (attempt + 1)  # back off a bit more each retry
                print(f"Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise  # a different, real error — don't hide it
    raise Exception("Failed after retries")

df = pd.read_csv("sample_tickets.csv")

def apply_rules(ticket_text, classification):
    text_lower = ticket_text.lower()
    
    # Rule 1: hard override — certain keywords always mean urgent, no matter what the model says
    outage_keywords = ["outage", "down", "entire team", "everyone", "all users"]
    if any(keyword in text_lower for keyword in outage_keywords):
        classification["priority"] = "High"
        classification["rule_triggered"] = "outage_keyword_override"
    
    # Rule 2: low confidence — don't trust the model, flag for a human
    elif classification["confidence"] < 0.7:
        classification["needs_human_review"] = True
        classification["rule_triggered"] = "low_confidence"
    
    else:
        classification["rule_triggered"] = "none"
    
    # Make sure both fields always exist, even when no rule fired
    classification.setdefault("needs_human_review", False)
    
    return classification

results = []
for index, row in df.iterrows():
    print(f"Classifying ticket {row['ticket_id']}...")
    result = classify_ticket(row["ticket_text"])
    result = apply_rules(row["ticket_text"], result)   # <-- new line
    results.append(result)
    time.sleep(4)  # stay comfortably under the per-minute limit

results_df = pd.DataFrame(results)
final_df = pd.concat([df, results_df], axis=1)

print(final_df)
final_df.to_csv("classified_tickets.csv", index=False)
print("Saved to classified_tickets.csv")