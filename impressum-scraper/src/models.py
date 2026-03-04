"""Datenmodelle für den Impressum-Scraper"""

from dataclasses import dataclass


@dataclass
class SearchResult:
    """Ergebnis einer Google-Suche"""

    title: str
    url: str
    snippet: str = ""


@dataclass
class FirmenResult:
    """Scraping-Ergebnis für eine Firma"""

    firmenname: str
    website: str = ""
    geschaeftsfuehrer: str = ""
    telefonnummer: str = ""
    status: str = ""

    def to_dict(self) -> dict:
        return {
            "Firmenname":       self.firmenname,
            "Website":          self.website,
            "Geschaeftsfuehrer": self.geschaeftsfuehrer,
            "Telefonnummer":    self.telefonnummer,
            "Status":           self.status,
        }
