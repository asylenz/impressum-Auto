"""
Utility-Funktionen
"""

import re
import unicodedata
from typing import Optional, Tuple, Dict
from src.constants import ACTIVE_KEYWORDS

def extract_phone_from_href(href: str) -> str:
    """Extrahiert Telefonnummer aus tel: Link"""
    if href.startswith('tel:'):
        return href.replace('tel:', '').strip()
    return href

def normalize_phone(phone: str) -> str:
    """Normalisiert Telefonnummer"""
    return re.sub(r'[\s\-\(\)\/]', '', phone)

def is_valid_phone(text: str) -> bool:
    """Prüft ob Text wie eine Telefonnummer aussieht"""
    pattern = r'^[\+\(\)\d\s\/-]{5,}$'
    return bool(re.match(pattern, text))

def normalize_string_for_matching(text: str) -> str:
    """
    Normalisiert String für robusten Vergleich:
    - Kleinschreibung
    - Umlaute ersetzen (ä->ae, ö->oe, ü->ue, ß->ss)
    - Akzente entfernen (á->a, é->e, etc.)
    """
    if not text:
        return ""
    
    text = text.lower()
    
    # Manuelle Ersetzung von deutschen Umlauten (Expansion)
    replacements = {
        'ä': 'ae',
        'ö': 'oe',
        'ü': 'ue',
        'ß': 'ss'
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    
    # Unicode-Normalisierung um Akzente zu entfernen (NFD splittet Zeichen + Akzent)
    text = unicodedata.normalize('NFD', text)
    # Entferne alle nicht-ASCII Zeichen (die Akzente)
    text = "".join([c for c in text if not unicodedata.combining(c)])
    
    return text

def categorize_stufe(stufe: str, config_stufen: Dict[str, list]) -> Tuple[bool, str]:
    """
    Kategorisiert eine Stufe in In Scope, Out of Scope oder Unbekannt
    
    Args:
        stufe: Die zu prüfende Stufe
        config_stufen: Dict mit 'in_scope' und 'out_of_scope' Listen
    
    Returns:
        Tuple[is_valid, category]
        - is_valid: True wenn In Scope, False sonst
        - category: "in_scope", "out_of_scope", oder "unknown"
    """
    if not stufe:
        return False, "unknown"
    
    stufe_lower = stufe.lower().strip()
    
    # Listen holen
    in_scope = config_stufen.get('in_scope', [])
    out_of_scope = config_stufen.get('out_of_scope', [])
    
    # Prüfe In Scope (Zielgruppe)
    for valid_stufe in in_scope:
        if valid_stufe.lower().strip() == stufe_lower:
            return True, "in_scope"
    
    # Prüfe Out of Scope (bekannte Stufen, aber nicht Zielgruppe)
    for invalid_stufe in out_of_scope:
        if invalid_stufe.lower().strip() == stufe_lower:
            return False, "out_of_scope"
    
    # Unbekannte Stufe
    return False, "unknown"

def check_active_status(date_text: str) -> bool:
    """Prüft ob Datums-String auf aktive Position hinweist"""
    if not date_text:
        return False
    
    text_lower = date_text.lower()
    
    for keyword in ACTIVE_KEYWORDS:
        if keyword in text_lower:
            return True
    
    # "Seit XXXX" ohne Enddatum auch aktiv
    if 'seit' in text_lower and ' - ' not in text_lower and 'bis' not in text_lower:
        return True
    
    return False

def clean_url(url: str) -> str:
    """Bereinigt URL (entfernt Query-Parameter etc.)"""
    if '?' in url:
        url = url.split('?')[0]
    return url.strip()
