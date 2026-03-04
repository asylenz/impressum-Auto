"""
Impressum-Parser: extrahiert Geschäftsführer-Name und Telefonnummer.

Extraktion via Gemini 2.0 Flash (primär) mit Regex als Fallback.

Telefon-Strategie (Priorität):
  1. Gemini 2.0 Flash
  2. <a href="tel:+49..."> oder <a href="tel:0...">
  3. Regex auf Plaintext — mit Kontext-Prüfung (nahe an Tel/Telefon/Fon/T:)

Geschäftsführer-Strategie:
  1. Gemini 2.0 Flash
  2. Regex: GF-Schlüsselwort finden → Namen-Wörter sammeln
"""

import os
import re
import logging
from typing import Optional, Tuple, List

from bs4 import BeautifulSoup
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from src.utils import extract_phone_from_href, is_valid_phone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# GEMINI FLASH EXTRAKTION (primär)
# ---------------------------------------------------------------------------

def _extract_with_gemini(plain_text: str) -> Tuple[str, str]:
    """
    Verwendet Gemini 3 Flash um GF-Name und Telefonnummer zu extrahieren.
    Gibt ("", "") zurück wenn kein API Key vorhanden oder Fehler auftritt.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        logger.debug("GEMINI_API_KEY nicht gesetzt — Gemini wird übersprungen")
        return "", ""

    try:
        from google import genai

        client = genai.Client(api_key=api_key)

        # Text auf 4000 Zeichen begrenzen (Impressum-relevanter Teil)
        text = plain_text[:4000]

        prompt = f"""Analysiere diesen deutschen Impressum-Text und extrahiere genau:

1. Den Namen des Geschäftsführers / Vertreters / Inhabers
   - Nur Vor- und Nachname (z.B. "Max Mustermann")
   - Mehrere Namen mit Komma trennen (z.B. "Max Müller, Anna Schmidt")
   - Keine Titel (Dr., Prof.), keine Positionsbezeichnungen
   - Falls nicht vorhanden: leer lassen

2. Die Telefonnummer
   - Bevorzugt +49 oder 0xxx Format
   - Kein Fax
   - Falls nicht vorhanden: leer lassen

Antworte NUR in exakt diesem Format (sonst nichts):
GF: <Name oder leer>
TEL: <Nummer oder leer>

Impressum-Text:
{text}"""

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
        )
        answer = response.text.strip()

        gf = ""
        tel = ""
        for line in answer.splitlines():
            line = line.strip()
            if line.upper().startswith("GF:"):
                gf = line[3:].strip()
            elif line.upper().startswith("TEL:"):
                tel = line[4:].strip()

        # Nur die erste Zeile des Wertes nehmen (Gemini kann manchmal mehrzeilig antworten)
        gf = gf.splitlines()[0].strip() if gf else ""
        tel = tel.splitlines()[0].strip() if tel else ""

        # Platzhalter-Werte und Nicht-Name-Anhängsel bereinigen
        _empty_vals = {"leer", "unbekannt", "-", "n/a", "keine angabe", "nicht vorhanden",
                       "nicht angegeben", "keine", ""}
        if gf.lower() in _empty_vals:
            gf = ""
        if tel.lower() in _empty_vals:
            tel = ""

        # Sicherheitscheck: GF-Feld darf keine Wörter wie Tel/Kontakt/Fax enthalten
        if gf and re.search(r'\b(tel|fax|kontakt|telefon|fon|@|www\.|http)\b', gf, re.IGNORECASE):
            logger.debug(f"Gemini GF enthält unerwünschte Wörter, verwerfe: '{gf}'")
            gf = ""

        if gf or tel:
            logger.info(f"Gemini 3 Flash → GF: '{gf}' | Tel: '{tel}'")
        else:
            logger.debug("Gemini 3 Flash: keine Daten gefunden")

        return gf, tel

    except Exception as e:
        logger.warning(f"Gemini-Fehler: {e}")
        return "", ""


# ---------------------------------------------------------------------------
# TELEFON (Regex-Fallback)
# ---------------------------------------------------------------------------

PHONE_PATTERN = re.compile(
    r'(?:'
    r'\+49[\s\.\-\/\(\)]{0,6}'
    r'|0049[\s\.\-\/\(\)]{0,6}'
    r'|\(?0\d{2,5}\)?[\s\.\-\/]{0,5}'
    r')'
    r'\d[\d\s\.\-\/\(\)]{4,20}\d',
    re.ASCII
)

TEL_CONTEXT_POS = re.compile(
    r'(tel\.?|telefon|fon|phone|t\s*:|ruf|call|mobil|handy|mobile|☎|📞)',
    re.IGNORECASE
)

FAX_CONTEXT_NEG = re.compile(
    r'(fax|telefax|f\s*:)',
    re.IGNORECASE
)


def _extract_phone_from_tel_links(soup: BeautifulSoup) -> Optional[str]:
    for tag in soup.find_all("a", href=True):
        href = tag.get("href", "").strip()
        if not href.lower().startswith("tel:"):
            continue

        phone = extract_phone_from_href(href).strip()
        if not phone:
            continue
        if not (phone.startswith("+49") or phone.startswith("0049") or phone.startswith("0")):
            continue

        link_text = tag.get_text().lower()
        parent_text = (tag.parent.get_text().lower() if tag.parent else "")
        if FAX_CONTEXT_NEG.search(link_text + " " + parent_text):
            continue

        if is_valid_phone(phone):
            logger.debug(f"Telefon aus tel:-Link: {phone}")
            return phone

    return None


def _extract_phone_from_text(text: str) -> Optional[str]:
    for match in PHONE_PATTERN.finditer(text):
        start, end = match.start(), match.end()
        ctx_before = text[max(0, start - 80):start]

        if FAX_CONTEXT_NEG.search(ctx_before):
            continue

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


def extract_phone_fallback(soup: BeautifulSoup, plain_text: str) -> str:
    return _extract_phone_from_tel_links(soup) or _extract_phone_from_text(plain_text) or ""


# ---------------------------------------------------------------------------
# GESCHÄFTSFÜHRER (Regex-Fallback)
# ---------------------------------------------------------------------------

GF_KEYWORDS = re.compile(
    r'(Gesch[äa]ftsf[üu]hrer(?:in)?|Vertreten\s+durch|'
    r'Vertretungsberechtigte?r?|Inhaber(?:in)?|'
    r'Gesch[äa]ftsleitung|CEO|Vorstand|Einzelkaufmann)',
    re.IGNORECASE
)

NAME_BLACKLIST = {
    "die", "der", "das", "ein", "eine", "des", "dem", "den", "wir",
    "und", "oder", "für", "mit", "nach", "durch", "von", "zu",
    "bei", "aus", "an", "auf", "in", "im", "ist", "sind",
    "verantwortlich", "inhalte", "redaktionelle", "team", "kontakt",
    "registereintrag", "umsatzsteuer", "identifikationsnummer",
    "impressum", "gesellschaft", "verwaltung", "leitung",
    "geschäftsführung", "presse", "marketing", "vertrieb",
    "technik", "service", "support", "beratung", "planung",
    "haftungsbeschränkt", "handelsregister", "amtsgericht",
    "geschäftsführer", "inhaber", "vorstand", "ansprechpartner",
    "herr", "frau", "beide", "jeweils", "allein", "gemeinsam",
    "tel", "fon", "fax", "mob", "web", "str", "nr", "ust",
    "gmbh", "ag", "kg", "ohg", "gbr", "mbh",
    "managing", "director", "chief", "officer", "executive",
}

ALLOWED_PREFIXES = {"von", "van", "de", "der", "den", "el", "al", "zu"}


def _collect_name_words(text_after_keyword: str) -> List[str]:
    segments = re.split(r'[\n\r\|]', text_after_keyword)
    candidate_text = segments[0][:80] if segments else ""

    words = candidate_text.split()
    collected: List[str] = []

    for word in words:
        clean_raw = word.strip(".,;:()[]")
        if not clean_raw:
            continue

        clean = clean_raw.lower()

        if clean in ALLOWED_PREFIXES:
            collected.append(clean_raw)
            continue

        if clean in NAME_BLACKLIST:
            break

        if not re.match(r'^[A-ZÄÖÜa-zäöüß\-]+$', clean_raw):
            break

        if not clean_raw[0].isupper():
            break

        if len(clean) < 2:
            continue

        collected.append(clean_raw)

    return collected


def extract_gf_fallback(plain_text: str) -> str:
    found: List[str] = []
    lines = plain_text.split('\n')

    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not GF_KEYWORDS.search(line_stripped):
            continue

        kw_match = GF_KEYWORDS.search(line_stripped)
        text_after = line_stripped[kw_match.end():]
        text_after = re.sub(r'^[\s:,]+', '', text_after)

        if not text_after.strip() and i + 1 < len(lines):
            text_after = lines[i + 1].strip()

        if not text_after.strip():
            continue

        name_segments = re.split(r',\s*', text_after)
        for segment in name_segments:
            words = _collect_name_words(segment)
            if len(words) >= 2:
                name = " ".join(words)
                if name not in found:
                    logger.debug(f"GF-Name (Regex): '{name}'")
                    found.append(name)

    return ", ".join(found) if found else ""


# ---------------------------------------------------------------------------
# Öffentliche Hauptfunktion
# ---------------------------------------------------------------------------

def parse_impressum(url: str, page: Page, timeout_ms: int = 10000) -> Tuple[str, str]:
    """
    Lädt Impressum-URL und extrahiert Geschäftsführer + Telefonnummer.

    Strategie:
      1. Gemini 2.0 Flash (präzise KI-Extraktion)
      2. Regex-Fallback falls Gemini nichts findet oder kein API Key

    Returns:
        Tuple (geschaeftsfuehrer: str, telefonnummer: str)
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

    # Primär: Gemini 2.0 Flash
    gf, phone = _extract_with_gemini(plain_text)

    # Fallback: Regex (wenn Gemini nichts liefert)
    if not gf:
        gf = extract_gf_fallback(plain_text)
    if not phone:
        phone = extract_phone_fallback(soup, plain_text)

    return gf, phone
