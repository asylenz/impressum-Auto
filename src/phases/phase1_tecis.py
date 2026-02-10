"""
Phase 1: Tecis.de Scraping
"""

import logging
from typing import Optional, List, Tuple
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from src.models import Lead, ProcessingFlags
from src.utils import extract_phone_from_href, categorize_stufe
from src.constants import TECIS_TITLE_CLASS, TECIS_CONTACT_LINKS, TECIS_KONTAKT_SUFFIX, TECIS_IMPRESSUM_SUFFIX

logger = logging.getLogger(__name__)

class TecisPhase:
    """Phase 1: Tecis.de Scraping"""
    
    def __init__(self, config, rate_limiter):
        self.config = config
        self.rate_limiter = rate_limiter
        self.valid_stufen = config.valid_stufen
    
    def process(self, page: Page, url: str, lead: Lead, flags: ProcessingFlags) -> Tuple[Optional[str], List[str]]:
        """
        Verarbeitet Tecis-URL und gibt (Stufe, [Telefonnummern]) zurück
        """
        if not url:
            return None, []
        
        try:
            logger.info(f"Öffne Tecis-Seite: {url}")
            
            # Rate-Limiting
            self.rate_limiter.wait_if_needed('tecis')
            
            # Seite öffnen
            page.goto(url, wait_until='domcontentloaded')
            self.rate_limiter.record_request('tecis')
            
            # Stufe extrahieren
            stufe = self._extract_stufe(page)
            
            if stufe:
                logger.info(f"Stufe gefunden: {stufe}")
                flags.stufe_gefunden = True
            else:
                logger.info("Keine gültige Stufe gefunden")
            
            # Kontaktseite öffnen und Telefonnummern holen
            telefonnummern = self._extract_telefonnummern(page, url, lead)
            
            if telefonnummern:
                logger.info(f"{len(telefonnummern)} Telefonnummer(n) gefunden")
                flags.telefonnummer_gefunden = True
            else:
                logger.info("Keine Telefonnummern auf Tecis-Seite gefunden")
            
            return stufe, telefonnummern
            
        except Exception as e:
            logger.error(f"Fehler beim Verarbeiten von Tecis-Seite: {e}")
            return None, []
    
    def _extract_stufe(self, page: Page) -> Optional[str]:
        """
        Extrahiert Stufe/Position von Tecis-Landingpage
        Gibt Stufe zurück, auch wenn Out of Scope (wird später kategorisiert)
        """
        def clean(t: str) -> str:
            return (t or "").strip().lstrip("|").strip()
        
        try:
            # Primär: CSS aus Spezifikation
            stufe_element = page.query_selector(TECIS_TITLE_CLASS)
            if not stufe_element:
                stufe_element = page.query_selector('h1 + span[class*="title"]')
            if not stufe_element:
                stufe_element = page.query_selector('[class*="personal-information"] [class*="title"]')
            
            if not stufe_element:
                return None
            
            stufe_text = clean(stufe_element.inner_text())
            if not stufe_text:
                return None
            
            # Prüfe ob Stufe bekannt ist (In Scope oder Out of Scope)
            is_valid, category = categorize_stufe(stufe_text)
            if category in ["in_scope", "out_of_scope"]:
                logger.debug(f"Stufe '{stufe_text}' gefunden - Kategorie: {category}")
                return stufe_text
            
            # Fallback: Einzelne Wörter prüfen (z. B. "Teamleiter | Spezialist...")
            for word in stufe_text.replace("|", " ").replace(",", " ").split():
                word = word.strip(".,")
                if word:
                    is_valid, category = categorize_stufe(word)
                    if category in ["in_scope", "out_of_scope"]:
                        logger.debug(f"Stufe '{word}' aus '{stufe_text}' extrahiert - Kategorie: {category}")
                        return word
            
            # Fallback: Teilstring-Match mit bekannten Stufen
            from src.constants import STUFEN_IN_SCOPE, STUFEN_OUT_OF_SCOPE
            stufe_lower = stufe_text.lower()
            for stufe in STUFEN_IN_SCOPE + STUFEN_OUT_OF_SCOPE:
                if stufe.lower() in stufe_lower:
                    logger.debug(f"Stufe '{stufe}' via Teilstring in '{stufe_text}' gefunden")
                    return stufe
            
            logger.debug(f"Stufe '{stufe_text}' ist unbekannt (weder In Scope noch Out of Scope)")
        except Exception as e:
            logger.debug(f"Fehler beim Extrahieren der Stufe: {e}")
        
        return None
    
    def _extract_telefonnummern(self, page: Page, base_url: str, lead: Lead) -> List[str]:
        """Extrahiert Telefonnummern von Kontaktseite, bei Bedarf auch aus Impressum."""
        telefonnummern = []
        
        try:
            # Zuerst Kontaktseite versuchen
            kontakt_url = self._build_kontakt_url(base_url)
            logger.debug(f"Öffne Kontaktseite: {kontakt_url}")
            page.goto(kontakt_url, wait_until='domcontentloaded')
            telefonnummern = self._collect_tel_links(page)
            
            # Fallback: Impressum, wenn auf Kontaktseite nichts gefunden
            if not telefonnummern:
                impressum_url = self._build_impressum_url(base_url)
                if impressum_url != kontakt_url:
                    logger.debug(f"Keine Nummer auf Kontaktseite, versuche Impressum: {impressum_url}")
                    page.goto(impressum_url, wait_until='domcontentloaded')
                    telefonnummern = self._collect_tel_links(page)
            
            return telefonnummern[:2]
            
        except PlaywrightTimeout:
            logger.warning("Timeout beim Laden der Kontaktseite")
        except Exception as e:
            logger.error(f"Fehler beim Extrahieren von Telefonnummern: {e}")
        
        return telefonnummern[:2] if telefonnummern else []
    
    def _collect_tel_links(self, page: Page) -> List[str]:
        """Sammelt alle tel:-Links von der aktuellen Seite"""
        result = []
        # Kontaktseite: Container .contacts-columns
        tel_links = page.query_selector_all(TECIS_CONTACT_LINKS)
        if not tel_links:
            # Impressum / allgemein: alle tel:-Links auf der Seite
            tel_links = page.query_selector_all('a[href^="tel:"]')
        
        for link in tel_links:
            href = link.get_attribute('href')
            if href:
                nummer = extract_phone_from_href(href)
                if nummer and nummer not in result:
                    result.append(nummer)
        return result
    
    def _build_kontakt_url(self, base_url: str) -> str:
        """Konstruiert Kontakt-URL aus Base-URL"""
        base_url = base_url.rstrip('/')
        
        if TECIS_KONTAKT_SUFFIX in base_url:
            return base_url
        if TECIS_IMPRESSUM_SUFFIX in base_url:
            return base_url.replace(TECIS_IMPRESSUM_SUFFIX, TECIS_KONTAKT_SUFFIX)
        if base_url.endswith('.html'):
            return base_url.replace('.html', TECIS_KONTAKT_SUFFIX)
        
        return f"{base_url}{TECIS_KONTAKT_SUFFIX}"
    
    def _build_impressum_url(self, base_url: str) -> str:
        """Konstruiert Impressum-URL aus Base-URL"""
        base_url = base_url.rstrip('/')
        
        if TECIS_IMPRESSUM_SUFFIX in base_url:
            return base_url
        if TECIS_KONTAKT_SUFFIX in base_url:
            return base_url.replace(TECIS_KONTAKT_SUFFIX, TECIS_IMPRESSUM_SUFFIX)
        if base_url.endswith('.html'):
            return base_url.replace('.html', TECIS_IMPRESSUM_SUFFIX)
        
        return f"{base_url}{TECIS_IMPRESSUM_SUFFIX}"
