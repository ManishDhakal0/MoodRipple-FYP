from __future__ import print_function
import os
import pickle
from datetime import datetime, timezone, timedelta
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        try:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
        except RefreshError:
            if os.path.exists('token.pickle'):
                os.remove('token.pickle')
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('calendar', 'v3', credentials=creds)
    return service

def list_upcoming_events(service, max_results=10):
    now = datetime.now(timezone.utc).isoformat()
    events_result = service.events().list(
        calendarId='primary', timeMin=now,
        maxResults=max_results, singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])
    if not events:
        print("No upcoming events.")
    else:
        print(f"Upcoming {len(events)} events:")
        for i, event in enumerate(events, start=1):
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(f"{i}. {start} - {event.get('summary')}")
    return events

def add_event_interactive(service):
    print("\nAdd a new event:")
    summary = input("Event Title: ")
    description = input("Description: ")
    start_input = input("Start Time (YYYY-MM-DD HH:MM, 24h, local time): ")
    end_input = input("End Time (YYYY-MM-DD HH:MM, 24h, local time): ")
    timezone_str = input("Timezone (default Asia/Kathmandu): ") or "Asia/Kathmandu"
    location = input("Location (optional): ") or None

    # parse input
    start = datetime.strptime(start_input, "%Y-%m-%d %H:%M")
    end = datetime.strptime(end_input, "%Y-%m-%d %H:%M")

    event = {
        'summary': summary,
        'description': description,
        'start': {'dateTime': start.isoformat(), 'timeZone': timezone_str},
        'end': {'dateTime': end.isoformat(), 'timeZone': timezone_str},
    }
    if location:
        event['location'] = location

    created_event = service.events().insert(calendarId='primary', body=event).execute()
    print("Event created! View here:", created_event.get('htmlLink'))

if __name__ == '__main__':
    service = get_calendar_service()
    list_upcoming_events(service)
    choice = input("\nDo you want to add a new event? (y/n): ").strip().lower()
    if choice == 'y':
        add_event_interactive(service)
    else:
        print("No new event added.")
