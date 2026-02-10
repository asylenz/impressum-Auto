"""
Haupt-Bot-Logik: Orchestrierung aller Phasen
"""

import logging
from pathlib import Path
from playwright.sync_api import sync_playwright
from typing import Optional, Tuple, List

from src.config import Config
from src.models import Lead, LeadResult, ProcessingFlags
from src.rate_limiter import RateLimiter, RateLimitExceeded
from src.linkedin_auth import LinkedInAuth
from src.discovery import LinkDiscovery
from src.phases import TecisPhase, LinkedInPhase, XingPhase, CreditreformPhase
from src.constants import STATUS_WECHSEL, STATUS_UNGUELTIG, STATUS_UNBEKANNT, TEL_KEINE, TEL_NA, STUFE_NA
from src.utils import categorize_stufe

logger = logging.getLogger(__name__)

class TecisBot:
    """Haupt-Bot zur Lead-Verarbeitung"""
    
    def __init__(self, config: Config):
        self.config = config
        self.rate_limiter = RateLimiter(config)
        self.linkedin_auth = LinkedInAuth(config)
        
        # Phasen initialisieren
        self.tecis_phase = TecisPhase(config, self.rate_limiter)
        self.linkedin_phase = LinkedInPhase(config, self.rate_limiter)
        self.xing_phase = XingPhase(config, self.rate_limiter)
        self.creditreform_phase = CreditreformPhase(config, self.rate_limiter)
        
        # Browser-Context (wird pro Batch wiederverwendet)
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.linkedin_logged_in = False
    
    def __enter__(self):
        """Context Manager: Browser starten"""
        headless = self.config.get('browser.headless', True)
        user_agent = self.config.get('browser.user_agent')
        
        # Persistent Context für dauerhafte Session (inkl. Cookies, LocalStorage)
        user_data_dir = Path('browser_data/linkedin')
        user_data_dir.mkdir(parents=True, exist_ok=True)
        
        self.playwright = sync_playwright().start()
        self.context = self.playwright.chromium.launch_persistent_context(
            str(user_data_dir),
            headless=headless,
            user_agent=user_agent,
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self.page.set_default_timeout(self.config.get('browser.timeout', 30000))
        
        # LinkedIn-Session laden (falls vorhanden)
        self.linkedin_auth.load_session(self.context)
        
        # Browser-Referenz für Kompatibilität (wird nicht verwendet)
        self.browser = None
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager: Browser schließen"""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.playwright:
            self.playwright.stop()
    
    def process_lead(self, lead: Lead) -> LeadResult:
        """
        Verarbeitet einen Lead durch alle Phasen
        Gibt LeadResult zurück
        """
        logger.info(f"=== Starte Verarbeitung: {lead.full_name} ===")
        
        result = LeadResult(lead=lead)
        flags = ProcessingFlags()
        
        try:
            # 1. Link-Discovery
            logger.info("--- Link-Discovery ---")
            link_discovery = LinkDiscovery(self.config, self.rate_limiter)
            urls = link_discovery.discover_urls(lead)
            
            result.target_url_tecis = urls['tecis']
            result.target_url_linkedin = urls['linkedin']
            result.target_url_xing = urls['xing']
            result.target_url_creditreform = urls['creditreform']
            
            # Browser starten für Phasen
            with self:
                # 2. Phase 1: Tecis
                stufe, telefonnummern = self._phase1_tecis(result, flags)
                
                if stufe:
                    result.stufe = stufe
                if telefonnummern:
                    result.telefonnummer = telefonnummern[0] if len(telefonnummern) > 0 else ""
                    result.zweite_telefonnummer = telefonnummern[1] if len(telefonnummern) > 1 else ""
                
                # 3. Phase 2: LinkedIn (falls nötig)
                if not flags.telefonnummer_gefunden or not flags.stufe_gefunden:
                    stufe_li, tel_li, ist_aktiv = self._phase2_linkedin(result, flags)
                    
                    # Status wird nicht gesetzt (nur Stufe/Telefon)
                    if stufe_li and not result.stufe:
                        result.stufe = stufe_li
                    
                    if tel_li and not result.telefonnummer:
                        result.telefonnummer = tel_li[0] if len(tel_li) > 0 else ""
                        result.zweite_telefonnummer = tel_li[1] if len(tel_li) > 1 else ""
                
                # 4. Phase 3: Xing (falls nötig)
                if not flags.stufe_gefunden or (flags.status_check_weiter_creditreform or flags.stufe_suchen_weiter_creditreform):
                    stufe_xing, ist_aktiv_xing = self._phase3_xing(result, flags)
                    
                    # Status wird nicht gesetzt (nur Stufe/Telefon)
                    if stufe_xing and not result.stufe:
                        result.stufe = stufe_xing
                
                # 5. Phase 4: Creditreform (falls Telefon fehlt aber Stufe vorhanden)
                if not flags.telefonnummer_gefunden and (flags.stufe_gefunden or result.stufe):
                    tel_cr = self._phase4_creditreform(result, flags)
                    
                    if tel_cr and not result.telefonnummer:
                        result.telefonnummer = tel_cr[0] if len(tel_cr) > 0 else ""
                        result.zweite_telefonnummer = tel_cr[1] if len(tel_cr) > 1 else ""
            
            # 6. Output-Mapping (Appendix A)
            self._apply_output_logic(result)
            
            logger.info(f"=== Verarbeitung abgeschlossen: {lead.full_name} ===")
            logger.info(f"Ergebnis: Tel={result.telefonnummer}, Stufe={result.stufe}, Zielgruppe={result.zielgruppe}")
            
            return result
            
        except RateLimitExceeded as e:
            logger.error(f"Rate-Limit erreicht: {e}")
            return result
        except Exception as e:
            logger.error(f"Fehler bei Lead-Verarbeitung: {e}", exc_info=True)
            return result
    
    def _set_inactive_status(self, result: LeadResult) -> None:
        """Setzt Status für ehemalige Mitarbeiter (Appendix A, Szenario 6): Tel=n/a, Stufe=n/a, Status=Wechsel"""
        result.status = STATUS_WECHSEL
        result.telefonnummer = TEL_NA
        result.zweite_telefonnummer = ""
        result.stufe = STUFE_NA
    
    def _phase1_tecis(self, result: LeadResult, flags: ProcessingFlags) -> Tuple[Optional[str], List[str]]:
        """Phase 1: Tecis"""
        if not result.target_url_tecis:
            logger.info("Phase 1: Keine Tecis-URL -> Überspringe")
            return None, []
        
        logger.info("--- Phase 1: Tecis ---")
        stufe, telefonnummern = self.tecis_phase.process(
            self.page, result.target_url_tecis, result.lead, flags
        )
        
        # Flags für nächste Phase setzen
        if telefonnummern and stufe:
            flags.nur_status_check = True
        elif telefonnummern and not stufe:
            flags.nur_stufe_suchen = True
        
        return stufe, telefonnummern
    
    def _phase2_linkedin(self, result: LeadResult, flags: ProcessingFlags):
        """Phase 2: LinkedIn"""
        if not result.target_url_linkedin:
            logger.info("Phase 2: Keine LinkedIn-URL -> Überspringe")
            return None, [], True
        
        logger.info("--- Phase 2: LinkedIn ---")
        
        # Zuerst Profil-URL prüfen (persistente Session nutzen); nur bei Bedarf Login
        if not self.linkedin_logged_in:
            if not self.linkedin_auth.is_logged_in(self.page, result.target_url_linkedin):
                if not self.linkedin_auth.login(self.context, self.page):
                    logger.error("LinkedIn-Login fehlgeschlagen (2FA/Captcha im Headless oft nicht möglich)")
                    return None, [], True
            self.linkedin_logged_in = True
        
        stufe, telefonnummern, ist_aktiv = self.linkedin_phase.process(
            self.page, result.target_url_linkedin, result.lead, flags
        )
        
        # Status für ehemalige Mitarbeiter setzen – nur wenn KEINE Tecis-Seite existiert.
        # Existiert eine Tecis-Seite, ist die Person dort gelistet = aktiv (Tecis ist maßgeblich).
        if not ist_aktiv and not result.target_url_tecis:
            self._set_inactive_status(result)
            return None, [], False
        if not ist_aktiv and result.target_url_tecis:
            logger.info("LinkedIn: Eintrag ohne 'Heute', aber Tecis-Seite vorhanden → behandle als aktiv, behalte Tecis-Daten")
        
        # Status-Flag setzen (nur wenn aktiv oder Tecis-Seite vorhanden)
        flags.status_active_confirmed = True
        
        return stufe, telefonnummern, ist_aktiv
    
    def _phase3_xing(self, result: LeadResult, flags: ProcessingFlags):
        """Phase 3: Xing"""
        if not result.target_url_xing:
            logger.info("Phase 3: Keine Xing-URL -> Überspringe")
            return None, True
        
        logger.info("--- Phase 3: Xing ---")
        
        stufe, ist_aktiv = self.xing_phase.process(
            self.page, result.target_url_xing, result.lead, flags
        )
        
        # Status für ehemalige Mitarbeiter setzen nur wenn weder LinkedIn aktiv bestätigt noch Tecis-Seite existiert
        if not ist_aktiv and not flags.status_active_confirmed and not result.target_url_tecis:
            self._set_inactive_status(result)
            return None, False
        if not ist_aktiv and result.target_url_tecis:
            logger.info("Xing: Kein aktiver Eintrag, aber Tecis-Seite vorhanden → behandle als aktiv, behalte Tecis-Daten")
        
        return stufe, ist_aktiv
    
    def _phase4_creditreform(self, result: LeadResult, flags: ProcessingFlags):
        """Phase 4: Creditreform"""
        if not result.target_url_creditreform:
            logger.info("Phase 4: Keine Creditreform-URL -> Überspringe")
            return []
        
        logger.info("--- Phase 4: Creditreform ---")
        
        telefonnummern = self.creditreform_phase.process(
            self.page, result.target_url_creditreform, result.lead, flags
        )
        
        return telefonnummern
    
    def _apply_output_logic(self, result: LeadResult) -> None:
        """
        Wendet Appendix A Output-Logik an
        
        Szenario 1: Telefonnummer(n) und Stufe gefunden → (Status bleibt leer, außer Out of Scope)
        Szenario 2: Telefonnummer(n) aber KEINE Stufe → Status "ungültig"
        Szenario 3: Stufe aber KEINE Telefonnummer → "garkeine"
        Szenario 4: KEINE Telefonnummer und KEINE Stufe → "garkeine" oder "n/a"
        Szenario 5: KEIN Tecis Eintrag → "n/a"
        Szenario 6: NICHT mehr bei Tecis → "Wechsel..." (bereits gesetzt)
        """
        has_telefon = bool(result.telefonnummer and result.telefonnummer not in ["", TEL_KEINE, TEL_NA])
        has_stufe = bool(result.stufe and result.stufe not in ["", STUFE_NA])

        # Prüfe ob Stufe Out of Scope ist (bekannt aber nicht Zielgruppe)
        if has_stufe:
            is_valid, category = categorize_stufe(result.stufe)
            
            # Zielgruppe setzen basierend auf Kategorie
            if category == "in_scope":
                result.zielgruppe = "In Scope"
                logger.debug(f"Stufe '{result.stufe}' ist In Scope (Zielgruppe)")
            elif category == "out_of_scope":
                result.zielgruppe = "Out of Scope"
                logger.info(f"Stufe '{result.stufe}' ist Out of Scope → Status ungültig")
                result.status = STATUS_UNGUELTIG
                # Telefonnummer bleibt erhalten wenn vorhanden
                if not has_telefon:
                    result.telefonnummer = TEL_KEINE
                    result.zweite_telefonnummer = ""
                return  # Fertig, Status ist gesetzt

        # Szenario 2: Telefon vorhanden, aber keine gültige Stufe (Spec: Status "Unbekannt")
        # Wechsel-Status (Szenario 6) nicht überschreiben, wenn z.B. Tecis Tel hatte, LinkedIn aber "ehemalig"
        if has_telefon and not has_stufe:
            result.stufe = STUFE_NA
            if result.status != STATUS_WECHSEL:
                result.status = STATUS_UNBEKANNT
        
        # Szenario 3: Stufe vorhanden (und In Scope), aber kein Telefon (Spec: Status leer)
        elif not has_telefon and has_stufe:
            result.telefonnummer = TEL_KEINE
            result.zweite_telefonnummer = ""
        
        # Szenario 4 & 5: Weder Telefon noch Stufe (Status nur setzen wenn nicht schon Szenario 6)
        elif not has_telefon and not has_stufe:
            if result.status != STATUS_WECHSEL:
                result.status = STATUS_UNBEKANNT
            # Szenario 5: Kein Tecis-Eintrag auf allen Plattformen
            if not result.target_url_tecis and not result.target_url_linkedin and not result.target_url_xing:
                result.telefonnummer = TEL_NA
                result.stufe = STUFE_NA
            # Szenario 4: URLs vorhanden, aber keine Daten gefunden
            else:
                result.telefonnummer = TEL_KEINE
                result.stufe = STUFE_NA
