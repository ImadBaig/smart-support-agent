import os
import json
from pathlib import Path

from dotenv import load_dotenv
import vertexai
from vertexai.language_models import TextEmbeddingModel
from google.cloud import aiplatform

repo_root = Path(__file__).resolve().parent.parent
load_dotenv(repo_root / ".env")

credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if credentials_path:
    credentials_path = Path(credentials_path)
    if not credentials_path.is_absolute():
        credentials_path = repo_root / credentials_path
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_path.resolve())

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
LOCATION = "us-east1"
EMBEDDING_MODEL_NAME = "text-embedding-004"
INDEX_ENDPOINT_RESOURCE_NAME = "projects/411440897339/locations/us-east1/indexEndpoints/3875290304747667456"
DEPLOYED_INDEX_ID = "epc_incidents_deployed"
INCIDENTS_FILE = "../data/historical_incidents.json"

if not PROJECT_ID:
    raise EnvironmentError("GCP_PROJECT_ID is not set. Add it to your .env file.")
if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS is not set. Add it to your .env file.")
if not Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]).exists():
    raise FileNotFoundError(f"Service account JSON file not found: {os.environ['GOOGLE_APPLICATION_CREDENTIALS']}")

print("PROJECT_ID=", PROJECT_ID)
print("CREDENTIALS=", os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
print("LOCATION=", LOCATION)
print("INDEX_ENDPOINT_RESOURCE_NAME=", INDEX_ENDPOINT_RESOURCE_NAME)

vertexai.init(project=PROJECT_ID, location=LOCATION)
aiplatform.init(project=PROJECT_ID, location=LOCATION)

embedding_model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL_NAME)
index_endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=INDEX_ENDPOINT_RESOURCE_NAME)

with open(INCIDENTS_FILE, "r") as f:
    incidents_lookup = {i["incident_id"]: i for i in json.load(f)}

query_text = "App keeps crashing when I try to upload photos on Android"
print("Embedding text:", query_text)
query_embedding = embedding_model.get_embeddings([query_text])[0].values
print("Got embedding length", len(query_embedding))

response = index_endpoint.find_neighbors(deployed_index_id=DEPLOYED_INDEX_ID, queries=[query_embedding], num_neighbors=3)
print("Response type:", type(response))
print(response)
