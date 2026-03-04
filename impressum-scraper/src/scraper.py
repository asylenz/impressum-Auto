"""
Haupt-Scraping-Logik: orchestriert Website-Suche, Impressum-Finder und Parser.

ImpressumScraper:
- Verwaltet einen Playwright-Browser-Kontext für alle Firmen
- Ruft der Reihe nach search → impressum_finder → impressum_parser auf
- Gibt FirmenResult zurück (inkl. Status-Code bei Fehlern)
"""

import logging
from typing import Optional

from playwright.sync_api import (
    sync_playwright,
    Browser,
    BrowserContext,
    Page,
    TimeoutError as PlaywrightTimeout,
)

from src.config import Config
from src.models import FirmenResult
from src.rate_limiter import RateLimiter
from src.search import find_company_website
from src.impressum_finder import find_impressum_url
from src.impressum_parser import parse_impressum

logger = logging.getLogger(__name__)


class ImpressumScraper:
    """
    Context-Manager der einen Playwright-Browser öffnet und für jede Firma
    die drei Scraping-Schritte ausführt.

    Verwendung:
        with ImpressumScraper(config) as scraper:
            result = scraper.scrape("Mustermann GmbH")
    """

    def __init__(self, config: Config):
        self.config = config
        self.rate_limiter = RateLimiter(config)
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    # -----------------------------------------------------------------------
    # Context Manager
    # -----------------------------------------------------------------------

    def __enter__(self) -> "ImpressumScraper":
        self._start_browser()
        return self

    def __exit__(self, *_) -> None:
        self._stop_browser()

    def _start_browser(self) -> None:
        headless = self.config.get("browser.headless", True)
        user_agent = self.config.get(
            "browser.user_agent",
            (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        timeout_ms = self.config.get("browser.timeout", 10000)

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=headless)
        self._context = self._browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1280, "height": 800},
            # SSL-Fehler tolerieren (selbstsignierte Zertifikate auf manchen Sites)
            ignore_https_errors=True,
        )
        self.page = self._context.new_page()
        self.page.set_default_timeout(timeout_ms)
        logger.debug(f"Browser gestartet (headless={headless})")

    def _stop_browser(self) -> None:
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception as e:
            logger.debug(f"Fehler beim Schließen des Browsers: {e}")
        logger.debug("Browser gestoppt")

    # -----------------------------------------------------------------------
    # Haupt-Methode
    # -----------------------------------------------------------------------

    def scrape(self, firmenname: str, website_hint: str = "") -> FirmenResult:
        """
        Verarbeitet eine Firma in drei Schritten:

        1. Website-URL ermitteln — falls website_hint übergeben wird, entfällt die Google-Suche
        2. Impressum-URL auf der Website finden
        3. Geschäftsführer + Telefonnummer aus dem Impressum extrahieren

        Gibt immer ein FirmenResult zurück — auch bei Fehlern (dann mit Status-Code).
        """
        result = FirmenResult(firmenname=firmenname)
        timeout_ms: int = self.config.get("browser.timeout", 10000)

        # -------------------------------------------------------------------
        # Schritt 1: Website ermitteln
        # -------------------------------------------------------------------
        if website_hint:
            # Website bereits bekannt → Google-Suche überspringen
            from src.search import get_base_url
            website = get_base_url(website_hint) if website_hint.startswith("http") else website_hint
            logger.info(f"[1/3] Website aus CSV übernommen: {website}")
        else:
            logger.info(f"[1/3] Suche Website für: {firmenname}")
            try:
                website = find_company_website(
                    firmenname,
                    self.config,
                    self.rate_limiter,
                    playwright_page=self.page,
                )
            except Exception as e:
                logger.error(f"Unerwarteter Fehler bei Website-Suche für '{firmenname}': {e}")
                result.status = "keine Website"
                return result

            if not website:
                result.status = "keine Website"
                return result

        result.website = website
        self.rate_limiter.wait_between_requests()

        # -------------------------------------------------------------------
        # Schritt 2: Impressum-URL finden
        # -------------------------------------------------------------------
        logger.info(f"[2/3] Suche Impressum auf: {website}")
        try:
            impressum_url = find_impressum_url(website, self.page, timeout_ms)
        except PlaywrightTimeout:
            logger.warning(f"Timeout bei Impressum-Suche für '{firmenname}'")
            result.status = "timeout"
            return result
        except Exception as e:
            logger.error(f"Fehler bei Impressum-Suche für '{firmenname}': {e}")
            result.status = "kein Impressum"
            return result

        if not impressum_url:
            result.status = "kein Impressum"
            return result

        result.impressum_url = impressum_url
        self.rate_limiter.wait_between_requests()
        self.rate_limiter.record_and_maybe_pause()

        # -------------------------------------------------------------------
        # Schritt 3: GF + Telefon extrahieren
        # -------------------------------------------------------------------
        logger.info(f"[3/3] Parse Impressum: {impressum_url}")
        try:
            gf, phone = parse_impressum(impressum_url, self.page, timeout_ms)
        except PlaywrightTimeout:
            logger.warning(f"Timeout beim Parsen von '{impressum_url}'")
            result.status = "timeout"
            return result
        except Exception as e:
            logger.error(f"Fehler beim Parsen von '{impressum_url}': {e}")
            result.status = "kein Ergebnis"
            return result

        result.geschaeftsfuehrer = gf
        result.telefonnummer = phone
        result.status = "OK" if (gf or phone) else "kein Ergebnis"

        return result
