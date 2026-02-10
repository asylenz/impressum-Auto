"""
Phase 4: Creditreform Scraping
"""

import logging
import re
from typing import List
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from src.models import Lead, ProcessingFlags
from src.utils import is_valid_phone

logger = logging.getLogger(__name__)

class CreditreformPhase:
    """Phase 4: Creditreform Scraping"""
    
    def __init__(self, config, rate_limiter):
        self.config = config
        self.rate_limiter = rate_limiter
    
    def process(self, page: Page, url: str, lead: Lead, flags: ProcessingFlags) -> List[str]:
        """
        Verarbeitet Creditreform-URL
        Gibt [Telefonnummern] zurück
        """
        if not url:
            return []
        
        try:
            logger.info(f"Öffne Creditreform-Seite: {url}")
            
            # Rate-Limiting
            self.rate_limiter.wait_if_needed('creditreform')
            
            # Seite öffnen
            page.goto(url, wait_until='domcontentloaded')
            self.rate_limiter.record_request('creditreform')
            
            page.wait_for_timeout(1000)
            
            # Telefonnummer im #kontakt Container suchen
            telefonnummern = self._extract_telefonnummer(page)
            
            if telefonnummern:
                logger.info(f"{len(telefonnummern)} Telefonnummer(n) gefunden")
            else:
                logger.info("Keine Telefonnummern auf Creditreform-Seite gefunden")
            
            return telefonnummern
            
        except Exception as e:
            logger.error(f"Fehler beim Verarbeiten von Creditreform-Seite: {e}")
            return []
    
    def _extract_telefonnummer(self, page: Page) -> List[str]:
        """Extrahiert Telefonnummer aus #kontakt Container"""
        telefonnummern = []
        
        try:
            # Container #kontakt finden
            kontakt_container = page.query_selector('#kontakt')
            
            if not kontakt_container:
                logger.debug("#kontakt Container nicht gefunden")
                return []
            
            # Alle Textelemente mit Klasse .adress-white
            text_elements = kontakt_container.query_selector_all('.adress-white, span, p')
            
            for element in text_elements:
                text = element.inner_text().strip()
                
                # Regex-Check: Sieht aus wie Telefonnummer?
                if is_valid_phone(text):
                    # Zusätzliche Prüfung: Enthält mindestens 5 Ziffern
                    digits = re.findall(r'\d', text)
                    if len(digits) >= 5:
                        if text not in telefonnummern:
                            telefonnummern.append(text)
            
            # Maximal 2 Nummern
            return telefonnummern[:2]
            
        except Exception as e:
            logger.error(f"Fehler beim Extrahieren von Telefonnummer: {e}")
            return []
