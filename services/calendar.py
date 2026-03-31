# services/calendar.py
# Google Calendar OAuth + service builder.
# Run standalone:  python -m services.calendar

from __future__ import print_function
import os
import pickle
from datetime import datetime, timezone

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

SCOPES = ["https://www.googleapis.com/auth/calendar"]
_TOKEN_PATH       = "token.pickle"
_CREDENTIALS_PATH = "credentials.json"


def get_calendar_service():
    """Return an authenticated Google Calendar service object."""
    creds = None
    if os.path.exists(_TOKEN_PATH):
        with open(_TOKEN_PATH, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        try:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(_CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
        except RefreshError:
            if os.path.exists(_TOKEN_PATH):
                os.remove(_TOKEN_PATH)
            flow = InstalledAppFlow.from_client_secrets_file(_CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(_TOKEN_PATH, "wb") as f:
            pickle.dump(creds, f)

    return build("calendar", "v3", credentials=creds)


def list_upcoming_events(service, max_results: int = 10) -> list:
    now = datetime.now(timezone.utc).isoformat()
    result = service.events().list(
        calendarId="primary", timeMin=now,
        maxResults=max_results, singleEvents=True,
        orderBy="startTime",
    ).execute()
    return result.get("items", [])


if __name__ == "__main__":
    svc    = get_calendar_service()
    events = list_upcoming_events(svc)
    if not events:
        print("No upcoming events.")
    else:
        for ev in events:
            start = ev["start"].get("dateTime", ev["start"].get("date"))
            print(f"{start}  —  {ev.get('summary')}")
