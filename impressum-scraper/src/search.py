"""
Website-URL-Suche via Serper API (primär) oder Playwright Google (Fallback).
Adaptiert aus BK-Automatisierung/src/discovery/search_provider.py.
"""

import logging
import os
import time
from typing import List, Optional
from urllib.parse import urlparse

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from src.models import SearchResult

logger = logging.getLogger(__name__)

# Domains die keine echten Firmen-Websites sind (Verzeichnisse, Social Media, …)
BLOCKED_DOMAINS = [
    "facebook.com",
    "twitter.com",
    "instagram.com",
    "linkedin.com",
    "xing.com",
    "youtube.com",
    "wikipedia.org",
    "gelbeseiten.de",
    "dasoertliche.de",
    "wlocalbook.de",
    "companyhouse.de",
    "northdata.de",
    "bundesanzeiger.de",
    "handelsregister.de",
    "creditreform.de",
    "dun.com",
    "google.com",
    "bing.com",
    "trustpilot.com",
    "kununu.com",
    "indeed.com",
    "stepstone.de",
    "yelp.de",
    "11880.com",
    "hotfrog.de",
    "firmenwissen.de",
    "unternehmensregister.de",
    "moneyhouse.de",
    "cylex.de",
    "werkennt.de",
    "meinestadt.de",
]


def is_valid_company_url(url: str) -> bool:
    """Gibt True zurück wenn URL eine echte Firmen-Website sein könnte"""
    if not url or not url.startswith("http"):
        return False
    url_lower = url.lower()
    for blocked in BLOCKED_DOMAINS:
        if blocked in url_lower:
            return False
    return True


def get_base_url(url: str) -> str:
    """Extrahiert Basis-URL (Schema + Domain), z.B. https://www.firma.de"""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


# ---------------------------------------------------------------------------
# Serper API
# ---------------------------------------------------------------------------

class SerperSearch:
    """Google-Suche via Serper API — keine CAPTCHA-Probleme, 2500 Suchen/Monat gratis"""

    def __init__(self, config):
        self.config = config
        self.api_key = os.getenv("SERPER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "SERPER_API_KEY nicht in .env gesetzt! "
                "Kostenlosen Key holen: https://serper.dev"
            )

    def search(self, query: str) -> List[SearchResult]:
        import requests as req

        try:
            logger.debug(f"Serper-Suche: {query}")
            response = req.post(
                "https://google.serper.dev/search",
                json={"q": query, "num": 5, "gl": "de", "hl": "de"},
                headers={
                    "X-API-KEY": self.api_key,
                    "Content-Type": "application/json",
                },
                timeout=10,
            )

            if response.status_code != 200:
                logger.error(
                    f"Serper API Fehler {response.status_code}: {response.text[:200]}"
                )
                if "Not enough credits" in response.text:
                    logger.critical(
                        "Serper API Credits aufgebraucht! "
                        "Bitte neuen Key auf https://serper.dev holen."
                    )
                return []

            results: List[SearchResult] = []
            for item in response.json().get("organic", [])[:5]:
                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                    )
                )
            logger.debug(f"{len(results)} Ergebnisse von Serper API")
            return results

        except Exception as e:
            logger.error(f"Serper API Fehler: {e}")
            return []


# ---------------------------------------------------------------------------
# Playwright Google (Fallback)
# ---------------------------------------------------------------------------

class PlaywrightSearch:
    """
    Google-Suche direkt via Playwright-Browser.
    Wird als Fallback verwendet wenn Serper API nicht verfügbar ist.
    Adaptiert aus BK-Automatisierung/src/discovery/search_provider.py.
    """

    def __init__(self, config, page: Page):
        self.config = config
        self.page = page
        self._consent_handled = False

    def _handle_consent(self):
        """Behandelt Google Consent-Dialog (einmalig pro Session)"""
        if self._consent_handled:
            return
        try:
            for selector in [
                'button:has-text("Alle akzeptieren")',
                'button:has-text("Accept all")',
                'button:has-text("Alles akzeptieren")',
                "#L2AGLb",
                'button:has-text("Ich stimme zu")',
            ]:
                try:
                    self.page.wait_for_selector(selector, timeout=2000)
                    self.page.click(selector)
                    time.sleep(1)
                    self._consent_handled = True
                    logger.debug(f"Google Consent akzeptiert: {selector}")
                    return
                except PlaywrightTimeout:
                    continue
        except Exception:
            pass

    def search(self, query: str) -> List[SearchResult]:
        try:
            logger.debug(f"Playwright Google-Suche: {query}")
            self.page.goto(
                "https://www.google.com",
                wait_until="domcontentloaded",
                timeout=15000,
            )
            self._handle_consent()

            # Suchfeld finden und Query eingeben
            self.page.wait_for_selector(
                'textarea[name="q"], input[name="q"]', timeout=5000
            )
            self.page.fill('textarea[name="q"], input[name="q"]', query)
            self.page.keyboard.press("Enter")

            # Auf Ergebnisse warten
            for selector in ["div#search div.g", "div#rso div.g", "#rso"]:
                try:
                    self.page.wait_for_selector(selector, timeout=5000)
                    break
                except PlaywrightTimeout:
                    continue

            results: List[SearchResult] = []
            for container in self.page.query_selector_all("div.g")[:5]:
                try:
                    link = container.query_selector("a[href]:not([href^='/'])")
                    if not link:
                        continue
                    url = link.get_attribute("href") or ""
                    if not url or url.startswith("/") or "google.com" in url:
                        continue
                    title_el = link.query_selector("h3")
                    title = title_el.inner_text() if title_el else ""
                    results.append(SearchResult(title=title, url=url))
                except Exception:
                    continue

            logger.debug(f"{len(results)} Ergebnisse von Playwright Google")
            return results

        except Exception as e:
            logger.error(f"Playwright Google Fehler: {e}")
            return []


# ---------------------------------------------------------------------------
# Öffentliche Funktion
# ---------------------------------------------------------------------------

def find_company_website(
    firmenname: str,
    config,
    rate_limiter,
    playwright_page: Optional[Page] = None,
) -> Optional[str]:
    """
    Findet die offizielle Website einer Firma.

    Suchstrategie:
    1. Serper API (falls SERPER_API_KEY gesetzt und use_serper=true in config)
    2. Playwright Google als Fallback

    Gibt die Basis-URL zurück (z.B. https://www.mustermann.de) oder None.
    """
    query = f"{firmenname} Impressum"
    use_serper = config.get("discovery.use_serper", True)
    results: List[SearchResult] = []

    # Serper API — primärer Provider
    if use_serper:
        try:
            results = SerperSearch(config).search(query)
        except ValueError as e:
            logger.warning(f"Serper nicht verfügbar ({e}) — nutze Playwright Fallback")

    # Playwright Google — Fallback
    if not results and playwright_page is not None:
        results = PlaywrightSearch(config, playwright_page).search(query)

    rate_limiter.wait_between_requests()

    for result in results:
        if is_valid_company_url(result.url):
            base = get_base_url(result.url)
            logger.info(f"Website gefunden: {base} (via '{result.title[:60]}')")
            return base

    logger.warning(f"Keine valide Website für '{firmenname}' gefunden")
    return None
