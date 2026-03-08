"""
setup_youtube_auth.py
One-time script to obtain a YouTube OAuth2 refresh token.

Run this locally (not in CI) to generate the credentials needed for
headless/automated uploads:

  python scripts/setup_youtube_auth.py

The script will open a browser window asking you to authorise the app.
After authorisation it prints the values to add as GitHub Secrets:
  YOUTUBE_CLIENT_ID
  YOUTUBE_CLIENT_SECRET
  YOUTUBE_REFRESH_TOKEN

Prerequisites:
  1. Go to https://console.cloud.google.com/
  2. Create a project and enable the "YouTube Data API v3"
  3. Create OAuth2 credentials (Desktop app type)
  4. Download the client_secrets.json to this directory
  5. Run this script: python scripts/setup_youtube_auth.py
"""

import json
import os
import sys

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("ERROR: google-auth-oauthlib is not installed.")
    print("Run:  pip install google-auth-oauthlib")
    sys.exit(1)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
SECRETS_FILE = os.path.join(os.path.dirname(__file__), "client_secrets.json")


def main():
    if not os.path.exists(SECRETS_FILE):
        print(f"ERROR: {SECRETS_FILE} not found.")
        print(
            "Download your OAuth2 client secrets from "
            "https://console.cloud.google.com/ and save them as "
            f"{SECRETS_FILE}"
        )
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(SECRETS_FILE, SCOPES)
    credentials = flow.run_local_server(port=0, prompt="consent")

    with open(SECRETS_FILE) as f:
        secrets = json.load(f)

    installed = secrets.get("installed") or secrets.get("web", {})
    client_id = installed.get("client_id") or credentials.client_id
    client_secret = installed.get("client_secret") or credentials.client_secret

    print("\n" + "═" * 60)
    print("Add these values as GitHub repository secrets:")
    print("═" * 60)
    print(f"YOUTUBE_CLIENT_ID     = {client_id}")
    print(f"YOUTUBE_CLIENT_SECRET = {client_secret}")
    print(f"YOUTUBE_REFRESH_TOKEN = {credentials.refresh_token}")
    print("═" * 60)
    print(
        "\nAlso add your xAI API key:\n"
        "  XAI_API_KEY = <your key from https://console.x.ai/>"
    )


if __name__ == "__main__":
    main()
