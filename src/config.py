"""
Konfigurationsmanagement
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from typing import Any, Dict

class Config:
    """Zentrale Konfigurationsklasse"""
    
    def __init__(self, config_path: str = "config.yaml"):
        # .env laden
        load_dotenv()
        
        # YAML-Konfiguration laden
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Konfigurationsdatei nicht gefunden: {config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)
    
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
    
    @property
    def valid_stufen(self) -> list:
        """Liste gültiger Stufen"""
        return self.get('valid_stufen', [])
    
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
