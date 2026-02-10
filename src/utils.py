"""
Utility-Funktionen
"""

import re
from typing import Optional, Tuple
from src.constants import ACTIVE_KEYWORDS, STUFEN_IN_SCOPE, STUFEN_OUT_OF_SCOPE

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

def validate_stufe(stufe: str, valid_stufen: list) -> bool:
    """
    Prüft ob Stufe in Whitelist (case-insensitive)
    DEPRECATED: Verwende stattdessen categorize_stufe()
    """
    if not stufe:
        return False
    
    stufe_lower = stufe.lower().strip()
    
    for valid in valid_stufen:
        if valid.lower().strip() == stufe_lower:
            return True
    
    return False

def categorize_stufe(stufe: str) -> Tuple[bool, str]:
    """
    Kategorisiert eine Stufe in In Scope, Out of Scope oder Unbekannt
    
    Returns:
        Tuple[is_valid, category]
        - is_valid: True wenn In Scope, False sonst
        - category: "in_scope", "out_of_scope", oder "unknown"
    """
    if not stufe:
        return False, "unknown"
    
    stufe_lower = stufe.lower().strip()
    
    # Prüfe In Scope (Zielgruppe)
    for valid_stufe in STUFEN_IN_SCOPE:
        if valid_stufe.lower().strip() == stufe_lower:
            return True, "in_scope"
    
    # Prüfe Out of Scope (bekannte Stufen, aber nicht Zielgruppe)
    for invalid_stufe in STUFEN_OUT_OF_SCOPE:
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
