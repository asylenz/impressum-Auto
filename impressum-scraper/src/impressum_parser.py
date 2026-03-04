"""
Impressum-Parser: extrahiert Geschäftsführer-Name und Telefonnummer.

Telefon-Strategie (Priorität):
  1. <a href="tel:+49..."> oder <a href="tel:0...">
  2. Regex auf Plaintext — mit Kontext-Prüfung (nahe an Tel/Telefon/Fon/T:)

Geschäftsführer-Strategie:
  - Zeile mit GF-Schlüsselwort finden
  - Text NACH dem Schlüsselwort nehmen
  - Wörter sammeln bis Blacklist-Wort, Ziffer oder Satzzeichen stoppt
  - Nur echte Personennamen (mind. Vor- + Nachname) werden zurückgegeben
"""

import re
import logging
from typing import Optional, Tuple, List

from bs4 import BeautifulSoup
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from src.utils import extract_phone_from_href, is_valid_phone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TELEFON
# ---------------------------------------------------------------------------

# Allgemeines Telefonnummer-Pattern — deckt alle deutschen Formate ab:
# +49 89 123456 | +49 (0) 89 123456 | 0049 89 123456
# (089) 123456  | 089/123456        | 089 / 12 34 56
PHONE_PATTERN = re.compile(
    r'(?:'
    r'\+49[\s\.\-\/\(\)]{0,6}'      # +49 ...
    r'|0049[\s\.\-\/\(\)]{0,6}'     # 0049 ...
    r'|\(?0\d{2,5}\)?[\s\.\-\/]{0,5}'  # 0xx(x) ...
    r')'
    r'\d[\d\s\.\-\/\(\)]{4,20}\d',
    re.ASCII
)

# Positiver Kontext: Nummer muss neben Telefon-Keyword stehen
TEL_CONTEXT_POS = re.compile(
    r'(tel\.?|telefon|fon|phone|t\s*:|ruf|call|mobil|handy|mobile|☎|📞)',
    re.IGNORECASE
)

# Negativer Kontext: Fax-Nummern ausschließen
FAX_CONTEXT_NEG = re.compile(
    r'(fax|telefax|f\s*:)',
    re.IGNORECASE
)


def _extract_phone_from_tel_links(soup: BeautifulSoup) -> Optional[str]:
    """
    Höchste Priorität: <a href="tel:+49..."> oder <a href="tel:0...">
    Fax-Links werden anhand des Kontext-Texts ausgeschlossen.
    """
    for tag in soup.find_all("a", href=True):
        href = tag.get("href", "").strip()
        if not href.lower().startswith("tel:"):
            continue

        phone = extract_phone_from_href(href).strip()
        if not phone:
            continue
        if not (phone.startswith("+49") or phone.startswith("0049") or phone.startswith("0")):
            continue

        # Fax-Link ausschließen
        link_text = tag.get_text().lower()
        parent_text = (tag.parent.get_text().lower() if tag.parent else "")
        if FAX_CONTEXT_NEG.search(link_text + " " + parent_text):
            logger.debug(f"tel:-Link als Fax erkannt: {href}")
            continue

        if is_valid_phone(phone):
            logger.debug(f"Telefon aus tel:-Link: {phone}")
            return phone

    return None


def _extract_phone_from_text(text: str) -> Optional[str]:
    """
    Sucht Telefonnummer per Regex im Plaintext.
    Nur Treffer die nahe an einem Telefon-Keyword stehen.
    FAX-Prüfung nur auf den Text VOR der Nummer (nicht danach).
    """
    for match in PHONE_PATTERN.finditer(text):
        start, end = match.start(), match.end()
        # Kontext VOR der Nummer (für Tel-Keyword + Fax-Ausschluss)
        ctx_before = text[max(0, start - 80):start]

        # Fax ausschließen — nur Kontext VOR der Nummer prüfen
        if FAX_CONTEXT_NEG.search(ctx_before):
            continue

        # Telefon-Keyword muss in der Nähe stehen
        # (80 Zeichen vor + 20 Zeichen nach — z.B. "Tel.:" steht manchmal nach dem Keyword auf nächster Zeile)
        ctx_around = ctx_before + text[end:end + 20]
        if not TEL_CONTEXT_POS.search(ctx_around):
            continue

        phone = match.group().strip()
        digits = re.sub(r'\D', '', phone)
        if len(digits) < 7:
            continue

        logger.debug(f"Telefon per Regex: {phone}")
        return phone

    return None


def extract_phone(soup: BeautifulSoup, plain_text: str) -> str:
    """Gibt beste gefundene Telefonnummer zurück (tel:-Link > Regex)"""
    return _extract_phone_from_tel_links(soup) or _extract_phone_from_text(plain_text) or ""


# ---------------------------------------------------------------------------
# GESCHÄFTSFÜHRER
# ---------------------------------------------------------------------------

# Schlüsselwörter die auf GF-Angabe hinweisen
GF_KEYWORDS = re.compile(
    r'(Gesch[äa]ftsf[üu]hrer(?:in)?|Vertreten\s+durch|'
    r'Vertretungsberechtigte?r?|Inhaber(?:in)?|'
    r'Gesch[äa]ftsleitung|CEO|Vorstand|Einzelkaufmann)',
    re.IGNORECASE
)

# Wörter die KEIN Personenname sind — Stop-Wörter
NAME_BLACKLIST = {
    # Artikel, Pronomen, Konjunktionen
    "die", "der", "das", "ein", "eine", "des", "dem", "den", "wir",
    "und", "oder", "für", "mit", "nach", "durch", "von", "zu",
    "bei", "aus", "an", "auf", "in", "im", "ist", "sind",
    # Juristische / Impressum-Begriffe
    "verantwortlich", "inhalte", "redaktionelle", "team", "kontakt",
    "registereintrag", "umsatzsteuer", "identifikationsnummer",
    "impressum", "gesellschaft", "verwaltung", "leitung",
    "geschäftsführung", "presse", "marketing", "vertrieb",
    "technik", "service", "support", "beratung", "planung",
    "haftungsbeschränkt", "handelsregister", "amtsgericht",
    # Positionsbezeichnungen
    "geschäftsführer", "inhaber", "vorstand", "ansprechpartner",
    "herr", "frau", "beide", "jeweils", "allein", "gemeinsam",
    # Abkürzungen
    "tel", "fon", "fax", "mob", "web", "str", "nr", "ust",
    "gmbh", "ag", "kg", "ohg", "gbr", "mbh",
    # Englisch
    "managing", "director", "chief", "officer", "executive",
}

# Erlaubte Vorsätze (Adelstitel) — zählen nicht als blacklisted
ALLOWED_PREFIXES = {"von", "van", "de", "der", "den", "el", "al", "zu"}


def _collect_name_words(text_after_keyword: str) -> List[str]:
    """
    Sammelt Namens-Wörter aus dem Text direkt nach dem GF-Schlüsselwort.
    Stoppt sobald ein Blacklist-Wort, eine Ziffer oder ein Satzzeichen kommt.
    Gibt nur die Wörter zurück, nicht den Rest.
    """
    # Erst bis zum nächsten sinnvollen Trennzeichen kürzen
    # (Komma → könnte mehrere Namen enthalten, Newline/| → sicher Ende)
    segments = re.split(r'[\n\r\|]', text_after_keyword)
    candidate_text = segments[0][:80] if segments else ""

    words = candidate_text.split()
    collected: List[str] = []

    for word in words:
        # Satzzeichen am Rand entfernen
        clean_raw = word.strip(".,;:()[]")
        if not clean_raw:
            continue

        clean = clean_raw.lower()

        # Erlaubte Vorsätze
        if clean in ALLOWED_PREFIXES:
            collected.append(clean_raw)
            continue

        # Blacklist → sofort stoppen
        if clean in NAME_BLACKLIST:
            break

        # Nur Buchstaben und Bindestrich erlaubt
        if not re.match(r'^[A-ZÄÖÜa-zäöüß\-]+$', clean_raw):
            break

        # Muss mit Großbuchstabe beginnen
        if not clean_raw[0].isupper():
            break

        # Mindestlänge
        if len(clean) < 2:
            continue

        collected.append(clean_raw)

    return collected


def extract_geschaeftsfuehrer(plain_text: str) -> str:
    """
    Findet alle GF-Namen im Text.
    Strategie: GF-Keyword-Zeile finden → Text nach Keyword nehmen →
    Wörter sammeln → nur echte 2-Wort-Namen zurückgeben.
    """
    found: List[str] = []
    lines = plain_text.split('\n')

    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not GF_KEYWORDS.search(line_stripped):
            continue

        # Text nach dem GF-Keyword extrahieren
        kw_match = GF_KEYWORDS.search(line_stripped)
        text_after = line_stripped[kw_match.end():]

        # Doppelpunkt und Leerzeichen am Anfang entfernen
        text_after = re.sub(r'^[\s:,]+', '', text_after)

        # Falls nach dem Keyword nichts steht → nächste Zeile nehmen
        if not text_after.strip() and i + 1 < len(lines):
            text_after = lines[i + 1].strip()

        if not text_after.strip():
            continue

        # Kann auch mehrere Namen per Komma enthalten: "Max Müller, Anna Schmidt"
        # Jeden Segment (getrennt durch Komma) einzeln prüfen
        name_segments = re.split(r',\s*', text_after)
        for segment in name_segments:
            words = _collect_name_words(segment)
            if len(words) >= 2:
                name = " ".join(words)
                if name not in found:
                    logger.debug(f"GF-Name akzeptiert: '{name}'")
                    found.append(name)

    result = ", ".join(found) if found else ""
    if result:
        logger.info(f"Geschäftsführer gefunden: {result}")
    return result


# ---------------------------------------------------------------------------
# Öffentliche Hauptfunktion
# ---------------------------------------------------------------------------

def parse_impressum(url: str, page: Page, timeout_ms: int = 10000) -> Tuple[str, str]:
    """
    Lädt Impressum-URL und extrahiert Geschäftsführer + Telefonnummer.

    Returns:
        Tuple (geschaeftsfuehrer: str, telefonnummer: str)
        Leere Strings wenn nicht gefunden.
    """
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        html = page.content()
    except PlaywrightTimeout:
        logger.warning(f"Timeout: {url}")
        return "", ""
    except Exception as e:
        logger.warning(f"Fehler beim Laden von {url}: {e}")
        return "", ""

    soup = BeautifulSoup(html, "html.parser")
    plain_text = soup.get_text(separator="\n")

    phone = extract_phone(soup, plain_text)
    gf    = extract_geschaeftsfuehrer(plain_text)

    return gf, phone
