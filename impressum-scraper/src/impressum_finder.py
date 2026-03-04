"""
Impressum-URL-Finder.

Strategie (in dieser Reihenfolge):
1. Häufige Pfade direkt per HEAD-Request prüfen
2. Homepage per Playwright laden → Links mit "impressum" suchen
3. /kontakt und /about per Playwright laden → ebenfalls Links suchen
"""

import logging
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

# Häufige Impressum-Pfade, in dieser Priorität abgeprüft
COMMON_IMPRESSUM_PATHS = [
    "/impressum",
    "/impressum.html",
    "/impressum/",
    "/de/impressum",
    "/ueber-uns/impressum",
    "/rechtliches/impressum",
    "/legal/impressum",
    "/imprint",
    "/imprint.html",
    "/de/imprint",
    "/rechtliches",
    "/legal",
]

# Fallback-Seiten, auf denen oft Impressum-Links zu finden sind
FALLBACK_PATHS = ["/kontakt", "/about", "/ueber-uns", "/contact"]

_SESSION = requests.Session()
_SESSION.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
)


def _url_exists(url: str, timeout: int = 5) -> bool:
    """
    Prüft per HEAD-Request ob eine URL mit Status < 400 antwortet.
    Folgt Redirects, ignoriert SSL-Fehler.
    """
    try:
        resp = _SESSION.head(
            url,
            timeout=timeout,
            allow_redirects=True,
            verify=False,
        )
        return resp.status_code < 400
    except Exception:
        return False


def _find_impressum_link_in_html(html: str, base_url: str) -> Optional[str]:
    """
    Sucht in HTML nach <a>-Tags die 'impressum' oder 'imprint' im href oder
    Link-Text enthalten (case-insensitive).
    Gibt die absolute URL zurück oder None.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all("a", href=True):
            href = tag.get("href", "").lower()
            text = tag.get_text(separator=" ").lower().strip()
            if "impressum" in href or "imprint" in href:
                return urljoin(base_url, tag["href"])
            if "impressum" in text and len(text) < 50:
                return urljoin(base_url, tag["href"])
    except Exception as e:
        logger.debug(f"HTML-Parsing Fehler in _find_impressum_link_in_html: {e}")
    return None


def _load_and_search(page: Page, url: str, base_url: str, timeout_ms: int) -> Optional[str]:
    """
    Lädt eine Seite mit Playwright und sucht nach Impressum-Links im HTML.
    Gibt gefundene absolute URL zurück oder None bei Fehler/nicht gefunden.
    """
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        html = page.content()
        return _find_impressum_link_in_html(html, base_url)
    except PlaywrightTimeout:
        logger.debug(f"Timeout beim Laden von: {url}")
        return None
    except Exception as e:
        logger.debug(f"Fehler beim Laden von {url}: {e}")
        return None


def find_impressum_url(
    base_url: str, page: Page, timeout_ms: int = 5000
) -> Optional[str]:
    """
    Findet die Impressum-URL für eine gegebene Website.

    Args:
        base_url:   Basis-URL der Firma, z.B. https://www.mustermann.de
        page:       Playwright-Page-Objekt (bereits geöffnet)
        timeout_ms: Timeout pro Seitenaufruf in Millisekunden

    Returns:
        Vollständige Impressum-URL oder None wenn nicht gefunden.
    """
    base_url = base_url.rstrip("/")

    # -----------------------------------------------------------------------
    # Schritt 1: Bekannte Pfade direkt prüfen (schnell, kein Browser nötig)
    # -----------------------------------------------------------------------
    logger.debug(f"Prüfe {len(COMMON_IMPRESSUM_PATHS)} bekannte Impressum-Pfade für {base_url}")
    for path in COMMON_IMPRESSUM_PATHS:
        candidate = base_url + path
        if _url_exists(candidate):
            logger.info(f"Impressum direkt gefunden: {candidate}")
            return candidate

    # -----------------------------------------------------------------------
    # Schritt 2: Homepage laden und Links durchsuchen
    # -----------------------------------------------------------------------
    logger.debug(f"Lade Homepage und suche Links: {base_url}")
    link = _load_and_search(page, base_url, base_url, timeout_ms * 2)
    if link:
        logger.info(f"Impressum via Homepage-Link gefunden: {link}")
        return link

    # -----------------------------------------------------------------------
    # Schritt 3: Fallback — /kontakt, /about etc. laden und Links durchsuchen
    # -----------------------------------------------------------------------
    logger.debug(f"Versuche Fallback-Seiten für {base_url}")
    for path in FALLBACK_PATHS:
        candidate = base_url + path
        if _url_exists(candidate):
            link = _load_and_search(page, candidate, base_url, timeout_ms)
            if link:
                logger.info(f"Impressum via Fallback-Seite '{path}' gefunden: {link}")
                return link

    logger.warning(f"Kein Impressum gefunden für {base_url}")
    return None
