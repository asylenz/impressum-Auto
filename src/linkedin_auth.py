"""
LinkedIn Authentifizierung
"""

import logging
import time
from pathlib import Path
from playwright.sync_api import Page, BrowserContext, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

class LinkedInAuth:
    """LinkedIn Login-Handler"""
    
    def __init__(self, config):
        self.config = config
        self.email = config.linkedin_email
        self.password = config.linkedin_password
        self.state_dir = Path('linkedin_state')
        self.state_dir.mkdir(exist_ok=True)
    
    def login(self, context: BrowserContext, page: Page) -> bool:
        """
        Führt LinkedIn-Login aus
        Gibt True zurück wenn erfolgreich
        """
        try:
            logger.info("Starte LinkedIn-Login...")
            
            # Zu Login-Seite navigieren
            page.goto('https://www.linkedin.com/login', wait_until='domcontentloaded')
            page.wait_for_timeout(2000)
            
            # Prüfen ob bereits eingeloggt (redirect zu Feed)
            current_url = page.url
            if 'feed' in current_url or 'mynetwork' in current_url:
                logger.info("Bereits bei LinkedIn eingeloggt (redirect zu Feed)")
                return True
            
            # Warten auf Login-Formular
            try:
                page.wait_for_selector('input[name="session_key"], #username', timeout=10000)
            except PlaywrightTimeout:
                # Kein Login-Form → Prüfe ob Challenge/CAPTCHA
                if 'checkpoint' in page.url or 'challenge' in page.url:
                    logger.warning("LinkedIn zeigt Challenge/CAPTCHA")
                    return self._handle_challenge(page)
                
                logger.error(f"Login-Formular nicht gefunden. Aktuelle URL: {page.url}")
                return False
            
            # E-Mail eingeben
            email_selectors = ['input[name="session_key"]', '#username']
            for selector in email_selectors:
                try:
                    page.fill(selector, self.email, timeout=2000)
                    logger.debug(f"E-Mail eingegeben (Selektor: {selector})")
                    break
                except PlaywrightTimeout:
                    continue
            
            # Passwort eingeben
            password_selectors = ['input[name="session_password"]', '#password']
            for selector in password_selectors:
                try:
                    page.fill(selector, self.password, timeout=2000)
                    logger.debug(f"Passwort eingegeben (Selektor: {selector})")
                    break
                except PlaywrightTimeout:
                    continue
            
            # "Angemeldet bleiben" ankreuzen (optional)
            try:
                remember_checkbox = page.query_selector('input[type="checkbox"]')
                if remember_checkbox and not remember_checkbox.is_checked():
                    remember_checkbox.check()
            except:
                pass
            
            # Login-Button klicken
            submit_selectors = ['button[type="submit"]', 'button[data-litms-control-urn*="login"]']
            for selector in submit_selectors:
                try:
                    page.click(selector, timeout=2000)
                    logger.debug(f"Login-Button geklickt (Selektor: {selector})")
                    break
                except PlaywrightTimeout:
                    continue
            
            # Warten auf Redirect zum Feed oder Verify-Seite
            page.wait_for_timeout(3000)
            
            # Prüfen ob Login erfolgreich
            current_url = page.url
            
            if 'feed' in current_url or 'mynetwork' in current_url:
                logger.info("LinkedIn-Login erfolgreich")
                self._save_session(context)
                return True
            
            elif 'checkpoint' in current_url or 'challenge' in current_url:
                return self._handle_challenge(page)
            
            logger.error(f"LinkedIn-Login fehlgeschlagen. Aktuelle URL: {current_url}")
            return False
            
        except Exception as e:
            logger.error(f"Fehler beim LinkedIn-Login: {e}")
            return False
    
    def _handle_challenge(self, page: Page) -> bool:
        """Behandelt LinkedIn Challenge/CAPTCHA/2FA"""
        logger.warning("LinkedIn verlangt zusätzliche Verifizierung (2FA/Captcha)")
        
        # Im headless-Modus kann das nicht funktionieren
        if self.config.get('browser.headless', True):
            logger.error("2FA/Captcha im headless-Modus nicht möglich. Bitte browser.headless: false in config.yaml setzen.")
            return False
        
        logger.warning("Bitte manuell im Browser verifizieren und dann Enter drücken...")
        
        # Warten auf Benutzer-Eingabe
        input("Drücke Enter wenn Verifizierung abgeschlossen ist...")
        
        # Prüfen ob jetzt eingeloggt
        current_url = page.url
        if 'feed' in current_url or 'mynetwork' in current_url:
            logger.info("LinkedIn-Login nach Verifizierung erfolgreich")
            return True
        
        logger.error(f"Verifizierung fehlgeschlagen. Aktuelle URL: {current_url}")
        return False
    
    def is_logged_in(self, page: Page, profile_url: str = None) -> bool:
        """
        Prüft ob eingeloggt. Wenn profile_url gesetzt: öffnet Profil und prüft ob Profil-Inhalt sichtbar ist.
        So wird die persistente Session genutzt, ohne die Startseite zu prüfen.
        """
        try:
            if profile_url:
                logger.debug("Prüfe Login-Status durch direkten Profil-Zugriff...")
                page.goto(profile_url, wait_until='domcontentloaded', timeout=15000)
                page.wait_for_timeout(3000)  # Warten bis Seite geladen ist
                
                # Prüfe ob Profil-Inhalt sichtbar ist
                if self._profile_content_visible(page):
                    logger.info("Profil-Seite geladen (bereits eingeloggt)")
                    return True
                
                # Prüfe ob Login-Wall erscheint
                current_url = page.url
                if 'authwall' in current_url or 'login' in current_url:
                    logger.debug("Login-Wall erkannt → nicht eingeloggt")
                    return False
                
                # Prüfe ob auf Feed redirected wurde (dann erfolgreich eingeloggt)
                if 'feed' in current_url or 'mynetwork' in current_url:
                    logger.info("Zu Feed redirected → bereits eingeloggt")
                    return True
                
                # Unbekannter Zustand - konservativer Ansatz: nicht eingeloggt
                logger.debug(f"Unbekannter Zustand nach Profil-Zugriff: {current_url}")
                return False
            
            # Ohne profile_url: klassische Prüfung über Startseite
            page.goto('https://www.linkedin.com', wait_until='domcontentloaded')
            page.wait_for_timeout(2000)
            current_url = page.url
            
            if 'feed' in current_url or 'mynetwork' in current_url:
                logger.info("Bereits bei LinkedIn eingeloggt")
                return True
            
            if 'login' in current_url or 'authwall' in current_url:
                return False
            
            return False
            
        except Exception as e:
            logger.debug(f"Fehler beim Prüfen des Login-Status: {e}")
            return False
    
    def _profile_content_visible(self, page: Page) -> bool:
        """Prüft ob die aktuelle Seite ein LinkedIn-Profil zeigt (Headline/Profilkarte)."""
        profile_selectors = [
            'div.top-card-layout__headline',
            '[data-view-name="profileCard"]',
            '.pv-text-details__left-panel h2',
            '#experience',
            'section[data-view-name*="profile"]',
        ]
        for sel in profile_selectors:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    return True
            except Exception:
                continue
        # Login-Formular sichtbar = kein Profil
        try:
            if page.query_selector('input[name="session_key"]'):
                return False
        except Exception:
            pass
        return False
    
    def load_session(self, context: BrowserContext) -> bool:
        """Lädt gespeicherte Session (Cookies)"""
        try:
            state_file = self.state_dir / 'cookies.json'
            if state_file.exists():
                logger.info("Lade gespeicherte LinkedIn-Session...")
                # Playwright kann keine Cookies direkt laden, aber wir können sie manuell setzen
                import json
                with open(state_file, 'r') as f:
                    cookies = json.load(f)
                context.add_cookies(cookies)
                return True
        except Exception as e:
            logger.debug(f"Fehler beim Laden der Session: {e}")
        
        return False
    
    def _save_session(self, context: BrowserContext):
        """Speichert aktuelle Session (Cookies)"""
        try:
            state_file = self.state_dir / 'cookies.json'
            cookies = context.cookies()
            
            import json
            with open(state_file, 'w') as f:
                json.dump(cookies, f)
            
            logger.info("LinkedIn-Session gespeichert")
        except Exception as e:
            logger.warning(f"Fehler beim Speichern der Session: {e}")
