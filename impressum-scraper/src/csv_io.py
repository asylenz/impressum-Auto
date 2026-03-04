"""
CSV Ein- und Ausgabe für den Impressum-Scraper.

- read_firmen():           Liest Firmennamen aus Eingabe-CSV
- read_existing_results(): Prüft welche Firmen schon verarbeitet wurden
- read_pending_retry():    Gibt Firmen mit Status "kein Ergebnis" zurück
- ensure_output_file():    Erstellt output.csv mit Header (falls nicht vorhanden)
- write_result():          Schreibt/aktualisiert einen einzelnen Eintrag sofort
"""

import csv
import logging
from pathlib import Path
from typing import Dict, List

from src.models import FirmenResult

logger = logging.getLogger(__name__)

OUTPUT_COLUMNS = [
    "Firmenname",
    "Website",
    "Impressum-URL",
    "Geschäftsführer",
    "Telefonnummer",
    "Status",
]


# ---------------------------------------------------------------------------
# Lesen
# ---------------------------------------------------------------------------

def read_firmen(filepath: str) -> List[dict]:
    """
    Liest Firmennamen (und optionale Website) aus der Eingabe-CSV.

    Akzeptierte Spalten für den Firmennamen: 'Firmenname' oder 'name'
    Optionale Spalte: 'website' (wird direkt genutzt, überspringt Google-Suche)

    Gibt eine Liste von Dicts zurück: [{"firmenname": "...", "website": "..."}, ...]
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Eingabe-Datei nicht gefunden: {filepath}")

    fields = None
    firmen: List[dict] = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []

        # Spaltenname für Firma ermitteln
        if "Firmenname" in fields:
            name_col = "Firmenname"
        elif "name" in fields:
            name_col = "name"
        else:
            raise ValueError(
                f"Keine Firmenname-Spalte gefunden. "
                f"Erwartet: 'Firmenname' oder 'name'. "
                f"Gefundene Spalten: {fields}"
            )

        has_website = "website" in fields

        for row in reader:
            name = row.get(name_col, "").strip()
            # "Firma " Präfix entfernen (häufig in HWK-Daten)
            if name.lower().startswith("firma "):
                name = name[6:].strip()
            if not name:
                continue
            website = row.get("website", "").strip() if has_website else ""
            firmen.append({"firmenname": name, "website": website})

    logger.info(f"{len(firmen)} Firmen aus '{filepath}' geladen (Spalte: '{name_col}')")
    if any(f["website"] for f in firmen):
        count = sum(1 for f in firmen if f["website"])
        logger.info(f"  → {count} Firmen haben bereits eine Website-URL (Google-Suche wird übersprungen)")
    return firmen


def read_existing_results(filepath: str) -> Dict[str, dict]:
    """
    Liest bereits verarbeitete Firmen aus der Output-CSV.
    Rückgabe: {Firmenname: row_dict} für alle Zeilen mit nicht-leerem Status.
    Ermöglicht Fortsetzung nach Abbruch.
    """
    path = Path(filepath)
    if not path.exists():
        return {}

    existing: Dict[str, dict] = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            firma = row.get("Firmenname", "").strip()
            status = row.get("Status", "").strip()
            if firma and status:
                existing[firma] = dict(row)

    if existing:
        logger.info(
            f"{len(existing)} bereits verarbeitete Firmen aus '{filepath}' geladen"
        )
    return existing


def read_pending_retry(filepath: str) -> List[dict]:
    """
    Gibt Firmen zurück deren Status 'kein ergebnis' ist.
    Wird für --retry Modus verwendet.
    Gibt Liste von Dicts zurück: [{"firmenname": "...", "website": "..."}, ...]
    """
    path = Path(filepath)
    if not path.exists():
        logger.warning(f"Output-Datei '{filepath}' nicht gefunden — kein Retry möglich")
        return []

    pending: List[dict] = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            firma = row.get("Firmenname", "").strip()
            status = row.get("Status", "").strip().lower()
            if firma and status == "kein ergebnis":
                pending.append({"firmenname": firma, "website": row.get("Website", "").strip()})

    logger.info(f"{len(pending)} Firmen mit Status 'kein Ergebnis' für Retry gefunden")
    return pending


# ---------------------------------------------------------------------------
# Schreiben
# ---------------------------------------------------------------------------

def ensure_output_file(filepath: str) -> None:
    """Erstellt die Output-CSV mit Header, falls sie noch nicht existiert."""
    path = Path(filepath)
    if not path.exists():
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS).writeheader()
        logger.info(f"Output-Datei erstellt: '{filepath}'")


def write_result(filepath: str, result: FirmenResult, retry_mode: bool = False) -> None:
    """
    Schreibt ein einzelnes Ergebnis sofort in die Output-CSV.

    Im normalen Modus: Zeile wird angehängt.
    Im Retry-Modus:    Bestehende Zeile wird in-place aktualisiert.
    """
    path = Path(filepath)

    if retry_mode and path.exists():
        _update_existing_row(filepath, result)
    else:
        with open(path, "a", newline="", encoding="utf-8-sig") as f:
            csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS).writerow(result.to_dict())


def _update_existing_row(filepath: str, result: FirmenResult) -> None:
    """
    Liest die gesamte CSV, ersetzt die Zeile der Firma und schreibt alles zurück.
    Wird nur im Retry-Modus aufgerufen.
    """
    path = Path(filepath)
    rows: List[dict] = []
    updated = False

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Firmenname", "").strip() == result.firmenname:
                rows.append(result.to_dict())
                updated = True
            else:
                rows.append(dict(row))

    if not updated:
        rows.append(result.to_dict())

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
