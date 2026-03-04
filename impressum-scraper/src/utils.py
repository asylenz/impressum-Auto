"""
Utility-Funktionen — übernommen und bereinigt aus BK-Automatisierung.
Enthält: Telefon-Extraktion, Normalisierung, URL-Bereinigung.
"""

import re
import unicodedata
from urllib.parse import unquote


def extract_phone_from_href(href: str) -> str:
    """Extrahiert Telefonnummer aus tel:-Link"""
    if href.startswith("tel:"):
        return unquote(href.replace("tel:", "").strip())
    return href


def normalize_phone(phone: str) -> str:
    """Normalisiert Telefonnummer — entfernt Leerzeichen, Bindestriche, Klammern, Schrägstriche"""
    return re.sub(r"[\s\-\(\)\/]", "", phone)


def is_valid_phone(text: str) -> bool:
    """Gibt True zurück, wenn text wie eine Telefonnummer aussieht"""
    pattern = r"^[\+\(\)\d\s\/-]{5,}$"
    return bool(re.match(pattern, text.strip()))


def normalize_string_for_matching(text: str) -> str:
    """
    Normalisiert String für robusten Vergleich:
    - Kleinschreibung
    - Umlaute expandieren (ä→ae, ö→oe, ü→ue, ß→ss)
    - Diakritische Zeichen entfernen (é→e, á→a, …)
    """
    if not text:
        return ""
    text = text.lower()
    for char, replacement in {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}.items():
        text = text.replace(char, replacement)
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text


def clean_url(url: str) -> str:
    """Bereinigt URL: entfernt Query-Parameter, Fragment und trailing Slash"""
    if "?" in url:
        url = url.split("?")[0]
    if "#" in url:
        url = url.split("#")[0]
    return url.strip().rstrip("/")
