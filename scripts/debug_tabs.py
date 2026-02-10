#!/usr/bin/env python3
"""
Debug-Skript: Zeigt alle Tabs in der Google Sheet
"""

from src.config import Config
from src.sheets_io import SheetsIO

def main():
    config = Config()
    sheets_io = SheetsIO(config)
    
    # Alle Sheets abrufen
    sheet_metadata = sheets_io.service.spreadsheets().get(
        spreadsheetId=sheets_io.sheet_id
    ).execute()
    
    sheets = sheet_metadata.get('sheets', [])
    
    print("=" * 60)
    print("VERFÜGBARE TABS IN DER GOOGLE SHEET")
    print("=" * 60)
    for sheet in sheets:
        props = sheet['properties']
        print(f"\nTab-Name: {props['title']}")
        print(f"  Sheet ID: {props['sheetId']}")
        print(f"  Index: {props['index']}")
        print(f"  Zeilen: {props.get('gridProperties', {}).get('rowCount', 'unknown')}")
        print(f"  Spalten: {props.get('gridProperties', {}).get('columnCount', 'unknown')}")
    
    print("\n" + "=" * 60)
    print(f"Konfigurierter Tab-Name: {config.get('sheets.sheet_name', 'Sheet1')}")
    print("=" * 60)

if __name__ == "__main__":
    main()
