"""
Phase 5: Lusha API – Fallback für Telefonnummern und Stufen
"""

import logging
import os
import time
from typing import List, Optional, Tuple
import json

import requests

from src.models import Lead, ProcessingFlags
from src.utils import categorize_stufe

logger = logging.getLogger(__name__)

LUSHA_API_URL = "https://api.lusha.com/v2/person"


class LushaPhase:
    """Phase 5: Lusha API – Fallback wenn Phasen 1-4 nichts gefunden haben"""

    def __init__(self, config, rate_limiter):
        self.config = config
        self.rate_limiter = rate_limiter
        self.valid_stufen = config.valid_stufen
        self.api_key = os.getenv("LUSHA_API_KEY")
        if not self.api_key:
            logger.warning("LUSHA_API_KEY nicht in .env gesetzt – Phase 5 wird übersprungen")

    def process(
        self,
        lead: Lead,
        flags: ProcessingFlags,
        linkedin_url: Optional[str] = None,
        need_phone: bool = True,
        need_stufe: bool = True,
    ) -> Tuple[List[str], Optional[str]]:
        """
        Sucht Telefonnummern und/oder Stufe über die Lusha API.

        Returns:
            (telefonnummern, stufe) – leere Liste / None wenn nichts gefunden
        """
        if not self.api_key:
            return [], None

        if not need_phone and not need_stufe:
            return [], None

        self.rate_limiter.wait_if_needed("lusha")

        try:
            params = {
                "firstName": lead.vorname.split()[0] if lead.vorname.split() else lead.vorname,
                "lastName": lead.nachname.split()[-1] if lead.nachname.split() else lead.nachname,
                "companyName": self.config.lusha_company_name,
                "revealPhones": "true",
                "revealEmails": "false",
            }

            if linkedin_url:
                params["linkedinUrl"] = linkedin_url

            if need_phone:
                params["filterBy"] = "phoneNumbers"

            headers = {
                "api_key": self.api_key,
                "Content-Type": "application/json",
            }

            logger.info(f"Lusha API Request Payload: URL={LUSHA_API_URL}, PARAMS={params}")
            logger.info(f"Lusha API Anfrage für: {lead.full_name}")
            
            response = requests.get(
                LUSHA_API_URL,
                params=params,
                headers=headers,
                timeout=15,
            )

            self.rate_limiter.record_request("lusha")
            
            logger.info(f"Lusha API Response: STATUS={response.status_code}, TEXT={response.text[:1000]}")

            if response.status_code == 404:
                logger.info(f"Lusha: Kein Eintrag gefunden für {lead.full_name}")
                return [], None

            if response.status_code == 451:
                logger.info(f"Lusha: DSGVO-Sperre für {lead.full_name} (451)")
                return [], None

            if response.status_code == 429:
                logger.warning("Lusha: Rate-Limit erreicht (429)")
                return [], None

            if response.status_code == 412:
                logger.warning(f"Lusha: Ungültiger Name für {lead.full_name} (412)")
                return [], None

            if response.status_code != 200:
                logger.error(f"Lusha API Fehler {response.status_code}: {response.text[:200]}")
                return [], None

            data = response.json()
            contact = data.get("contact", {})

            # Fehler im Kontakt-Objekt prüfen
            if contact.get("error"):
                err = contact["error"]
                logger.info(f"Lusha: Kein Ergebnis für {lead.full_name} – {err.get('name', '')} ({err.get('message', '')})")
                return [], None

            contact_data = contact.get("data", {})
            if not contact_data:
                logger.info(f"Lusha: Leeres data-Objekt für {lead.full_name}")
                return [], None

            # Telefonnummern extrahieren
            telefonnummern = []
            if need_phone:
                for phone_obj in contact_data.get("phoneNumbers", []):
                    if phone_obj.get("doNotCall"):
                        continue
                    number = (
                        phone_obj.get("localNumber")
                        or phone_obj.get("internationalNumber")
                        or phone_obj.get("number")
                        or phone_obj.get("rawNumber")
                    )
                    if number and number not in telefonnummern:
                        telefonnummern.append(str(number))

            if telefonnummern:
                logger.info(f"Lusha: {len(telefonnummern)} Telefonnummer(n) gefunden für {lead.full_name}")

            # Stufe (jobTitle) extrahieren und validieren
            stufe = None
            if need_stufe:
                job_title_obj = contact_data.get("jobTitle", {})
                raw_title = job_title_obj.get("title", "") if isinstance(job_title_obj, dict) else ""

                if raw_title:
                    _, category = categorize_stufe(raw_title, self.valid_stufen)
                    stufe = raw_title
                    logger.info(f"Lusha: Jobtitel '{raw_title}' gefunden (Kategorie: {category})")

            return telefonnummern, stufe

        except requests.Timeout:
            logger.error(f"Lusha API Timeout für {lead.full_name}")
            return [], None
        except Exception as e:
            logger.error(f"Lusha API unerwarteter Fehler für {lead.full_name}: {e}")
            return [], None
