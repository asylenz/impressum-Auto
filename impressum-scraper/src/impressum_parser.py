"""
Impressum-Parser: extrahiert Geschäftsführer-Name und Telefonnummer aus HTML.

Telefon-Priorität:
  1. <a href="tel:..."> — direkt aus Attribut
  2. Regex auf Plaintext — mit Kontext-Prüfung (nah an "Tel", "Telefon" etc.)

Geschäftsführer-Priorität:
  Regex-Pattern in dieser Reihenfolge:
  Geschäftsführer, Vertreten durch, Vertretungsberechtigter,
  Inhaber, CEO, Vorstand
"""

import re
import logging
from typing import Optional, Tuple

from bs4 import BeautifulSoup
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from src.utils import extract_phone_from_href, is_valid_phone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Regex-Patterns für Geschäftsführer
# ---------------------------------------------------------------------------

# Namens-Gruppe: Vorname + optional Mittelname/Initiale + Nachname
# Beispiele: "Max Müller", "Anna-Maria Schmidt", "Hans W. Mustermann"
_NAME = r"([A-ZÄÖÜ][a-zäöüß\-]+(?:\s+[A-ZÄÖÜ][\w\.\-]*)*\s+[A-ZÄÖÜ][a-zäöüß\-]+)"

GF_PATTERNS = [
    rf"Gesch[äa]ftsf[üu]hrer(?:in)?[:\s]+{_NAME}",
    rf"Vertreten\s+durch[:\s]+{_NAME}",
    rf"Vertretungsberechtigte?r?[:\s]+{_NAME}",
    rf"Inhaber(?:in)?[:\s]+{_NAME}",
    rf"CEO[:\s]+{_NAME}",
    rf"Vorstand[:\s]+{_NAME}",
    rf"Gesch[äa]ftsleitung[:\s]+{_NAME}",
    rf"Einzelkaufmann[:\s]+{_NAME}",
]

# ---------------------------------------------------------------------------
# Telefon — Regex auf Plaintext
# ---------------------------------------------------------------------------

# +49 oder 0, gefolgt von mind. 7 Ziffern/Leerzeichen/Trennzeichen
PHONE_PATTERN = re.compile(r"(\+49|0)[0-9\s\-\/\(\)]{7,20}")

# Kontext-Keywords die auf Telefon (positiv) hinweisen
TEL_KEYWORDS_POS = {"tel", "telefon", "fon", "phone", "t:", "ruf", "call"}

# Kontext-Keywords die auf Fax hinweisen → ausschließen
TEL_KEYWORDS_NEG = {"fax", "f:", "telefax"}


# ---------------------------------------------------------------------------
# Interne Hilfsfunktionen
# ---------------------------------------------------------------------------

def _extract_phone_from_tel_links(soup: BeautifulSoup) -> Optional[str]:
    """
    Sucht <a href="tel:..."> Tags und extrahiert die Nummer direkt aus
    dem href-Attribut (höchste Zuverlässigkeit).
    """
    for tag in soup.find_all("a", href=True):
        href = tag.get("href", "")
        if href.lower().startswith("tel:"):
            phone = extract_phone_from_href(href).strip()
            if phone and is_valid_phone(phone):
                logger.debug(f"Telefon aus tel:-Link: {phone}")
                return phone
    return None


def _is_phone_in_tel_context(text: str, match_start: int, match_end: int) -> bool:
    """
    Prüft ob ein Regex-Match für eine Telefonnummer in der Nähe von
    Telefon-Keywords steht und kein Fax ist.

    Kontext-Fenster: 80 Zeichen vor dem Match, 30 Zeichen danach.
    """
    ctx_before = text[max(0, match_start - 80) : match_start].lower()
    ctx_after = text[match_end : match_end + 30].lower()
    context = ctx_before + ctx_after

    # Fax ausschließen
    for neg in TEL_KEYWORDS_NEG:
        if neg in context:
            return False

    # Telefon-Kontext vorhanden?
    for pos in TEL_KEYWORDS_POS:
        if pos in context:
            return True

    return False


def _extract_phone_from_text(text: str) -> Optional[str]:
    """Sucht Telefonnummer per Regex im Plaintext, prüft Kontext."""
    for match in PHONE_PATTERN.finditer(text):
        if _is_phone_in_tel_context(text, match.start(), match.end()):
            phone = match.group().strip()
            logger.debug(f"Telefon per Regex: {phone}")
            return phone
    return None


def _extract_geschaeftsfuehrer(text: str) -> str:
    """
    Extrahiert Geschäftsführer-Namen per Regex.
    Mehrere Namen (z.B. GmbH mit 2 GFs) werden mit Komma getrennt.
    """
    found: list[str] = []
    for pattern in GF_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            name = match.group(1).strip()
            # Trailing-Punkt oder Komma entfernen
            name = name.rstrip(".,")
            if name and name not in found:
                found.append(name)
                # Pro Pattern nur den ersten Treffer nehmen, um Dopplungen zu vermeiden
                break

    if found:
        result = ", ".join(found)
        logger.debug(f"Geschäftsführer gefunden: {result}")
        return result
    return ""


# ---------------------------------------------------------------------------
# Öffentliche Funktion
# ---------------------------------------------------------------------------

def parse_impressum(
    url: str, page: Page, timeout_ms: int = 10000
) -> Tuple[str, str]:
    """
    Lädt die Impressum-URL und extrahiert Geschäftsführer + Telefonnummer.

    Args:
        url:        Vollständige Impressum-URL
        page:       Playwright-Page-Objekt
        timeout_ms: Timeout in Millisekunden

    Returns:
        Tuple (geschaeftsfuehrer: str, telefonnummer: str)
        Leere Strings wenn nicht gefunden.
    """
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        html = page.content()
    except PlaywrightTimeout:
        logger.warning(f"Timeout beim Laden von: {url}")
        return "", ""
    except Exception as e:
        logger.warning(f"Fehler beim Laden von {url}: {e}")
        return "", ""

    soup = BeautifulSoup(html, "html.parser")

    # -----------------------------------------------------------------------
    # Telefonnummer
    # -----------------------------------------------------------------------
    # Priorität 1: tel:-Links
    phone = _extract_phone_from_tel_links(soup)

    # Priorität 2: Regex auf Plaintext
    if not phone:
        plain_text = soup.get_text(separator="\n")
        phone = _extract_phone_from_text(plain_text)

    # -----------------------------------------------------------------------
    # Geschäftsführer
    # -----------------------------------------------------------------------
    plain_text = soup.get_text(separator="\n")
    gf = _extract_geschaeftsfuehrer(plain_text)

    return gf, phone
