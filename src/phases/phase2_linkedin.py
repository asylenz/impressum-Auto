"""
Phase 2: LinkedIn Profil-Scraping
"""

import logging
from typing import Optional, List, Tuple
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from src.models import Lead, ProcessingFlags
from src.utils import extract_phone_from_href, categorize_stufe, check_active_status
from src.discovery.search_provider import PlaywrightGoogleSearch
from src.constants import LINKEDIN_CONTACT_INFO_BUTTON, LINKEDIN_CONTACT_INFO_MODAL

logger = logging.getLogger(__name__)

class LinkedInPhase:
    """Phase 2: LinkedIn Profil-Scraping"""
    
    def __init__(self, config, rate_limiter):
        self.config = config
        self.rate_limiter = rate_limiter
        self.valid_stufen = config.valid_stufen
        self.company_name = config.company_name
    
    def process(self, page: Page, url: str, lead: Lead, flags: ProcessingFlags) -> Tuple[Optional[str], List[str], bool]:
        """
        Verarbeitet LinkedIn-URL
        Gibt (Stufe, [Telefonnummern], ist_aktiv) zurück
        """
        if not url:
            return None, [], True  # Default: aktiv
        
        try:
            logger.info(f"Öffne LinkedIn-Profil: {url}")
            
            # Rate-Limiting
            self.rate_limiter.acquire('linkedin')
            
            # Profil öffnen
            page.goto(url, wait_until='domcontentloaded')
            page.wait_for_timeout(2000)  # Kurze Pause für JS-Rendering
            
            # Stufe zuerst aus Headline versuchen (oft sichtbar ohne Scroll; Experience lädt manchmal nicht)
            stufe = self._extract_stufe_from_headline(page)
            
            # Company-Eintrag in Experience suchen (für präzise Stufe + Aktiv-Check)
            company_entry = self._find_company_entry(page)
            
            if not company_entry:
                if stufe:
                    logger.info(f"Stufe aus Headline: {stufe} (Experience-Sektion nicht gefunden)")
                    flags.stufe_gefunden = True
                else:
                    logger.info(f"Kein {self.company_name}-Eintrag in LinkedIn Experience gefunden")
                # Trotzdem Telefonnummern versuchen wenn nötig
                telefonnummern = []
                if not flags.telefonnummer_gefunden and not flags.nur_stufe_suchen:
                    telefonnummern = self._extract_contact_info(page, lead)
                    if telefonnummern:
                        flags.telefonnummer_gefunden = True
                return stufe, telefonnummern, True
            
            # Status prüfen (Present/Heute)
            ist_aktiv = self._check_active_status(company_entry)
            
            if not ist_aktiv:
                logger.info(f"Person ist nicht mehr bei {self.company_name} (ehemaliger Eintrag)")
                return None, [], False
            
            logger.info(f"Person ist aktiv bei {self.company_name}")
            
            # Stufe aus Experience-Eintrag (überschreibt Headline falls genauer)
            stufe_from_entry = self._extract_stufe(company_entry)
            if stufe_from_entry:
                stufe = stufe_from_entry
            
            if stufe:
                logger.info(f"Stufe gefunden: {stufe}")
                flags.stufe_gefunden = True
            else:
                logger.info("Keine gültige Stufe in LinkedIn gefunden")
            
            # Telefonnummern nur holen wenn noch keine vorhanden
            telefonnummern = []
            if not flags.telefonnummer_gefunden and not flags.nur_stufe_suchen:
                telefonnummern = self._extract_contact_info(page, lead)
                
                if telefonnummern:
                    logger.info(f"{len(telefonnummern)} Telefonnummer(n) gefunden")
                    flags.telefonnummer_gefunden = True
            
            return stufe, telefonnummern, ist_aktiv
            
        except Exception as e:
            logger.error(f"Fehler beim Verarbeiten von LinkedIn-Profil: {e}")
            return None, [], True
    
    def _find_company_entry(self, page: Page) -> Optional[any]:
        """Findet den Firmen-Eintrag in der Experience-Sektion."""
        try:
            # Scroll runter
            page.wait_for_timeout(2000)
            page.evaluate("window.scrollTo(0, 600)")
            page.wait_for_timeout(1000)
            page.evaluate("window.scrollTo(0, 1200)")
            page.wait_for_timeout(1500)
            
            all_entries = []
            company_lower = self.company_name.lower()
            company_upper = self.company_name.upper()
            
            try:
                # Suche nach <li> die den Firmennamen enthalten
                # translate() für case-insensitive check
                xpath = f'//li[descendant::*[contains(translate(text(), "{company_upper}", "{company_lower}"), "{company_lower}")]]'
                entries = page.query_selector_all(f'xpath={xpath}')
                
                if entries:
                    all_entries.extend(entries)
                
                # Fallback: div/article
                if not all_entries:
                    xpath_div = f'//*[self::div or self::article][descendant::*[contains(translate(text(), "{company_upper}", "{company_lower}"), "{company_lower}")]]'
                    entries_div = page.query_selector_all(f'xpath={xpath_div}')
                    if entries_div:
                        all_entries.extend(entries_div)
                        
            except Exception as e:
                logger.debug(f"XPath-Suche fehlgeschlagen: {e}")
            
            # Prüfe jeden gefundenen Eintrag auf nested Sub-Positionen
            final_entries = []
            for li in all_entries:
                try:
                    nested_lis = li.query_selector_all('xpath=.//ul/li')
                    if nested_lis:
                        for sub_li in nested_lis:
                            if sub_li not in final_entries:
                                final_entries.append(sub_li)
                    else:
                        if li not in final_entries:
                            final_entries.append(li)
                except Exception:
                    pass
            
            # Oberster Eintrag mit "heute"
            if final_entries:
                logger.debug(f"{len(final_entries)} {self.company_name}-Eintrag/Einträge gefunden")
                for entry in final_entries:
                    try:
                        text = entry.inner_text().lower()
                        if any(kw in text for kw in ['–heute', '- heute', 'present', 'current', 'bis heute', 'bis jetzt']):
                            logger.debug("Aktiven Eintrag gewählt (Heute/Present im Text)")
                            return entry
                    except Exception:
                        pass
                logger.debug("Obersten Eintrag gewählt (kein 'Heute' erkannt)")
                return final_entries[0]
            
        except PlaywrightTimeout:
            logger.debug("Experience-Sektion nicht gefunden (Timeout)")
        except Exception as e:
            logger.debug(f"Fehler beim Suchen von Firmen-Eintrag: {e}")
        
        return None
    
    def _check_active_status(self, entry) -> bool:
        """Prüft ob Eintrag noch aktiv ist (Present/Heute)"""
        try:
            text = entry.inner_text()
            result = check_active_status(text)
            return result
        except:
            return True  # Default: aktiv
    
    def _extract_stufe(self, entry) -> Optional[str]:
        """Extrahiert Stufe aus Eintrag in Berufserfahrung (Experience)."""
        def clean(s: str) -> str:
            s = (s or "").strip().lstrip("|").strip()
            return s

        try:
            # Verschiedene Selektoren für Jobtitel
            title_selectors = [
                'xpath=.//span[@aria-hidden="true"][1]',
                'xpath=.//div[contains(@class, "display-flex")]//span[1]',
                'xpath=.//span[contains(@class, "t-14")][1]',
                'xpath=.//*[contains(@class, "experience-item")]//span[1]',
            ]
            for idx, sel in enumerate(title_selectors):
                el = entry.query_selector(sel)
                if el:
                    stufe_text = clean(el.inner_text())
                    if stufe_text:
                        is_valid, category = categorize_stufe(stufe_text, self.valid_stufen)
                        
                        if category in ["in_scope", "out_of_scope"]:
                            return stufe_text
                        logger.debug(f"Stufe-Kandidat: '{stufe_text}' (Kategorie: {category})")

            # Fallback: Alle Zeilen des Eintrags durchgehen
            full_text = entry.inner_text()
            lines = [clean(line) for line in full_text.split('\n') if line.strip()]
            
            for line_idx, line in enumerate(lines):
                if not line or len(line) > 80:
                    continue
                is_valid, category = categorize_stufe(line, self.valid_stufen)
                if category in ["in_scope", "out_of_scope"]:
                    return line
                
                first_word = line.split()[0] if line.split() else ""
                if first_word:
                    is_valid, category = categorize_stufe(first_word, self.valid_stufen)
                    if category in ["in_scope", "out_of_scope"]:
                        return first_word

        except Exception as e:
            logger.debug(f"Fehler beim Extrahieren der Stufe: {e}")
        return None
    
    def _extract_stufe_from_headline(self, page: Page) -> Optional[str]:
        """Stufe aus der Profil-Headline"""
        try:
            headline_selectors = [
                'div.top-card-layout__headline',
                '[data-view-name="profileCard"] div.text-body-medium',
                'section[data-view-name="profileCard"] div:first-of-type',
                'h2.top-card-layout__headline',
                '.pv-text-details__left-panel h2',
                '#top-card div.text-body-medium',
            ]
            headline_text = ""
            for sel in headline_selectors:
                el = page.query_selector(sel)
                if el:
                    headline_text = (el.inner_text() or "").strip()
                    if headline_text and len(headline_text) < 200:
                        break
            
            if not headline_text:
                return None
            
            logger.debug(f"LinkedIn Headline: {headline_text[:80]}...")
            
            # Teile bei " - " und prüfe jeden Teil
            for part in headline_text.replace("–", "-").split("-"):
                part = part.strip()
                is_valid, category = categorize_stufe(part, self.valid_stufen)
                if category in ["in_scope", "out_of_scope"]:
                    return part
                # Einzelne Wörter
                for word in part.split():
                    word = word.strip(".,")
                    is_valid, category = categorize_stufe(word, self.valid_stufen)
                    if category in ["in_scope", "out_of_scope"]:
                        return word
            
            return None
        except Exception as e:
            logger.debug(f"Fehler beim Headline-Stufe-Extract: {e}")
            return None
    
    def _extract_contact_info(self, page: Page, lead: Lead) -> List[str]:
        """Extrahiert Telefonnummern aus Contact Info Modal"""
        telefonnummern = []
        
        try:
            # "Contact info" Link finden und klicken
            contact_info_selectors = [
                LINKEDIN_CONTACT_INFO_BUTTON,
                'a[href*="contact-info"]',
                'a:has-text("Contact info")',
                'a:has-text("Kontaktinfo")'
            ]
            
            clicked = False
            for selector in contact_info_selectors:
                try:
                    page.click(selector, timeout=2000)
                    clicked = True
                    logger.debug(f"Contact Info Modal geöffnet (Selektor: {selector})")
                    break
                except:
                    continue
            
            if not clicked:
                logger.debug("Contact Info Button nicht gefunden")
                return []
            
            # Warte auf Modal
            page.wait_for_selector(LINKEDIN_CONTACT_INFO_MODAL, timeout=5000)
            page.wait_for_timeout(1000)
            
            # Telefonnummer in Modal suchen
            phone_xpath = '//section[.//h3[contains(text(), "Phone") or contains(text(), "Telefon")]]//span'
            phone_elements = page.query_selector_all(f'xpath={phone_xpath}')
            
            for element in phone_elements:
                text = element.inner_text().strip()
                if any(char.isdigit() for char in text) and len(text) > 5:
                    if text not in telefonnummern:
                        telefonnummern.append(text)
            
            # Webseite suchen (falls keine Telefonnummer)
            if not telefonnummern:
                telefonnummern = self._extract_from_website(page, lead)
            
            # Modal schließen
            try:
                page.keyboard.press('Escape')
            except:
                pass
            
        except PlaywrightTimeout:
            logger.debug("Contact Info Modal nicht gefunden")
        except Exception as e:
            logger.error(f"Fehler beim Extrahieren von Contact Info: {e}")
        
        return telefonnummern[:2]
    
    def _extract_from_website(self, page: Page, lead: Lead) -> List[str]:
        """Extrahiert Telefonnummer von externer Webseite (via Impressum)"""
        telefonnummern = []
        
        try:
            # Webseite-Link im Modal suchen
            website_xpath = '//section[.//h3[contains(text(), "Website") or contains(text(), "Websites")]]//a[@href]'
            website_links = page.query_selector_all(f'xpath={website_xpath}')
            
            for link in website_links:
                url = link.get_attribute('href')
                
                # Ignoriere Firmenseite (z.B. tecis.de) und linkedin.com
                company_domain = self.config.company_name.lower().replace(" ", "")
                if not url or company_domain in url.lower() or 'linkedin.com' in url:
                    continue
                
                logger.info(f"Prüfe externe Webseite: {url}")
                
                # Öffne Webseite in neuem Tab
                new_page = page.context.new_page()
                
                try:
                    new_page.goto(url, wait_until='domcontentloaded', timeout=15000)
                    
                    # Impressum-Link suchen
                    impressum_link = new_page.query_selector('a:has-text("Impressum"), a[href*="impressum"]')
                    
                    if impressum_link:
                        impressum_url = impressum_link.get_attribute('href')
                        if not impressum_url.startswith('http'):
                            from urllib.parse import urljoin
                            impressum_url = urljoin(url, impressum_url)
                        
                        logger.debug(f"Öffne Impressum: {impressum_url}")
                        new_page.goto(impressum_url, wait_until='domcontentloaded', timeout=10000)
                    
                    # Prüfe Geschäftsführer
                    text = new_page.inner_text('body')
                    if lead.vorname.lower() in text.lower() and lead.nachname.lower() in text.lower():
                        logger.info("Geschäftsführer-Name im Impressum gefunden")
                        
                        # Suche Telefonnummer
                        tel_links = new_page.query_selector_all('a[href^="tel:"]')
                        for tel_link in tel_links:
                            href = tel_link.get_attribute('href')
                            if href:
                                nummer = extract_phone_from_href(href)
                                if nummer and nummer not in telefonnummern:
                                    telefonnummern.append(nummer)
                        
                        if telefonnummern:
                            break
                
                finally:
                    new_page.close()
                
                break
        
        except Exception as e:
            logger.debug(f"Fehler beim Extrahieren von externer Webseite: {e}")
        
        return telefonnummern
