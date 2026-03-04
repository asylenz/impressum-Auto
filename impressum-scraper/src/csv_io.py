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
import os
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

# Semikolon als Trennzeichen für deutsches Excel / CRM-Import
CSV_DELIMITER = ";"


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

        has_website  = "website"      in fields
        has_telefon  = "telefon"      in fields
        has_email    = "email"        in fields
        has_street   = "street"       in fields
        has_plz      = "postal_code"  in fields
        has_city     = "city"         in fields

        for row in reader:
            name = row.get(name_col, "").strip()
            if not name:
                continue
            firmen.append({
                "firmenname": name,
                "website":    row.get("website",      "").strip() if has_website else "",
                "telefon":    row.get("telefon",      "").strip() if has_telefon else "",
                "email":      row.get("email",        "").strip() if has_email   else "",
                "strasse":    row.get("street",       "").strip() if has_street  else "",
                "plz":        row.get("postal_code",  "").strip() if has_plz     else "",
                "ort":        row.get("city",         "").strip() if has_city    else "",
            })

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
        reader = csv.DictReader(f, delimiter=CSV_DELIMITER)
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
        reader = csv.DictReader(f, delimiter=CSV_DELIMITER)
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

def _make_writer(f) -> csv.DictWriter:
    """Erstellt einen DictWriter mit einheitlichen Einstellungen."""
    return csv.DictWriter(
        f,
        fieldnames=OUTPUT_COLUMNS,
        delimiter=CSV_DELIMITER,
        quoting=csv.QUOTE_ALL,        # Alle Felder quoten → keine Mehrzeiler-Probleme
        extrasaction="ignore",        # Unbekannte Felder ignorieren
        lineterminator="\n",
    )


def ensure_output_file(filepath: str) -> None:
    """Erstellt die Output-CSV mit Header, falls sie noch nicht existiert."""
    path = Path(filepath)
    if not path.exists():
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            _make_writer(f).writeheader()
        logger.info(f"Output-Datei erstellt: '{filepath}' (Trennzeichen: Semikolon)")


def write_result(filepath: str, result: FirmenResult, retry_mode: bool = False) -> None:
    """
    Schreibt ein einzelnes Ergebnis sofort in die Output-CSV.

    Im normalen Modus: Zeile wird angehängt.
    Im Retry-Modus:    Bestehende Zeile wird in-place aktualisiert.
    """
    path = Path(filepath)

    # Newlines in Feldern bereinigen (Sicherheitsnetz gegen mehrzeilige Werte)
    data = result.to_dict()
    for key in data:
        if isinstance(data[key], str):
            data[key] = " ".join(data[key].split())

    if retry_mode and path.exists():
        _update_existing_row(filepath, result)
    else:
        with open(path, "a", newline="", encoding="utf-8-sig") as f:
            writer = _make_writer(f)
            writer.writerow(data)


def _update_existing_row(filepath: str, result: FirmenResult) -> None:
    """
    Liest die gesamte CSV, ersetzt die Zeile der Firma und schreibt alles zurück.
    Wird nur im Retry-Modus aufgerufen.
    """
    path = Path(filepath)
    rows: List[dict] = []
    updated = False

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=CSV_DELIMITER)
        for row in reader:
            if row.get("Firmenname", "").strip() == result.firmenname:
                data = result.to_dict()
                for key in data:
                    if isinstance(data[key], str):
                        data[key] = " ".join(data[key].split())
                rows.append(data)
                updated = True
            else:
                rows.append(dict(row))

    if not updated:
        data = result.to_dict()
        for key in data:
            if isinstance(data[key], str):
                data[key] = " ".join(data[key].split())
        rows.append(data)

    # Atomares Schreiben: erst in Temp-Datei, dann umbenennen.
    # Verhindert Datenverlust wenn der Prozess während des Schreibens abbricht.
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = _make_writer(f)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp_path, path)  # atomare Operation auf allen gängigen Dateisystemen
