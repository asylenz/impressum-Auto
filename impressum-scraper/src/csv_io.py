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

def read_firmen(filepath: str) -> List[str]:
    """
    Liest Firmennamen aus der Eingabe-CSV.
    Erwartet mindestens Spalte 'Firmenname'.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Eingabe-Datei nicht gefunden: {filepath}")

    firmen: List[str] = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if "Firmenname" not in (reader.fieldnames or []):
            raise ValueError(
                f"Spalte 'Firmenname' fehlt in der CSV. "
                f"Gefundene Spalten: {reader.fieldnames}"
            )
        for row in reader:
            name = row.get("Firmenname", "").strip()
            if name:
                firmen.append(name)

    logger.info(f"{len(firmen)} Firmennamen aus '{filepath}' geladen")
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


def read_pending_retry(filepath: str) -> List[str]:
    """
    Gibt Firmen zurück deren Status 'kein ergebnis' ist.
    Wird für --retry Modus verwendet.
    """
    path = Path(filepath)
    if not path.exists():
        logger.warning(f"Output-Datei '{filepath}' nicht gefunden — kein Retry möglich")
        return []

    pending: List[str] = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            firma = row.get("Firmenname", "").strip()
            status = row.get("Status", "").strip().lower()
            if firma and status == "kein ergebnis":
                pending.append(firma)

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
