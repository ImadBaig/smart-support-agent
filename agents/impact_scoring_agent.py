import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.cloud import firestore

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
LOCATION = os.getenv("GCP_LOCATION", "us-east1")
DATABASE_ID = os.getenv("FIRESTORE_DATABASE_ID", "ebc-firestone")
MODEL_NAME = "gemini-2.5-flash"

SIGNIFICANCE_THRESHOLD = 60  # score at or above this is escalation-worthy

SCORING_PROMPT_TEMPLATE = """
You are a business impact analyst at an enterprise software company.

A cluster of {ticket_count} customer support tickets has been grouped together because
they describe the same underlying problem:

Cluster summary: {summary}
Individual tickets:
{ticket_list}

Score the business impact of this problem on a scale of 0-100, and classify its severity.

Respond with ONLY a valid JSON object in this exact format:
{{
  "impact_score": <integer 0-100>,
  "severity": "Low" | "Medium" | "High" | "Critical",
  "rationale": "one or two sentences explaining the score"
}}
"""

REFLECTION_PROMPT_TEMPLATE = """
You previously scored a cluster of support tickets as follows:

Impact score: {impact_score}
Severity: {severity}
Rationale: {rationale}

Ticket count in this cluster: {ticket_count}

Review this score against this rubric:
- Low (0-30): isolated, minor inconvenience, few tickets
- Medium (31-60): moderate inconvenience, noticeable pattern
- High (61-85): significant business impact, many affected users, urgent
- Critical (86-100): severe, widespread, or revenue/trust threatening

Is the severity label consistent with the numeric score under this rubric?
Respond with ONLY a valid JSON object:
{{
  "consistent": true | false,
  "corrected_severity": "Low" | "Medium" | "High" | "Critical"
}}
"""

# Old SDK: vertexai.init(project=PROJECT_ID, location=LOCATION) + GenerativeModel(MODEL_NAME)
# New SDK: same Vertex AI backend (auth via project ID + ADC, no API key needed),
# just called through the updated google-genai client.
client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
db = firestore.Client(project=PROJECT_ID, database=DATABASE_ID)


def score_cluster(cluster: dict, ticket_texts: list[str]) -> dict:
    ticket_list = "\n".join(f"- {t}" for t in ticket_texts)
    prompt = SCORING_PROMPT_TEMPLATE.format(
        ticket_count=cluster["ticket_count"],
        summary=cluster["summary"],
        ticket_list=ticket_list,
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    result = json.loads(response.text)

    # Self-reflection pass: check the score against a rubric before finalizing
    reflection_prompt = REFLECTION_PROMPT_TEMPLATE.format(
        impact_score=result["impact_score"],
        severity=result["severity"],
        rationale=result["rationale"],
        ticket_count=cluster["ticket_count"],
    )
    reflection_response = client.models.generate_content(
        model=MODEL_NAME,
        contents=reflection_prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    reflection_result = json.loads(reflection_response.text)

    if not reflection_result["consistent"]:
        result["severity"] = reflection_result["corrected_severity"]
        result["rationale"] += " (Severity adjusted after self-review for rubric consistency.)"

    return result


def score_cluster_by_id(cluster_id: str) -> dict:
    cluster_doc = db.collection("clusters").document(cluster_id).get()
    cluster = cluster_doc.to_dict()

    ticket_texts = []
    for ticket_id in cluster["ticket_ids"]:
        ticket_doc = db.collection("tickets").document(ticket_id).get()
        ticket_data = ticket_doc.to_dict() or {}
        ticket_text = ticket_data.get("raw_text") or ticket_data.get("summary")
        if not ticket_text:
            raise KeyError(
                f"Ticket {ticket_id} has neither 'raw_text' nor 'summary'"
            )
        ticket_texts.append(ticket_text)

    result = score_cluster(cluster, ticket_texts)

    db.collection("clusters").document(cluster_id).update({
        "impact_score": result["impact_score"],
        "severity": result["severity"],
        "scoring_rationale": result["rationale"],
    })

    return result


if __name__ == "__main__":
    all_clusters = db.collection("clusters").stream()
    for doc in all_clusters:
        cluster_id = doc.id
        result = score_cluster_by_id(cluster_id)
        print(f"{cluster_id}: score={result['impact_score']} severity={result['severity']}")
        print(f"  rationale: {result['rationale']}\n")