from dotenv import load_dotenv
load_dotenv()
import os
import json
import time
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types
from google.genai.errors import ClientError

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

# ---------- UI starts here ----------
st.title("AI Ticket Triage Bot")
st.write("Classify support tickets by category and priority using an LLM, with a rule-based safety layer on top.")

tab1, tab2 = st.tabs(["Single Ticket", "Batch (CSV)"])

with tab1:
    ticket_input = st.text_area("Paste a support ticket:")
    if st.button("Classify Ticket"):
        if ticket_input.strip() == "":
            st.warning("Please enter a ticket first.")
        else:
            with st.spinner("Classifying..."):
                result = classify_ticket(ticket_input)
                result = apply_rules(ticket_input, result)
            st.json(result)

with tab2:
    uploaded_file = st.file_uploader("Upload a CSV with a 'ticket_text' column", type="csv")
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        if st.button("Classify All Tickets"):
            progress = st.progress(0)
            results = []
            for i, row in df.iterrows():
                result = classify_ticket(row["ticket_text"])
                result = apply_rules(row["ticket_text"], result)
                results.append(result)
                progress.progress((i + 1) / len(df))
                time.sleep(4)
            results_df = pd.DataFrame(results)
            final_df = pd.concat([df, results_df], axis=1)
            st.dataframe(final_df)
            st.download_button("Download results as CSV", final_df.to_csv(index=False), "classified_tickets.csv")