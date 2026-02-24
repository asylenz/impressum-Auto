"""
Konfigurationsmanagement
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from typing import Any, Dict, List

class Config:
    """Zentrale Konfigurationsklasse"""
    
    def __init__(self, config_path: str = "config.yaml", mode: str = None):
        # .env laden
        load_dotenv()
        
        # YAML-Konfiguration laden
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Konfigurationsdatei nicht gefunden: {config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)
            
        # Modus setzen (Argument gewinnt, sonst Config, sonst 'tecis')
        self.mode = mode or self.get('current_mode', 'tecis')
    
    def get(self, key: str, default: Any = None) -> Any:
        """Wert aus Konfiguration holen (unterstützt verschachtelte Keys mit Punkt-Notation)"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            
            if value is None:
                return default
        
        return value
    
    def get_env(self, key: str, default: str = None) -> str:
        """Umgebungsvariable holen"""
        return os.getenv(key, default)
    
    @property
    def linkedin_email(self) -> str:
        """LinkedIn E-Mail aus Umgebungsvariablen"""
        email = self.get_env('LINKEDIN_EMAIL')
        if not email:
            raise ValueError("LINKEDIN_EMAIL nicht in .env gesetzt")
        return email
    
    @property
    def linkedin_password(self) -> str:
        """LinkedIn Passwort aus Umgebungsvariablen"""
        password = self.get_env('LINKEDIN_PASSWORD')
        if not password:
            raise ValueError("LINKEDIN_PASSWORD nicht in .env gesetzt")
        return password
    
    @property
    def sheet_id(self) -> str:
        """Google Sheet ID aus Umgebungsvariablen"""
        sheet_id = self.get_env('SHEET_ID')
        if not sheet_id:
            raise ValueError("SHEET_ID nicht in .env gesetzt")
        return sheet_id
    
    # --- Company Specific Properties ---
    
    @property
    def company_config(self) -> Dict[str, Any]:
        """Konfiguration für die aktuelle Firma"""
        config = self.get(f'companies.{self.mode}')
        if not config:
            raise ValueError(f"Keine Konfiguration für Firma '{self.mode}' gefunden")
        return config
    
    @property
    def company_name(self) -> str:
        """Name der aktuellen Firma"""
        return self.company_config.get('name', self.mode)
    
    @property
    def company_aliases(self) -> List[str]:
        """
        Gibt eine Liste von Aliasen für die Firma zurück (für Sheet-Filterung).
        Wenn keine definiert sind, wird der Firmenname als Default verwendet.
        """
        aliases = self.company_config.get('sheet_aliases', [])
        if not aliases:
            aliases = [self.company_name]
        return aliases
    
    @property
    def valid_stufen(self) -> Dict[str, list]:
        """
        Gibt Dictionary mit 'in_scope' und 'out_of_scope' Listen zurück.
        Kompatibilität: Wenn nur eine Liste zurückgegeben wurde, ist das jetzt anders.
        """
        return self.company_config.get('stufen', {'in_scope': [], 'out_of_scope': []})
    
    @property
    def company_url_pattern(self) -> str:
        """Regex Pattern für die Firmenseite"""
        return self.company_config.get('url_pattern')

    @property
    def company_selectors(self) -> Dict[str, str]:
        """CSS/XPath Selektoren für die Firmenseite"""
        return self.company_config.get('selectors', {})
        
    @property
    def company_suffixes(self) -> Dict[str, str]:
        """URL Suffixe für Kontakt/Impressum"""
        return self.company_config.get('suffixes', {})
    
    # --- Limits ---
    
    def get_limit(self, platform: str, limit_type: str, default: Any = None) -> Any:
        """Limit für spezifische Plattform holen"""
        # Erst in Umgebungsvariablen schauen
        env_key = f"{platform.upper()}_{limit_type.upper()}"
        env_value = self.get_env(env_key)
        if env_value is not None:
            try:
                return int(env_value) if env_value.isdigit() else env_value
            except:
                pass
        
        # Sonst aus Config
        return self.get(f'limits.{platform}.{limit_type}', default)
