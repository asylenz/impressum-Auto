"""Datenmodelle für den Impressum-Scraper"""

from dataclasses import dataclass, field


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
    impressum_url: str = ""
    geschaeftsfuehrer: str = ""
    telefonnummer: str = ""
    status: str = ""

    def to_dict(self) -> dict:
        return {
            "Firmenname":        self.firmenname,
            "Website":           self.website,
            "Impressum-URL":     self.impressum_url,
            "Geschäftsführer":   self.geschaeftsfuehrer,
            "Telefonnummer":     self.telefonnummer,
            "Status":            self.status,
        }
