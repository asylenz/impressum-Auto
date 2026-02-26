"""
Datenmodelle
"""

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Lead:
    """Eingabe-Lead aus Google Sheets"""
    vorname: str
    nachname: str
    unternehmen: str
    row_number: int  # Zeile in Google Sheets
    
    @property
    def full_name(self) -> str:
        return f"{self.vorname} {self.nachname}".strip()

@dataclass
class LeadResult:
    """Ergebnis nach Verarbeitung eines Leads"""
    lead: Lead
    telefonnummer: str = ""
    zweite_telefonnummer: str = ""
    stufe: str = ""
    stufe_prio: int = 99  # Priorität der Stufen-Quelle (1=Firmenseite, 2=Entry, 3=Headline, 4=Lusha; niedriger = besser)
    status: str = ""
    zielgruppe: str = ""  # "In Scope", "Out of Scope" oder leer
    tel_quelle: str = ""  # Quelle der Telefonnummer: "Firmenseite" | "LinkedIn" | "Creditreform" | "Lusha"
    
    # URLs für Debugging/Logging
    target_url_company: Optional[str] = None
    target_url_linkedin: Optional[str] = None
    target_url_xing: Optional[str] = None
    target_url_creditreform: Optional[str] = None

@dataclass
class SearchResult:
    """Suchergebnis von Google"""
    title: str
    url: str
    snippet: str = ""

@dataclass
class ProcessingFlags:
    """Flags für die Phasensteuerung"""
    nur_status_check: bool = False
    nur_stufe_suchen: bool = False
    status_check_weiter_creditreform: bool = False
    stufe_suchen_weiter_creditreform: bool = False
    nur_stufe_suchen_status_active_confirmed: bool = False
    status_active_confirmed: bool = False
    
    telefonnummer_gefunden: bool = False
    stufe_gefunden: bool = False
