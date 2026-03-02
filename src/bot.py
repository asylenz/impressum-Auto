"""
Haupt-Bot-Logik: Orchestrierung aller Phasen (Modular)
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
from src.phases import CompanySitePhase, LinkedInPhase, XingPhase, CreditreformPhase, LushaPhase
from src.constants import STATUS_WECHSEL, STATUS_UNGUELTIG, STATUS_UNBEKANNT, TEL_KEINE, TEL_NA, STUFE_NA
from src.utils import categorize_stufe

logger = logging.getLogger(__name__)

class CompanyBot:
    """Haupt-Bot zur Lead-Verarbeitung (Generisch)"""
    
    def __init__(self, config: Config):
        self.config = config
        self.rate_limiter = RateLimiter(config)
        self.linkedin_auth = LinkedInAuth(config)
        self.company_name = config.company_name
        
        # Phasen initialisieren
        self.company_site_phase = CompanySitePhase(config, self.rate_limiter)
        self.linkedin_phase = LinkedInPhase(config, self.rate_limiter)
        self.xing_phase = XingPhase(config, self.rate_limiter)
        self.creditreform_phase = CreditreformPhase(config, self.rate_limiter)
        self.lusha_phase = LushaPhase(config, self.rate_limiter)
        
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
        logger.info(f"=== Starte Verarbeitung ({self.config.mode}): {lead.full_name} ===")
        
        result = LeadResult(lead=lead)
        flags = ProcessingFlags()
        
        try:
            # 1. Link-Discovery
            logger.info("--- Link-Discovery ---")
            link_discovery = LinkDiscovery(self.config, self.rate_limiter)
            urls = link_discovery.discover_urls(lead)
            
            result.target_url_company = urls['company']
            result.target_url_linkedin = urls['linkedin']
            result.target_url_xing = urls['xing']
            result.target_url_creditreform = urls['creditreform']
            
            # Browser starten für Phasen
            with self:
                # 2. Phase 1: Company Site
                stufe, telefonnummern = self._phase1_company_site(result, flags)
                
                if stufe:
                    self._set_stufe_if_better(result, stufe, prio=1, source="Firmenseite")
                if telefonnummern:
                    result.telefonnummer = telefonnummern[0] if len(telefonnummern) > 0 else ""
                    result.zweite_telefonnummer = telefonnummern[1] if len(telefonnummern) > 1 else ""
                    result.tel_quelle = "Firmenseite"
                
                # 3. Phase 2: LinkedIn (falls nötig)
                if not flags.telefonnummer_gefunden or not flags.stufe_gefunden:
                    stufe_entry_li, stufe_headline_li, tel_li, ist_aktiv = self._phase2_linkedin(result, flags)
                    
                    # Entry (Prio 2) hat Vorrang vor Headline (Prio 3)
                    if stufe_entry_li:
                        self._set_stufe_if_better(result, stufe_entry_li, prio=2, source="LinkedIn Entry")
                    elif stufe_headline_li:
                        self._set_stufe_if_better(result, stufe_headline_li, prio=3, source="LinkedIn Header")
                    
                    if tel_li and not result.telefonnummer:
                        result.telefonnummer = tel_li[0] if len(tel_li) > 0 else ""
                        result.zweite_telefonnummer = tel_li[1] if len(tel_li) > 1 else ""
                        result.tel_quelle = "LinkedIn"
                
                # 4. Phase 3: Xing (falls nötig)
                if not flags.stufe_gefunden or (flags.status_check_weiter_creditreform or flags.stufe_suchen_weiter_creditreform):
                    stufe_entry_xing, stufe_header_xing, ist_aktiv_xing = self._phase3_xing(result, flags)

                    # Entry (Prio 2) hat Vorrang vor Header (Prio 3)
                    if stufe_entry_xing:
                        self._set_stufe_if_better(result, stufe_entry_xing, prio=2, source="Xing Entry")
                    elif stufe_header_xing:
                        self._set_stufe_if_better(result, stufe_header_xing, prio=3, source="Xing Header")
                
                # 5. Phase 4: Creditreform (falls Telefon fehlt aber Stufe vorhanden)
                if not flags.telefonnummer_gefunden and (flags.stufe_gefunden or result.stufe):
                    tel_cr = self._phase4_creditreform(result, flags)
                    
                    if tel_cr and not result.telefonnummer:
                        result.telefonnummer = tel_cr[0] if len(tel_cr) > 0 else ""
                        result.zweite_telefonnummer = tel_cr[1] if len(tel_cr) > 1 else ""
                        result.tel_quelle = "Creditreform"
            
            # 6. Phase 5: Lusha (Fallback – außerhalb des Browser-Kontexts, da reine API)
            need_phone = not result.telefonnummer
            need_stufe = not result.stufe
            # Guard 1: Nur aufrufen wenn Person als aktiv bestätigt ist
            person_confirmed_active = (
                flags.status_active_confirmed or bool(result.target_url_company)
            ) and result.status != STATUS_WECHSEL
            
            if person_confirmed_active and (need_phone or need_stufe):
                if need_stufe:
                    # Schritt 1: erst Stufe suchen – kein Telefon-Lookup ohne validierte Stufe
                    _, stufe_lusha = self._phase5_lusha(
                        result, flags,
                        linkedin_url=result.target_url_linkedin,
                        need_phone=False,
                        need_stufe=True,
                    )
                    if stufe_lusha:
                        self._set_stufe_if_better(result, stufe_lusha, prio=4, source="Lusha")
                        flags.stufe_gefunden = True
                        # Schritt 2: Telefon suchen wenn Stufe ausreichend validiert ist
                        if need_phone and self._stufe_allows_phone(stufe_lusha):
                            tel_lusha, _ = self._phase5_lusha(
                                result, flags,
                                linkedin_url=result.target_url_linkedin,
                                need_phone=True,
                                need_stufe=False,
                            )
                            if tel_lusha:
                                result.telefonnummer = tel_lusha[0]
                                result.zweite_telefonnummer = tel_lusha[1] if len(tel_lusha) > 1 else ""
                                result.tel_quelle = "Lusha"
                    # Kein else: kein Telefon-Lookup wenn Lusha keine Stufe gefunden hat
                else:
                    # Stufe aus Phasen 1–4 vorhanden → Telefon suchen wenn Stufe ausreichend validiert ist
                    if need_phone and self._stufe_allows_phone(result.stufe):
                        tel_lusha, _ = self._phase5_lusha(
                            result, flags,
                            linkedin_url=result.target_url_linkedin,
                            need_phone=True,
                            need_stufe=False,
                        )
                        if tel_lusha:
                            result.telefonnummer = tel_lusha[0]
                            result.zweite_telefonnummer = tel_lusha[1] if len(tel_lusha) > 1 else ""
                            result.tel_quelle = "Lusha"
            
            # 7. Letzter Fallback: Modus-spezifischer Default-Stufe (z.B. DVAG: "Vermögensberater")
            # Wird nur angewendet wenn alle Phasen (LinkedIn, Xing, Lusha) keine Stufe gefunden haben
            if not result.stufe:
                default_stufe = self.config.company_config.get('default_stufe')
                if default_stufe:
                    result.stufe = default_stufe
                    result.stufe_quelle = "Modus-Default"
                    result.stufe_prio = 99
                    flags.stufe_gefunden = True
                    logger.info(f"Keine Stufe in allen Phasen gefunden – verwende Modus-Default: '{default_stufe}'")

            # 8. Output-Mapping (Appendix A)
            self._apply_output_logic(result)
            
            logger.info(f"=== Verarbeitung abgeschlossen: {lead.full_name} ===")
            logger.info(f"Ergebnis: Tel={result.telefonnummer}, Stufe={result.stufe}, Zielgruppe={result.zielgruppe}, Quelle={result.tel_quelle}")
            
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
    
    def _stufe_allows_phone(self, stufe_text: str) -> bool:
        """
        Gibt True zurück wenn eine Stufe gut genug ist, um einen Lusha-Telefon-Lookup zu rechtfertigen.
        Normal: nur in_scope / out_of_scope.
        treat_unknown_as_validated-Modus: auch unknown Stufen erlaubt.
        """
        _, cat = categorize_stufe(stufe_text, self.config.valid_stufen)
        if cat in ("in_scope", "out_of_scope"):
            return True
        return cat == "unknown" and self.config.treat_unknown_as_validated

    def _set_stufe_if_better(self, result: LeadResult, candidate: str, prio: int, source: str = "") -> bool:
        """
        Setzt Stufe nur wenn candidate eine höhere Priorität hat als die aktuelle Stufe.
        Prio: 1=Firmenseite, 2=Entry (LinkedIn/Xing), 3=Headline (LinkedIn), 4=Lusha.
        Validierte Stufen (in_scope/out_of_scope) werden nie durch unvalidierte überschrieben.
        """
        if not candidate:
            return False
        if result.stufe:
            _, current_cat = categorize_stufe(result.stufe, self.config.valid_stufen)
            _, cand_cat = categorize_stufe(candidate, self.config.valid_stufen)
            # Validierte durch unvalidierte nie überschreiben
            if current_cat in ("in_scope", "out_of_scope") and cand_cat == "unknown":
                logger.debug(f"Stufe-Kandidat '{candidate}' (Prio {prio}) verworfen – aktuelle Stufe '{result.stufe}' ist validiert")
                return False
        # Nur setzen wenn noch keine Stufe vorhanden oder neue Prio besser ist
        if not result.stufe or prio < result.stufe_prio:
            logger.debug(f"Stufe gesetzt: '{candidate}' (Prio {prio}, Quelle: {source}, vorher: '{result.stufe}' Prio {result.stufe_prio})")
            result.stufe = candidate
            result.stufe_prio = prio
            result.stufe_quelle = source
            return True
        return False
    
    def _phase1_company_site(self, result: LeadResult, flags: ProcessingFlags) -> Tuple[Optional[str], List[str]]:
        """Phase 1: Firmenseite"""
        if not result.target_url_company:
            logger.info(f"Phase 1: Keine {self.company_name}-URL -> Überspringe")
            return None, []
        
        logger.info(f"--- Phase 1: {self.company_name} ---")
        stufe, telefonnummern = self.company_site_phase.process(
            self.page, result.target_url_company, result.lead, flags
        )
        
        # Flags für nächste Phase setzen
        if telefonnummern and stufe:
            flags.nur_status_check = True
        elif telefonnummern and not stufe:
            flags.nur_stufe_suchen = True
        
        return stufe, telefonnummern
    
    def _phase2_linkedin(self, result: LeadResult, flags: ProcessingFlags):
        """Phase 2: LinkedIn – gibt (stufe_entry, stufe_headline, telefonnummern, ist_aktiv) zurück"""
        if not result.target_url_linkedin:
            logger.info("Phase 2: Keine LinkedIn-URL -> Überspringe")
            return None, None, [], True
        
        logger.info("--- Phase 2: LinkedIn ---")
        
        # Zuerst Profil-URL prüfen (persistente Session nutzen); nur bei Bedarf Login
        if not self.linkedin_logged_in:
            if not self.linkedin_auth.is_logged_in(self.page, result.target_url_linkedin):
                if not self.linkedin_auth.login(self.context, self.page):
                    logger.error("LinkedIn-Login fehlgeschlagen (2FA/Captcha im Headless oft nicht möglich)")
                    return None, None, [], True
            self.linkedin_logged_in = True
        
        stufe_entry, stufe_headline, telefonnummern, ist_aktiv = self.linkedin_phase.process(
            self.page, result.target_url_linkedin, result.lead, flags
        )
        
        # Status für ehemalige Mitarbeiter setzen – nur wenn KEINE Company-Seite existiert.
        # Existiert eine Company-Seite, ist die Person dort gelistet = aktiv (Company ist maßgeblich).
        if not ist_aktiv and not result.target_url_company:
            self._set_inactive_status(result)
            return None, None, [], False
        if not ist_aktiv and result.target_url_company:
            logger.info(f"LinkedIn: Eintrag ohne 'Heute', aber {self.company_name}-Seite vorhanden → behandle als aktiv, behalte Daten")
        
        # Status-Flag setzen (nur wenn aktiv oder Company-Seite vorhanden)
        flags.status_active_confirmed = True
        
        return stufe_entry, stufe_headline, telefonnummern, ist_aktiv
    
    def _phase3_xing(self, result: LeadResult, flags: ProcessingFlags):
        """Phase 3: Xing – gibt (stufe_entry, stufe_header, ist_aktiv) zurück"""
        if not result.target_url_xing:
            logger.info("Phase 3: Keine Xing-URL -> Überspringe")
            return None, None, True

        logger.info("--- Phase 3: Xing ---")

        stufe_entry, stufe_header, ist_aktiv = self.xing_phase.process(
            self.page, result.target_url_xing, result.lead, flags
        )

        # Status für ehemalige Mitarbeiter setzen nur wenn weder LinkedIn aktiv bestätigt noch Company-Seite existiert
        if not ist_aktiv and not flags.status_active_confirmed and not result.target_url_company:
            self._set_inactive_status(result)
            return None, None, False
        if not ist_aktiv and result.target_url_company:
            logger.info(f"Xing: Kein aktiver Eintrag, aber {self.company_name}-Seite vorhanden → behandle als aktiv, behalte Daten")

        return stufe_entry, stufe_header, ist_aktiv
    
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
    
    def _phase5_lusha(
        self,
        result: LeadResult,
        flags: ProcessingFlags,
        linkedin_url: Optional[str] = None,
        need_phone: bool = True,
        need_stufe: bool = True,
    ) -> Tuple[List[str], Optional[str]]:
        """Phase 5: Lusha API – Fallback für Telefon und Stufe"""
        logger.info("--- Phase 5: Lusha ---")
        return self.lusha_phase.process(
            result.lead,
            flags,
            linkedin_url=linkedin_url,
            need_phone=need_phone,
            need_stufe=need_stufe,
        )
    
    def _apply_output_logic(self, result: LeadResult) -> None:
        """
        Wendet Appendix A Output-Logik an
        """
        has_telefon = bool(result.telefonnummer and result.telefonnummer not in ["", TEL_KEINE, TEL_NA])
        has_stufe = bool(result.stufe and result.stufe not in ["", STUFE_NA])

        # Prüfe ob Stufe bekannt ist (In Scope, Out of Scope oder unknown)
        if has_stufe:
            is_valid, category = categorize_stufe(result.stufe, self.config.valid_stufen)
            
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
            elif category == "unknown":
                if self.config.treat_unknown_as_validated:
                    # Modus: unbekannte Stufe als validiert behandeln
                    result.stufe = result.stufe + " (nicht validiert)"
                    result.zielgruppe = "In Scope"
                    logger.info(f"Stufe (nicht validiert) als In Scope behandelt: '{result.stufe}'")
                    # Kein return – fällt durch zu den Szenarien unten (Telefon ggf. TEL_KEINE setzen)
                    has_stufe = True
                else:
                    # Stufe-Text bleibt erhalten (wird ins Sheet geschrieben), Zielgruppe = Unbekannt
                    result.zielgruppe = STATUS_UNBEKANNT
                    logger.info(f"Stufe '{result.stufe}' ist unbekannt → Zielgruppe=Unbekannt, Stufe-Text bleibt erhalten")
                    if result.status != STATUS_WECHSEL:
                        result.status = STATUS_UNBEKANNT
                    if not has_telefon:
                        result.telefonnummer = TEL_KEINE
                        result.zweite_telefonnummer = ""
                    return  # Fertig

        # Szenario 2: Telefon vorhanden, aber keine gültige Stufe (Spec: Status "Unbekannt")
        if has_telefon and not has_stufe:
            result.stufe = STUFE_NA
            if result.status != STATUS_WECHSEL:
                result.status = STATUS_UNBEKANNT
        
        # Szenario 3: Stufe vorhanden (und In Scope), aber kein Telefon (Spec: Status leer)
        elif not has_telefon and has_stufe:
            result.telefonnummer = TEL_KEINE
            result.zweite_telefonnummer = ""
        
        # Szenario 4 & 5: Weder Telefon noch Stufe
        elif not has_telefon and not has_stufe:
            if result.status != STATUS_WECHSEL:
                result.status = STATUS_UNBEKANNT
            # Szenario 5: Kein Company-Eintrag auf allen Plattformen
            if not result.target_url_company and not result.target_url_linkedin and not result.target_url_xing:
                result.telefonnummer = TEL_NA
                result.stufe = STUFE_NA
            # Szenario 4: URLs vorhanden, aber keine Daten gefunden
            else:
                result.telefonnummer = TEL_KEINE
                result.stufe = STUFE_NA
