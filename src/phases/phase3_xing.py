"""
Phase 3: Xing Profil-Scraping
"""

import logging
from typing import Optional, List, Tuple
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from src.models import Lead, ProcessingFlags
from src.utils import categorize_stufe, check_active_status
from src.constants import XING_HEADLINE_ATTR, XING_HEADLINE_VALUE

logger = logging.getLogger(__name__)

class XingPhase:
    """Phase 3: Xing Profil-Scraping"""
    
    def __init__(self, config, rate_limiter):
        self.config = config
        self.rate_limiter = rate_limiter
        self.valid_stufen = config.valid_stufen
        self.company_name = config.company_name
        self.match_name = config.linkedin_match_name
    
    def process(self, page: Page, url: str, lead: Lead, flags: ProcessingFlags) -> Tuple[Optional[str], Optional[str], bool]:
        """
        Verarbeitet Xing-URL
        Gibt (stufe_entry, stufe_header, ist_aktiv) zurück.
        stufe_entry  = Stufe aus Berufserfahrungs-Eintrag (Prio 2), None wenn nicht gefunden
        stufe_header = Stufe aus Profilkopf (Prio 3), None wenn nicht gefunden
        """
        if not url:
            return None, None, True  # Default: aktiv

        try:
            logger.info(f"Öffne Xing-Profil: {url}")

            # Rate-Limiting
            self.rate_limiter.acquire('xing')

            # Profil öffnen
            page.goto(url, wait_until='domcontentloaded')
            page.wait_for_timeout(2000)

            # Header-Stufe merken (Prio 3 – Fallback wenn kein Entry gefunden)
            stufe_header = self._extract_stufe_from_header(page)

            # Firmen-Eintrag in Berufserfahrung suchen
            company_entry = self._find_company_entry(page)

            if not company_entry:
                logger.info(f"Kein {self.company_name}-Eintrag in Xing Berufserfahrung gefunden")
                if stufe_header:
                    logger.info(f"Stufe aus Header: {stufe_header} (Berufserfahrungs-Sektion nicht gefunden)")
                    flags.stufe_gefunden = True
                return None, stufe_header, True

            # Status prüfen ("bis heute")
            ist_aktiv = self._check_active_status(company_entry)

            if not ist_aktiv:
                # Bei LinkedIn=Active confirmed widerspricht Xing
                if flags.status_active_confirmed:
                    logger.info("Xing zeigt 'ehemalig', aber LinkedIn zeigte 'aktiv' - ignoriere Xing-Status")
                    ist_aktiv = True
                else:
                    logger.info(f"Person ist nicht mehr bei {self.company_name} (ehemaliger Eintrag)")
                    return None, None, False

            logger.info(f"Person ist aktiv bei {self.company_name}")

            # Stufe aus Experience-Eintrag (Prio 2)
            stufe_entry = self._extract_stufe(company_entry)

            if stufe_entry:
                logger.info(f"Stufe aus Entry gefunden: {stufe_entry}")
                flags.stufe_gefunden = True
            elif stufe_header:
                logger.info(f"Stufe aus Header (Fallback): {stufe_header}")
                flags.stufe_gefunden = True
            else:
                logger.info("Keine Stufe in Xing gefunden")

            return stufe_entry, stufe_header, ist_aktiv

        except Exception as e:
            logger.error(f"Fehler beim Verarbeiten von Xing-Profil: {e}")
            return None, None, True
    
    def _find_company_entry(self, page: Page) -> Optional[any]:
        """Findet den Firmen-Eintrag in der Berufserfahrung"""
        try:
            # Scroll runter damit Berufserfahrungs-Sektion lazy-geladen wird
            page.wait_for_load_state('load', timeout=10000)
            page.wait_for_timeout(2000)
            page.evaluate("window.scrollTo(0, 600)")
            page.wait_for_timeout(1000)
            page.evaluate("window.scrollTo(0, 1500)")
            page.wait_for_timeout(1000)
            page.evaluate("window.scrollTo(0, 2500)")
            page.wait_for_timeout(1500)
            page.evaluate("window.scrollTo(0, 1200)")
            page.wait_for_timeout(1000)

            company_lower = self.match_name.lower()
            company_upper = self.match_name.upper()

            # --- Primäransatz: Berufserfahrungs-Überschrift gezielt abwarten ---
            exp_heading_selectors = [
                'xpath=//h2[normalize-space(text())="Berufserfahrung"]',
                'xpath=//h2[normalize-space(text())="Experience"]',
                'xpath=//h3[normalize-space(text())="Berufserfahrung"]',
                'xpath=//h3[normalize-space(text())="Experience"]',
            ]
            for sel in exp_heading_selectors:
                try:
                    page.wait_for_selector(sel, timeout=2000)
                    break
                except PlaywrightTimeout:
                    continue
                except Exception:
                    continue

            # Berufserfahrungs-Section via Heading direkt targetieren
            exp_section_xpaths = [
                'xpath=//h2[normalize-space(text())="Berufserfahrung"]/ancestor::section[1]',
                'xpath=//h2[normalize-space(text())="Experience"]/ancestor::section[1]',
                'xpath=//h3[normalize-space(text())="Berufserfahrung"]/ancestor::section[1]',
                'xpath=//h3[normalize-space(text())="Experience"]/ancestor::section[1]',
            ]
            for xpath in exp_section_xpaths:
                try:
                    exp_section = page.query_selector(xpath)
                    if exp_section:
                        exp_text = exp_section.inner_text()
                        if company_lower in exp_text.lower():
                            logger.debug(f"Xing Berufserfahrungs-Sektion via Heading gefunden ({len(exp_text)} Zeichen)")
                            return exp_section
                except Exception:
                    continue

            # --- Fallback: XPath-Suche (ohne main/body Fallback) ---
            xpaths = [
                f'//a[contains(@href,"{company_lower}")]/ancestor::*[.//h4][1]',
                f'//a[contains(translate(text(),"{company_upper}","{company_lower}"),"{company_lower}")]/ancestor::*[.//h4][1]',
            ]
            for xpath in xpaths:
                try:
                    entries = page.query_selector_all(f'xpath={xpath}')
                    if entries:
                        logger.debug(f"{self.company_name}-Eintrag via XPath gefunden")
                        return entries[0]
                except Exception:
                    pass

            # Alte Selektoren (eingeloggte Nutzer)
            for sel in ['[class*="experience"]', '[data-section="experience"]']:
                try:
                    section = page.query_selector(sel)
                    if section:
                        entries = section.query_selector_all(f'xpath=.//a[contains(translate(text(),"{company_upper}","{company_lower}"),"{company_lower}")]/ancestor::*[.//h4][1]')
                        if entries:
                            return entries[0]
                except Exception:
                    pass

            # Direkter Firmen-Link (kein main/body Fallback mehr)
            company_link = page.query_selector(f'a[href*="{company_lower}"]')
            if company_link:
                return company_link

        except Exception as e:
            logger.debug(f"Fehler beim Suchen von Firmen-Eintrag: {e}")

        return None
    
    def _extract_stufe_from_header(self, page: Page) -> Optional[str]:
        """Stufe aus dem Xing-Profilkopf (Job-Titel-Bereich oben)"""
        try:
            header_selectors = [
                '[class*="job-title"]',
                '[class*="JobTitle"]',
                '[data-xds="Text"][class*="title"]',
                'h2[class*="title"]',
                '[class*="profile-header"] [class*="title"]',
                '[class*="profileHeader"] [class*="title"]',
                '[class*="position"]',
                'p[class*="subtitle"]',
            ]
            header_text = ""
            for sel in header_selectors:
                try:
                    el = page.query_selector(sel)
                    if el:
                        header_text = (el.inner_text() or "").strip()
                        if header_text and len(header_text) < 200:
                            break
                        header_text = ""
                except Exception:
                    continue

            if not header_text:
                return None

            # Nur weitermachen wenn das gesuchte Unternehmen im Header-Text vorkommt
            if self.match_name.lower() not in header_text.lower():
                logger.debug(f"Xing Header enthält nicht '{self.match_name}' – wird ignoriert")
                return None

            logger.debug(f"Xing Header-Text: {header_text[:80]}")

            # "Jobtitel bei Firma"-Format → Jobtitel extrahieren
            header_candidate = None
            if " bei " in header_text.lower():
                bei_idx = header_text.lower().index(" bei ")
                job_part = header_text[:bei_idx].strip()
                if job_part and len(job_part) > 3:
                    header_candidate = job_part
                    is_valid, category = categorize_stufe(job_part, self.valid_stufen)
                    if category in ["in_scope", "out_of_scope"]:
                        return job_part

            # Teile bei " - " und prüfe jeden Teil
            for part in header_text.replace("–", "-").split("-"):
                part = part.strip()
                is_valid, category = categorize_stufe(part, self.valid_stufen)
                if category in ["in_scope", "out_of_scope"]:
                    return part
                for word in part.split():
                    word = word.strip(".,")
                    is_valid, category = categorize_stufe(word, self.valid_stufen)
                    if category in ["in_scope", "out_of_scope"]:
                        return word

            return header_candidate
        except Exception as e:
            logger.debug(f"Fehler beim Xing Header-Stufe-Extract: {e}")
            return None

    def _check_active_status(self, entry) -> bool:
        """Prüft ob Eintrag noch aktiv ist (bis heute)"""
        try:
            text = entry.inner_text()
            return check_active_status(text)
        except:
            return True
    
    def _extract_stufe(self, entry) -> Optional[str]:
        """Extrahiert Stufe aus Eintrag"""
        first_candidate = None
        try:
            # data-mds="Headline" - Xing-Spezifikation
            stufe_element = entry.query_selector(f'h4[{XING_HEADLINE_ATTR}="{XING_HEADLINE_VALUE}"]')
            if not stufe_element:
                stufe_element = entry.query_selector('h4')
            
            # Wenn entry nur der Link ist: Stufe aus vorherigem h4 per evaluate
            if not stufe_element:
                try:
                    stufe_text_raw = entry.evaluate('''el => {
                        let prev = el.previousElementSibling;
                        while (prev) {
                            let h = prev.querySelector("h4") || (prev.tagName==="H4" ? prev : null);
                            if (h && h.innerText) return h.innerText.trim();
                            prev = prev.previousElementSibling;
                        }
                        let h = el.closest("main")?.querySelector("h4");
                        return h ? h.innerText.trim() : null;
                    }''')
                    if stufe_text_raw:
                        first_candidate = stufe_text_raw
                        is_valid, category = categorize_stufe(stufe_text_raw, self.valid_stufen)
                        if category in ["in_scope", "out_of_scope"]:
                            return stufe_text_raw
                except Exception:
                    pass
            
            if stufe_element:
                stufe_text = stufe_element.inner_text().strip()
                first_candidate = stufe_text
                is_valid, category = categorize_stufe(stufe_text, self.valid_stufen)
                if category in ["in_scope", "out_of_scope"]:
                    return stufe_text
                logger.debug(f"Stufe '{stufe_text}' - Kategorie: {category} – wird trotzdem eingetragen")
        
        except Exception as e:
            logger.debug(f"Fehler beim Extrahieren der Stufe: {e}")
        
        return first_candidate
