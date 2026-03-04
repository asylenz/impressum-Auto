"""Konfigurationsmanagement — liest config.yaml mit Punkt-Notation-Zugriff"""

import yaml
from pathlib import Path


class Config:
    def __init__(self, config_path: str = "config.yaml"):
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config-Datei nicht gefunden: {config_path}")
        with open(path, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f) or {}

    def get(self, key: str, default=None):
        """Wert per Punkt-Notation abrufen (z.B. 'browser.headless')"""
        keys = key.split(".")
        value = self._data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value if value is not None else default
