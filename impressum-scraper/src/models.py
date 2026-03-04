"""Datenmodelle für den Impressum-Scraper"""

import re
from dataclasses import dataclass, field


@dataclass
class SearchResult:
    """Ergebnis einer Google-Suche"""

    title: str
    url: str
    snippet: str = ""


@dataclass
class FirmenResult:
    """Scraping-Ergebnis für eine Firma — CRM/Excel-optimiertes Format"""

    # Firmendaten
    firmenname: str
    strasse: str = ""
    plz: str = ""
    ort: str = ""

    # Kontaktdaten aus Quell-CSV
    telefon_verzeichnis: str = ""
    email: str = ""

    # Scraping-Ergebnisse
    website: str = ""
    impressum_url: str = ""
    geschaeftsfuehrer: str = ""        # Vollständiger Name (z.B. "Max Müller")
    gf_vorname: str = ""               # Aufgeteilt für CRM-Import
    gf_nachname: str = ""
    telefon_impressum: str = ""        # Roh aus Impressum
    telefon_normalisiert: str = ""     # Bereinigt: +49 30 123456
    status: str = ""

    def _split_gf_name(self) -> None:
        """Teilt Geschäftsführer-Name in Vorname/Nachname auf"""
        name = self.geschaeftsfuehrer.strip()
        # Bei mehreren GFs (Komma-getrennt) nur den ersten nehmen
        if "," in name:
            name = name.split(",")[0].strip()
        parts = name.split()
        if len(parts) >= 2:
            self.gf_nachname = parts[-1]
            self.gf_vorname = " ".join(parts[:-1])
        elif len(parts) == 1:
            self.gf_nachname = parts[0]

    def _normalize_phone(self, phone: str) -> str:
        """Normalisiert Telefonnummer auf einheitliches Format"""
        if not phone:
            return ""
        # Alles außer Ziffern, +, (, ) entfernen für Vergleich
        clean = re.sub(r"[\s\-\/\.]", "", phone).strip()
        # Führende 0 durch +49 ersetzen
        if clean.startswith("0") and not clean.startswith("00"):
            clean = "+49" + clean[1:]
        elif clean.startswith("0049"):
            clean = "+49" + clean[4:]
        return clean

    def finalize(self) -> "FirmenResult":
        """Berechnet abgeleitete Felder vor dem Schreiben"""
        self._split_gf_name()
        self.telefon_normalisiert = self._normalize_phone(
            self.telefon_impressum or self.telefon_verzeichnis
        )
        return self

    def to_dict(self) -> dict:
        return {
            "Firmenname":            self.firmenname,
            "GF_Vorname":            self.gf_vorname,
            "GF_Nachname":           self.gf_nachname,
            "Geschaeftsfuehrer":     self.geschaeftsfuehrer,
            "Telefon_Impressum":     self.telefon_impressum,
            "Telefon_Normalisiert":  self.telefon_normalisiert,
            "Telefon_Verzeichnis":   self.telefon_verzeichnis,
            "Email":                 self.email,
            "Strasse":               self.strasse,
            "PLZ":                   self.plz,
            "Ort":                   self.ort,
            "Website":               self.website,
            "Impressum_URL":         self.impressum_url,
            "Status":                self.status,
        }
