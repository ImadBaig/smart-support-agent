
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

TOKEN_FILE = "../token.json"

def get_credentials():
    return Credentials.from_authorized_user_file(TOKEN_FILE)


def get_drive_doc(keyword: str) -> str:
    """Searches Drive for a document whose name contains the keyword, and returns its text content."""
    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    results = service.files().list(
        q=f"name contains '{keyword}'",
        fields="files(id, name, mimeType)",
    ).execute()

    files = results.get("files", [])
    if not files:
        return f"No document found matching '{keyword}'."

    file = files[0]
    content = service.files().export(fileId=file["id"], mimeType="text/plain").execute()
    return content.decode("utf-8")


if __name__ == "__main__":
    result = get_drive_doc("Runbook")
    print(result)

