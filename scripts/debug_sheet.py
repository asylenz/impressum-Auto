#!/usr/bin/env python3
"""
Debug-Skript: Zeigt Google Sheet-Struktur an
"""

from src.config import Config
from src.sheets_io import SheetsIO

def main():
    config = Config()
    sheets_io = SheetsIO(config)
    
    # Header lesen
    sheet_name = config.get('sheets.sheet_name', 'Sheet1')
    header_row = config.get('sheets.header_row', 1)
    
    range_name = f"{sheet_name}!A{header_row}:Z{header_row}"
    
    result = sheets_io.service.spreadsheets().values().get(
        spreadsheetId=sheets_io.sheet_id,
        range=range_name
    ).execute()
    
    headers = result.get('values', [[]])[0]
    
    print("=" * 60)
    print("GOOGLE SHEET STRUKTUR")
    print("=" * 60)
    print(f"Sheet Name: {sheet_name}")
    print(f"Header Row: {header_row}")
    print(f"\nSpalten ({len(headers)}):")
    for i, header in enumerate(headers):
        print(f"  {i}: {header}")
    
    # Erste 5 Datenzeilen lesen
    data_start = config.get('sheets.data_start_row', 2)
    range_name = f"{sheet_name}!A{data_start}:Z"
    
    result = sheets_io.service.spreadsheets().values().get(
        spreadsheetId=sheets_io.sheet_id,
        range=range_name
    ).execute()
    
    rows = result.get('values', [])
    
    print(f"\nDatenzeilen: {len(rows)} Zeilen gefunden")
    print(f"\nErste {min(5, len(rows))} Zeilen:")
    for i, row in enumerate(rows[:5], start=data_start):
        print(f"\n  Zeile {i}:")
        for j, cell in enumerate(row):
            print(f"    [{headers[j] if j < len(headers) else f'Col{j}'}]: {cell}")
    
    # Config-Einstellungen
    print("\n" + "=" * 60)
    print("CONFIG-EINSTELLUNGEN")
    print("=" * 60)
    print(f"skip_already_processed: {config.get('sheets.skip_already_processed')}")
    print(f"skip_check_column: {config.get('sheets.skip_check_column')}")
    print(f"input_columns.vorname: {config.get('sheets.input_columns.vorname')}")
    print(f"input_columns.nachname: {config.get('sheets.input_columns.nachname')}")
    print(f"input_columns.unternehmen: {config.get('sheets.input_columns.unternehmen')}")

if __name__ == "__main__":
    main()
