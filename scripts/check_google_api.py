#!/usr/bin/env python3
"""
Prüft die Google Cloud / Sheets API Einrichtung.
Führt keine sensiblen Daten in Logs aus.
"""

import json
import sys
from pathlib import Path

# Projekt-Root
sys.path.insert(0, str(Path(__file__).parent))

def check_credentials_file():
    """Prüft ob credentials.json existiert und gültige Struktur hat."""
    path = Path("credentials.json")
    if not path.exists():
        print("❌ credentials.json nicht gefunden (im Projektordner ablegen)")
        return False
    
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ credentials.json ist kein gültiges JSON: {e}")
        return False
    
    # Desktop-OAuth hat "installed", Web-OAuth hat "web"
    if "installed" not in data and "web" not in data:
        print('❌ credentials.json braucht "installed" (Desktop) oder "web"')
        return False
    
    key = "installed" if "installed" in data else "web"
    client = data[key]
    
    if "client_id" not in client or "client_secret" not in client:
        print("❌ credentials.json: client_id oder client_secret fehlt")
        return False
    
    print("✅ credentials.json gefunden und Struktur OK (Desktop-OAuth)")
    return True

def check_sheets_auth_and_access():
    """Prüft Authentifizierung und optional Sheet-Zugriff."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        import os
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
    except ImportError as e:
        print(f"❌ Fehlende Bibliothek: {e}")
        print("   Führe aus: pip install -r requirements.txt")
        return False
    
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    token_file = Path("token.json")
    creds_file = Path("credentials.json")
    
    creds = None
    if token_file.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        except Exception as e:
            print(f"⚠️ token.json konnte nicht geladen werden: {e}")
            creds = None
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("✅ Token erneuert")
            except Exception as e:
                print(f"⚠️ Token-Erneuerung fehlgeschlagen: {e}")
                creds = None
        if not creds or not creds.valid:
            print("⚠️ Noch nicht eingeloggt. Beim ersten Start von main.py öffnet sich der Browser zur Anmeldung.")
            return True  # Setup ist OK, nur Login fehlt noch
    
    if not creds.valid:
        print("⚠️ Bitte einmal main.py starten und im Browser 'Zulassen' klicken.")
        return True
    
    sheet_id = os.getenv("SHEET_ID")
    if not sheet_id or sheet_id == "deine-google-sheet-id":
        print("⚠️ SHEET_ID in .env nicht gesetzt – Sheet-Zugriff wird nicht getestet.")
        print("   Sobald SHEET_ID gesetzt ist, kannst du diesen Check erneut ausführen.")
        return True
    
    try:
        service = build("sheets", "v4", credentials=creds)
        # Nur Metadaten abfragen (keine sensiblen Daten)
        sheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        title = sheet.get("properties", {}).get("title", "?")
        print(f"✅ Zugriff auf Google Sheet OK (Titel: \"{title}\")")
        return True
    except HttpError as e:
        if e.resp.status == 404:
            print("❌ Sheet nicht gefunden. Prüfe SHEET_ID in .env (aus der Sheet-URL).")
        elif e.resp.status == 403:
            print("❌ Kein Zugriff auf das Sheet. Ist deine E-Mail als Testnutzer in der Google Cloud Console eingetragen?")
        else:
            print(f"❌ API-Fehler: {e.resp.status}")
        return False
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return False

def main():
    print("=== Google Cloud / Sheets API Check ===\n")
    
    ok = check_credentials_file()
    if not ok:
        sys.exit(1)
    
    print()
    ok = check_sheets_auth_and_access()
    if not ok:
        sys.exit(1)
    
    print("\n=== Check beendet ===")

if __name__ == "__main__":
    main()
