"""
Phase 3: Xing Profil-Scraping
"""

import logging
from typing import Optional, List, Tuple
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from src.models import Lead, ProcessingFlags
from src.utils import categorize_stufe, check_active_status
from src.constants import XING_HEADLINE_ATTR, XING_HEADLINE_VALUE

logger = logging.getLogger(__name__)

class XingPhase:
    """Phase 3: Xing Profil-Scraping"""
    
    def __init__(self, config, rate_limiter):
        self.config = config
        self.rate_limiter = rate_limiter
        self.valid_stufen = config.valid_stufen
    
    def process(self, page: Page, url: str, lead: Lead, flags: ProcessingFlags) -> Tuple[Optional[str], bool]:
        """
        Verarbeitet Xing-URL
        Gibt (Stufe, ist_aktiv) zurück
        """
        if not url:
            return None, True  # Default: aktiv
        
        try:
            logger.info(f"Öffne Xing-Profil: {url}")
            
            # Rate-Limiting
            self.rate_limiter.acquire('xing')
            
            # Profil öffnen
            page.goto(url, wait_until='domcontentloaded')
            page.wait_for_timeout(2000)
            
            # Tecis-Eintrag in Berufserfahrung suchen
            tecis_entry = self._find_tecis_entry(page)
            
            if not tecis_entry:
                logger.info("Kein Tecis-Eintrag in Xing Berufserfahrung gefunden")
                return None, True
            
            # Status prüfen ("bis heute")
            ist_aktiv = self._check_active_status(tecis_entry)
            
            if not ist_aktiv:
                # Bei LinkedIn=Active confirmed widerspricht Xing
                if flags.status_active_confirmed:
                    logger.info("Xing zeigt 'ehemalig', aber LinkedIn zeigte 'aktiv' - ignoriere Xing-Status")
                    ist_aktiv = True
                else:
                    logger.info("Person ist nicht mehr bei Tecis (ehemaliger Eintrag)")
                    return None, False
            
            logger.info("Person ist aktiv bei Tecis")
            
            # Stufe extrahieren
            stufe = self._extract_stufe(tecis_entry)
            
            if stufe:
                logger.info(f"Stufe gefunden: {stufe}")
                flags.stufe_gefunden = True
            else:
                logger.info("Keine gültige Stufe in Xing gefunden")
            
            return stufe, ist_aktiv
            
        except Exception as e:
            logger.error(f"Fehler beim Verarbeiten von Xing-Profil: {e}")
            return None, True
    
    def _find_tecis_entry(self, page: Page) -> Optional[any]:
        """Findet den Tecis-Eintrag in der Berufserfahrung"""
        try:
            # Xing nutzt keine class/experience – warte auf Seiteninhalt
            # 'load' statt 'networkidle' um Tracking/Analytics-Requests zu ignorieren
            page.wait_for_load_state('load', timeout=10000)
            page.wait_for_timeout(2000)
            
            # Variante 1: XPath – Tecis-Link und nächster Ancestor mit h4 (Stufe)
            xpaths = [
                '//a[contains(@href,"tecis")]/ancestor::*[.//h4][1]',
                '//a[contains(translate(text(),"TECIS","tecis"),"tecis")]/ancestor::*[.//h4][1]',
            ]
            for xpath in xpaths:
                try:
                    entries = page.query_selector_all(f'xpath={xpath}')
                    if entries:
                        logger.debug(f"Tecis-Eintrag via XPath gefunden")
                        return entries[0]
                except Exception:
                    pass
            
            # Variante 2: Tecis-Link direkt (Fallback für Stufe aus Headline)
            tecis_link = page.query_selector('a[href*="tecis"]')
            if tecis_link:
                return tecis_link
            
            # Variante 3: Alte Selektoren (eingeloggte Nutzer)
            for sel in ['[class*="experience"]', '[data-section="experience"]']:
                try:
                    section = page.query_selector(sel)
                    if section:
                        entries = section.query_selector_all('xpath=.//a[contains(translate(text(),"TECIS","tecis"),"tecis")]/ancestor::*[.//h4][1]')
                        if entries:
                            return entries[0]
                except Exception:
                    pass
            
            # Fallback: Tecis-Text auf Seite
            body_text = page.inner_text('body').lower()
            if 'tecis' in body_text:
                logger.debug("Tecis-Text auf Seite gefunden (Fallback)")
                return page.query_selector('main') or page.query_selector('body')
        
        except Exception as e:
            logger.debug(f"Fehler beim Suchen von Tecis-Eintrag: {e}")
        
        return None
    
    def _check_active_status(self, entry) -> bool:
        """Prüft ob Tecis-Eintrag noch aktiv ist (bis heute)"""
        try:
            text = entry.inner_text()
            return check_active_status(text)
        except:
            return True
    
    def _extract_stufe(self, entry) -> Optional[str]:
        """Extrahiert Stufe aus Tecis-Eintrag"""
        try:
            # data-mds="Headline" - Xing-Spezifikation
            stufe_element = entry.query_selector(f'h4[{XING_HEADLINE_ATTR}="{XING_HEADLINE_VALUE}"]')
            if not stufe_element:
                stufe_element = entry.query_selector('h4')
            
            # Wenn entry nur der Link ist: Stufe aus vorherigem h4 per evaluate
            if not stufe_element:
                try:
                    stufe_text_raw = entry.evaluate('''el => {
                        let prev = el.previousElementSibling;
                        while (prev) {
                            let h = prev.querySelector("h4") || (prev.tagName==="H4" ? prev : null);
                            if (h && h.innerText) return h.innerText.trim();
                            prev = prev.previousElementSibling;
                        }
                        let h = el.closest("main")?.querySelector("h4");
                        return h ? h.innerText.trim() : null;
                    }''')
                    if stufe_text_raw:
                        is_valid, category = categorize_stufe(stufe_text_raw)
                        if category in ["in_scope", "out_of_scope"]:
                            return stufe_text_raw
                except Exception:
                    pass
            
            if stufe_element:
                stufe_text = stufe_element.inner_text().strip()
                is_valid, category = categorize_stufe(stufe_text)
                if category in ["in_scope", "out_of_scope"]:
                    return stufe_text
                logger.debug(f"Stufe '{stufe_text}' - Kategorie: {category}")
        
        except Exception as e:
            logger.debug(f"Fehler beim Extrahieren der Stufe: {e}")
        
        return None
