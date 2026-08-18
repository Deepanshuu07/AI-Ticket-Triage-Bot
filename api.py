from dotenv import load_dotenv
load_dotenv()
import os
import json
import time
from flask import Flask, request, jsonify
from google import genai
from google.genai import types
from google.genai.errors import ClientError

app = Flask(__name__)
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

schema = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": ["Access Issue", "Bug", "How-To Question", "Outage", "Billing", "Other"]
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
                time.sleep(15 * (attempt + 1))
            else:
                raise
    raise Exception("Failed after retries")

def apply_rules(ticket_text, classification):
    text_lower = ticket_text.lower()
    outage_keywords = ["outage", "down", "entire team", "everyone", "all users"]
    if any(keyword in text_lower for keyword in outage_keywords):
        classification["priority"] = "High"
        classification["rule_triggered"] = "outage_keyword_override"
    elif classification["confidence"] < 0.7:
        classification["needs_human_review"] = True
        classification["rule_triggered"] = "low_confidence"
    else:
        classification["rule_triggered"] = "none"
    classification.setdefault("needs_human_review", False)
    return classification

@app.route("/classify", methods=["POST"])
def classify():
    data = request.get_json()
    ticket_text = data.get("ticket_text", "")
    if not ticket_text.strip():
        return jsonify({"error": "ticket_text is required"}), 400
    result = classify_ticket(ticket_text)
    result = apply_rules(ticket_text, result)
    return jsonify(result)

if __name__ == "__main__":
    app.run(port=5000)