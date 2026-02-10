"""
Google Sheets Ein-/Ausgabe
"""

import logging
from pathlib import Path
from typing import List
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.models import Lead, LeadResult
from src.constants import STATUS_WECHSEL, STATUS_UNBEKANNT

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

class SheetsIO:
    """Google Sheets API Handler"""
    
    def __init__(self, config):
        self.config = config
        self.sheet_id = config.sheet_id
        self.sheet_name = config.get('sheets.sheet_name', 'Sheet1')
        self.service = self._authenticate()
    
    def _authenticate(self):
        """OAuth2 Authentifizierung"""
        creds = None
        token_file = Path('token.json')
        creds_file = Path('credentials.json')
        
        # Token-Datei existiert?
        if token_file.exists():
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        
        # Gültige Credentials?
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Erneuere Google-Credentials...")
                creds.refresh(Request())
            else:
                if not creds_file.exists():
                    raise FileNotFoundError(
                        "credentials.json nicht gefunden. "
                        "Bitte Google Cloud Console Credentials herunterladen."
                    )
                logger.info("Starte Google OAuth-Flow...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(creds_file), SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Token speichern
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
        
        return build('sheets', 'v4', credentials=creds)
    
    def read_leads(self) -> List[Lead]:
        """
        Liest Leads aus Google Sheets.
        Wenn skip_already_processed=true: Es werden alle Zeilen verarbeitet,
        in denen die Skip-Check-Spalte (z.B. Telefonnummer) leer ist –
        also auch Lücken (nicht ausgefüllte Zeilen dazwischen).
        """
        try:
            # Spalten-Konfiguration
            input_cols = self.config.get('sheets.input_columns', {})
            output_cols = self.config.get('sheets.output_columns', {})
            full_name_col = input_cols.get('full_name')
            vorname_col = input_cols.get('vorname', 'Vorname')
            nachname_col = input_cols.get('nachname', 'Nachname')
            unternehmen_col = input_cols.get('unternehmen', 'Unternehmen')
            if not unternehmen_col:
                unternehmen_col = input_cols.get('company', 'Company')
            
            # Header-Zeile holen
            header_row = self.config.get('sheets.header_row', 1)
            range_name = f"{self.sheet_name}!A{header_row}:Z{header_row}"
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=range_name
            ).execute()
            
            headers = result.get('values', [[]])[0]
            
            # Spalten-Indizes finden (entweder "Full Name" + "Company" oder "Vorname" + "Nachname" + "Unternehmen")
            use_full_name = bool(full_name_col and full_name_col in headers)
            try:
                if use_full_name:
                    full_name_idx = headers.index(full_name_col)
                    unternehmen_idx = headers.index(unternehmen_col)
                    vorname_idx = nachname_idx = full_name_idx  # werden aus derselben Zelle gesetzt
                else:
                    vorname_idx = headers.index(vorname_col)
                    nachname_idx = headers.index(nachname_col)
                    unternehmen_idx = headers.index(unternehmen_col)
            except ValueError as e:
                raise ValueError(f"Spalte nicht gefunden. Erwartet: {list(input_cols.values()) or ['Vorname','Nachname','Unternehmen']}, gefunden: {headers}. {e}")
            
            # Optional: Index der Spalte zum Überspringen bereits verarbeiteter Zeilen
            skip_already = self.config.get('sheets.skip_already_processed', True)
            skip_col = self.config.get('sheets.skip_check_column', 'Telefonnummer')
            skip_idx = None
            if skip_already and skip_col in headers:
                skip_idx = headers.index(skip_col)
            
            # Daten lesen
            data_start = self.config.get('sheets.data_start_row', 2)
            range_name = f"{self.sheet_name}!A{data_start}:Z"
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=range_name
            ).execute()
            
            rows = result.get('values', [])
            
            # Verarbeite alle Zeilen, in denen die Skip-Spalte (z.B. Telefonnummer) leer ist –
            # also auch Lücken (nicht ausgefüllte Zeilen dazwischen). Hilft z.B. beim LinkedIn-Limiter.
            leads = []
            for i, row in enumerate(rows, start=data_start):
                # Bereits verarbeitet = Skip-Spalte ist ausgefüllt (nicht leer)
                if skip_already and skip_idx is not None:
                    if len(row) > skip_idx:
                        cell = (row[skip_idx] or "").strip()
                        if cell:
                            continue  # Zeile überspringen, wurde schon verarbeitet
                
                # Zeile hat genug Spalten?
                if len(row) > max(vorname_idx, nachname_idx, unternehmen_idx):
                    if use_full_name:
                        vorname = (row[full_name_idx].strip() if len(row) > full_name_idx else "")
                        nachname = ""  # Full Name ungeteilt nutzen
                    else:
                        vorname = row[vorname_idx].strip() if len(row) > vorname_idx else ""
                        nachname = row[nachname_idx].strip() if len(row) > nachname_idx else ""
                    unternehmen = row[unternehmen_idx].strip() if len(row) > unternehmen_idx else ""
                    
                    if vorname and (nachname or use_full_name):
                        leads.append(Lead(
                            vorname=vorname,
                            nachname=nachname,
                            unternehmen=unternehmen,
                            row_number=i
                        ))
            
            if skip_already and leads:
                logger.info(f"{len(leads)} Zeilen mit leerer {skip_col} (inkl. Lücken dazwischen) werden verarbeitet")
            
            return leads
            
        except HttpError as error:
            logger.error(f"Google Sheets API Fehler: {error}")
            raise
    
    def write_single_result(self, result: LeadResult):
        """
        Schreibt ein einzelnes Ergebnis sofort in Google Sheets
        (Optimiert für einzelnes Update)
        """
        self.write_results([result])
    
    def write_results(self, results: List[LeadResult]):
        """Schreibt Ergebnisse zurück in Google Sheets mit Formatierung für Zielgruppe"""
        try:
            # Output-Spalten aus Config
            output_cols = self.config.get('sheets.output_columns', {})
            header_row = self.config.get('sheets.header_row', 1)
            
            # Header lesen um Spalten-Indizes zu finden
            range_name = f"{self.sheet_name}!A{header_row}:Z{header_row}"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=range_name
            ).execute()
            
            headers = result.get('values', [[]])[0]
            
            # Spalten-Indizes (oder erstellen wenn nicht vorhanden)
            tel_col = output_cols.get('telefonnummer', 'Telefonnummer')
            tel2_col = output_cols.get('zweite_telefonnummer', 'Zweite Telefonnummer')
            stufe_col = output_cols.get('stufe', 'Stufe/Position')
            zielgruppe_col = output_cols.get('zielgruppe', 'Zielgruppe')
            
            # Finde/erstelle Spalten-Indizes
            def get_or_create_col_idx(headers, col_name):
                try:
                    return headers.index(col_name)
                except ValueError:
                    # Spalte existiert nicht, füge sie hinzu
                    headers.append(col_name)
                    return len(headers) - 1
            
            tel_idx = get_or_create_col_idx(headers, tel_col)
            tel2_idx = get_or_create_col_idx(headers, tel2_col)
            stufe_idx = get_or_create_col_idx(headers, stufe_col)
            zielgruppe_idx = get_or_create_col_idx(headers, zielgruppe_col)
            
            # Header aktualisieren falls neue Spalten
            header_range = f"{self.sheet_name}!A{header_row}:Z{header_row}"
            self.service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range=header_range,
                valueInputOption='RAW',
                body={'values': [headers]}
            ).execute()
            
            # Alle Zeilen einmal lesen (um bestehende Daten zu bewahren)
            data_start = self.config.get('sheets.data_start_row', 2)
            all_rows_range = f"{self.sheet_name}!A{data_start}:Z"
            all_rows_result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=all_rows_range
            ).execute()
            existing_rows = all_rows_result.get('values', [])
            
            # Batch-Update für alle Ergebnisse
            updates = []
            format_requests = []  # Für Formatierung (Hintergrundfarbe)
            
            for result in results:
                row_num = result.lead.row_number
                row_idx = row_num - data_start  # Index im existing_rows Array
                
                # Bestehende Zeile lesen (oder leere Zeile erstellen)
                if row_idx < len(existing_rows):
                    row_data = list(existing_rows[row_idx])  # Kopie der bestehenden Daten
                    # Zeile auf Header-Länge erweitern falls nötig
                    while len(row_data) < len(headers):
                        row_data.append('')
                else:
                    row_data = [''] * len(headers)
                
                # Output-Spalten aktualisieren (Input-Daten bleiben erhalten!)
                row_data[tel_idx] = result.telefonnummer
                row_data[tel2_idx] = result.zweite_telefonnummer
                row_data[stufe_idx] = result.stufe
                # Zielgruppe: Status "Unbekannt" und "Wechsel/Nicht mehr in Branche" in Zielgruppe anzeigen
                if result.status == STATUS_UNBEKANNT:
                    row_data[zielgruppe_idx] = STATUS_UNBEKANNT  # "Unbekannt" → wird orange formatiert
                elif result.status == STATUS_WECHSEL:
                    row_data[zielgruppe_idx] = STATUS_WECHSEL  # "Wechsel/Nicht mehr in Branche" → wird rot formatiert
                else:
                    row_data[zielgruppe_idx] = result.zielgruppe or ""
                
                # A1-Notation für diese Zeile
                range_name = f"{self.sheet_name}!A{row_num}:Z{row_num}"
                updates.append({
                    'range': range_name,
                    'values': [row_data]
                })
                
                # Formatierung für Zielgruppe-Spalte (Hintergrundfarbe)
                zielgruppe_display = row_data[zielgruppe_idx]  # bereits oben gesetzt (inkl. Unbekannt/Wechsel)
                if zielgruppe_display:
                    # Grün = In Scope, Orange = Unbekannt + Out of Scope, Rot = Nicht mehr in Branche
                    color = {
                        "In Scope": {"red": 0.7, "green": 0.9, "blue": 0.7},       # Hellgrün
                        "Out of Scope": {"red": 1.0, "green": 0.8, "blue": 0.6},   # Hellorange
                        STATUS_UNBEKANNT: {"red": 1.0, "green": 0.6, "blue": 0.2}, # Orange (Unbekannt)
                        STATUS_WECHSEL: {"red": 1.0, "green": 0.2, "blue": 0.2},   # Rot (Nicht mehr in Branche)
                    }.get(zielgruppe_display)
                    
                    if color:
                        format_requests.append({
                            "repeatCell": {
                                "range": {
                                    "sheetId": 0,  # Erste Sheet (Standard)
                                    "startRowIndex": row_num - 1,  # 0-basiert
                                    "endRowIndex": row_num,
                                    "startColumnIndex": zielgruppe_idx,
                                    "endColumnIndex": zielgruppe_idx + 1
                                },
                                "cell": {
                                    "userEnteredFormat": {
                                        "backgroundColor": color
                                    }
                                },
                                "fields": "userEnteredFormat.backgroundColor"
                            }
                        })
            
            # Batch-Update ausführen
            if updates:
                body = {
                    'valueInputOption': 'RAW',
                    'data': updates
                }
                self.service.spreadsheets().values().batchUpdate(
                    spreadsheetId=self.sheet_id,
                    body=body
                ).execute()
                
                logger.info(f"{len(updates)} Zeilen in Google Sheets aktualisiert")
            
            # Formatierung anwenden (separate API-Call)
            if format_requests:
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.sheet_id,
                    body={"requests": format_requests}
                ).execute()
                logger.info(f"{len(format_requests)} Zellen formatiert (Zielgruppe)")
            
        except HttpError as error:
            logger.error(f"Google Sheets API Fehler beim Schreiben: {error}")
            raise
