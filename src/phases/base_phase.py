"""
Base-Klasse für alle Scraping-Phasen
"""

import logging
from typing import Optional, List
from playwright.sync_api import Page

from src.config import Config
from src.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class BasePhase:
    """Basis-Klasse für alle Scraping-Phasen mit gemeinsamer Logik"""
    
    def __init__(self, config: Config, rate_limiter: RateLimiter, platform: str):
        """
        Args:
            config: Konfigurationsobjekt
            rate_limiter: Rate-Limiter-Instanz
            platform: Plattform-Name für Rate-Limiting ('tecis', 'linkedin', 'xing', 'creditreform')
        """
        self.config = config
        self.rate_limiter = rate_limiter
        self.platform = platform
        self.valid_stufen = config.valid_stufen
    
    def navigate_with_rate_limit(self, page: Page, url: str) -> bool:
        """
        Navigiert zur URL mit Rate-Limiting und Fehlerbehandlung
        
        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            logger.info(f"Öffne {self.platform.capitalize()}-Seite: {url}")
            
            # Rate-Limiting
            self.rate_limiter.acquire(self.platform)
            
            # Navigation
            page.goto(url, wait_until='domcontentloaded')
            page.wait_for_timeout(2000)  # Kurze Pause für JS-Rendering
            
            return True
        except Exception as e:
            logger.error(f"Fehler beim Öffnen der {self.platform}-Seite: {e}")
            return False
    
    def safe_query_selector(self, page_or_element, selector: str) -> Optional[any]:
        """
        Sichere Selektor-Abfrage mit Fehlerbehandlung
        
        Returns:
            Element oder None
        """
        try:
            return page_or_element.query_selector(selector)
        except Exception as e:
            logger.debug(f"Selektor fehlgeschlagen ({selector}): {e}")
            return None
    
    def safe_query_selector_all(self, page_or_element, selector: str) -> List[any]:
        """
        Sichere Selektor-Abfrage (alle Treffer) mit Fehlerbehandlung
        
        Returns:
            Liste von Elementen (leer bei Fehler)
        """
        try:
            return page_or_element.query_selector_all(selector)
        except Exception as e:
            logger.debug(f"Selektor fehlgeschlagen ({selector}): {e}")
            return []
    
    def safe_inner_text(self, element, default: str = "") -> str:
        """
        Extrahiert Text sicher aus Element
        
        Returns:
            Text oder default
        """
        try:
            if element:
                return element.inner_text().strip()
            return default
        except Exception:
            return default
