import os
from pathlib import Path
from dotenv import load_dotenv

repo_root = Path(__file__).resolve().parent.parent
load_dotenv(repo_root / ".env")

print('GCP_PROJECT_ID=', os.getenv('GCP_PROJECT_ID'))
print('GOOGLE_APPLICATION_CREDENTIALS=', os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))

from google.cloud.aiplatform_v1beta1.services.match_service import MatchServiceClient

print('MatchServiceClient signature:')
print(MatchServiceClient.__init__)
print('Available transports:')
print(MatchServiceClient._transport_registry)

for transport in ['grpc', 'grpc_asyncio', 'rest']:
    try:
        client = MatchServiceClient(transport=transport)
        print(f'Transport {transport} works')
    except Exception as exc:
        print(f'Transport {transport} failed: {exc}')
