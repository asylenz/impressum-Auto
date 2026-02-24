"""
Phase 1: Firmenseite Scraping (Generisch)
"""

import logging
from typing import Optional, List, Tuple, Union
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from src.models import Lead, ProcessingFlags
from src.utils import extract_phone_from_href, categorize_stufe

logger = logging.getLogger(__name__)

class CompanySitePhase:
    """Phase 1: Firmenseite Scraping"""
    
    def __init__(self, config, rate_limiter):
        self.config = config
        self.rate_limiter = rate_limiter
        # self.valid_stufen ist jetzt ein Dict mit 'in_scope' und 'out_of_scope'
        self.valid_stufen = config.valid_stufen
        self.selectors = config.company_selectors
        self.suffixes = config.company_suffixes
    
    def process(self, page: Page, url: str, lead: Lead, flags: ProcessingFlags) -> Tuple[Optional[str], List[str]]:
        """
        Verarbeitet Firmen-URL und gibt (Stufe, [Telefonnummern]) zurück
        """
        if not url:
            return None, []
        
        try:
            logger.info(f"Öffne Firmenseite: {url}")
            
            # Rate-Limiting (Generisch oder 'tecis')
            # Nutze Modus-Namen als Key für Rate-Limiter (z.B. 'tecis')
            limit_key = self.config.mode if self.config.get(f'limits.{self.config.mode}.delay_between_requests_min') else 'company_site'
            self.rate_limiter.wait_if_needed(limit_key)
            
            # Seite öffnen
            page.goto(url, wait_until='domcontentloaded')
            self.rate_limiter.record_request(limit_key)
            
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
                logger.info("Keine Telefonnummern auf Firmenseite gefunden")
            
            return stufe, telefonnummern
            
        except Exception as e:
            logger.error(f"Fehler beim Verarbeiten von Firmenseite: {e}")
            return None, []
    
    def _extract_stufe(self, page: Page) -> Optional[str]:
        """
        Extrahiert Stufe/Position von Landingpage
        """
        def clean(t: str) -> str:
            return (t or "").strip().lstrip("|").strip()
        
        try:
            # Selektor(en) aus Config
            title_selectors = self.selectors.get('title')
            # Stelle sicher, dass es eine Liste ist
            if isinstance(title_selectors, str):
                title_selectors = [title_selectors]
            elif not title_selectors:
                title_selectors = []
            
            stufe_element = None
            
            # 1. Config-Selektoren prüfen
            for selector in title_selectors:
                stufe_element = page.query_selector(selector)
                if stufe_element:
                    logger.debug(f"Stufe gefunden mit Config-Selektor: {selector}")
                    break
            
            # 2. Fallbacks (generisch), falls Config-Selektoren nicht greifen
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
            is_valid, category = categorize_stufe(stufe_text, self.valid_stufen)
            if category in ["in_scope", "out_of_scope"]:
                logger.debug(f"Stufe '{stufe_text}' gefunden - Kategorie: {category}")
                return stufe_text
            
            # Fallback: Einzelne Wörter prüfen (z. B. "Teamleiter | Spezialist...")
            for word in stufe_text.replace("|", " ").replace(",", " ").split():
                word = word.strip(".,")
                if word:
                    is_valid, category = categorize_stufe(word, self.valid_stufen)
                    if category in ["in_scope", "out_of_scope"]:
                        logger.debug(f"Stufe '{word}' aus '{stufe_text}' extrahiert - Kategorie: {category}")
                        return word
            
            # Fallback: Teilstring-Match mit bekannten Stufen
            all_stufen = self.valid_stufen.get('in_scope', []) + self.valid_stufen.get('out_of_scope', [])
            stufe_lower = stufe_text.lower()
            for stufe in all_stufen:
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
        tel_links = []
        
        # Kontaktseite: Container aus Config (Liste oder String)
        contact_links_selectors = self.selectors.get('contact_links')
        if isinstance(contact_links_selectors, str):
            contact_links_selectors = [contact_links_selectors]
        elif not contact_links_selectors:
            contact_links_selectors = []
            
        # 1. Config-Selektoren prüfen
        for selector in contact_links_selectors:
            found_links = page.query_selector_all(selector)
            if found_links:
                tel_links.extend(found_links)
        
        # 2. Fallback: alle tel:-Links auf der Seite
        if not tel_links:
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
        
        suffix_kontakt = self.suffixes.get('kontakt', '/kontakt.html')
        suffix_impressum = self.suffixes.get('impressum', '/impressum.html')
        
        if suffix_kontakt in base_url:
            return base_url
        if suffix_impressum in base_url:
            return base_url.replace(suffix_impressum, suffix_kontakt)
        if base_url.endswith('.html'):
            return base_url.replace('.html', suffix_kontakt)
        
        return f"{base_url}{suffix_kontakt}"
    
    def _build_impressum_url(self, base_url: str) -> str:
        """Konstruiert Impressum-URL aus Base-URL"""
        base_url = base_url.rstrip('/')
        
        suffix_kontakt = self.suffixes.get('kontakt', '/kontakt.html')
        suffix_impressum = self.suffixes.get('impressum', '/impressum.html')
        
        if suffix_impressum in base_url:
            return base_url
        if suffix_kontakt in base_url:
            return base_url.replace(suffix_kontakt, suffix_impressum)
        if base_url.endswith('.html'):
            return base_url.replace('.html', suffix_impressum)
        
        return f"{base_url}{suffix_impressum}"
