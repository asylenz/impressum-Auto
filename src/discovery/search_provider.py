"""
Link-Discovery über lokale Google-Suche mit Playwright, Crawl4AI oder Serper API
"""

import logging
import re
import time
import asyncio
import os
from typing import List, Optional
from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout

from src.models import SearchResult, Lead

logger = logging.getLogger(__name__)

class SearchProvider:
    """Interface für Such-Provider"""
    
    def search(self, query: str) -> List[SearchResult]:
        """Führt Suche aus und gibt Ergebnisse zurück"""
        raise NotImplementedError

class PlaywrightGoogleSearch(SearchProvider):
    """Lokale Google-Suche mit Playwright"""
    
    def __init__(self, config, rate_limiter):
        self.config = config
        self.rate_limiter = rate_limiter
        self.selectors = config.get('google_selectors', {})
        self.user_agent = config.get('browser.user_agent')
        self.timeout = config.get('browser.timeout', 30000)
        
        # Browser-Context wird pro Batch wiederverwendet
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    def __enter__(self):
        """Context Manager: Browser starten"""
        headless = self.config.get('browser.headless', True)
        
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=headless)
        self.context = self.browser.new_context(
            user_agent=self.user_agent,
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = self.context.new_page()
        self.page.set_default_timeout(self.timeout)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager: Browser schließen"""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def _handle_consent(self):
        """Behandelt Google Consent-Dialog"""
        try:
            # Mehrere mögliche Consent-Button-Varianten
            possible_consent_buttons = [
                'button:has-text("Alle akzeptieren")',
                'button:has-text("Accept all")',
                'button:has-text("Alles akzeptieren")',
                'button[aria-label*="Accept"]',
                'button[aria-label*="akzeptieren"]',
                '#L2AGLb',  # Google's Consent Button ID
                'button:has-text("Ich stimme zu")'
            ]
            
            for selector in possible_consent_buttons:
                try:
                    self.page.wait_for_selector(selector, timeout=2000)
                    self.page.click(selector)
                    logger.debug(f"Google Consent akzeptiert mit: {selector}")
                    time.sleep(1)
                    return
                except PlaywrightTimeout:
                    continue
            
            # Kein Consent-Dialog gefunden - nicht schlimm
            logger.debug("Kein Consent-Dialog gefunden")
            
        except Exception as e:
            logger.debug(f"Fehler beim Consent-Handling: {e}")
    
    def search(self, query: str) -> List[SearchResult]:
        """Führt Google-Suche aus und gibt erste organische Ergebnisse zurück"""
        # Rate-Limiting
        self.rate_limiter.wait_if_needed('google_search')
        
        try:
            logger.debug(f"Google-Suche: {query}")
            
            # Zu Google navigieren
            self.page.goto('https://www.google.com', wait_until='domcontentloaded')
            
            # Consent-Dialog behandeln
            self._handle_consent()
            
            # Suchfeld finden und Query eingeben
            search_box = self.selectors.get('search_box', 'textarea[name="q"], input[name="q"]')
            self.page.wait_for_selector(search_box)
            self.page.fill(search_box, query)
            
            # Suche absenden
            self.page.keyboard.press('Enter')
            
            # Auf Ergebnisse warten - verschiedene Selektoren probieren
            result_container = None
            possible_selectors = [
                'div#search div.g',  # Standard
                'div#rso div.g',     # Alternative
                'div#search',        # Fallback: Haupt-Container
                '#rso'               # Alternative Haupt-Container
            ]
            
            for selector in possible_selectors:
                try:
                    self.page.wait_for_selector(selector, timeout=5000)
                    result_container = selector
                    logger.debug(f"Ergebnisse gefunden mit Selektor: {selector}")
                    break
                except PlaywrightTimeout:
                    continue
            
            if not result_container:
                # Debug: Screenshot erstellen
                screenshot_path = f"debug_google_search_{int(time.time())}.png"
                self.page.screenshot(path=screenshot_path)
                logger.error(f"Keine Suchergebnisse gefunden. Screenshot gespeichert: {screenshot_path}")
                logger.error(f"Aktueller HTML-Ausschnitt: {self.page.content()[:500]}")
                return []
            
            # Ergebnisse extrahieren
            results = []
            containers = self.page.query_selector_all('div.g')
            
            for container in containers[:5]:  # Maximal 5 Ergebnisse
                try:
                    # Link-Element finden
                    link_selector = self.selectors.get('result_link', 'a[href]:not([href^="/"])')
                    link_element = container.query_selector(link_selector)
                    
                    if not link_element:
                        continue
                    
                    url = link_element.get_attribute('href')
                    if not url or url.startswith('/') or 'google.com' in url:
                        continue
                    
                    # Titel extrahieren
                    title_element = link_element.query_selector('h3')
                    title = title_element.inner_text() if title_element else ""
                    
                    # Snippet extrahieren (optional)
                    snippet = ""
                    snippet_elements = container.query_selector_all('div[style*="line-height"], span')
                    for el in snippet_elements:
                        text = el.inner_text().strip()
                        if len(text) > 20:
                            snippet = text
                            break
                    
                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet
                    ))
                    
                except Exception as e:
                    logger.debug(f"Fehler beim Parsen eines Ergebnisses: {e}")
                    continue
            
            # Rate-Limiting aufzeichnen
            self.rate_limiter.record_request('google_search')
            
            logger.debug(f"{len(results)} Ergebnisse gefunden")
            return results
            
        except Exception as e:
            logger.error(f"Fehler bei Google-Suche: {e}")
            return []

class Crawl4AIGoogleSearch(SearchProvider):
    """Google-Suche mit Crawl4AI (Anti-Bot mit Stealth + Undetected Mode)"""
    
    def __init__(self, config, rate_limiter):
        self.config = config
        self.rate_limiter = rate_limiter
        self.timeout = config.get('browser.timeout', 30000)
        
    async def search_async(self, query: str) -> List[SearchResult]:
        """Asynchrone Suche mit Crawl4AI"""
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
        from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
        
        # Rate-Limiting
        self.rate_limiter.wait_if_needed('google_search')
        
        try:
            logger.debug(f"Crawl4AI Google-Suche: {query}")
            
            # Config-Einstellungen
            enable_stealth = self.config.get('discovery.crawl4ai.enable_stealth', True)
            enable_undetected = self.config.get('discovery.crawl4ai.enable_undetected', True)
            headless = self.config.get('discovery.crawl4ai.headless', True)
            
            # Browser-Config mit Stealth Mode
            browser_config = BrowserConfig(
                enable_stealth=enable_stealth,
                headless=headless,
                verbose=False
            )
            
            # Optional: Undetected Adapter für maximale Anti-Bot-Evasion
            crawler_strategy = None
            if enable_undetected:
                try:
                    from crawl4ai import UndetectedAdapter
                    adapter = UndetectedAdapter()
                    crawler_strategy = AsyncPlaywrightCrawlerStrategy(
                        browser_config=browser_config,
                        browser_adapter=adapter
                    )
                    logger.debug("Undetected Browser Mode aktiviert")
                except Exception as e:
                    logger.warning(f"Undetected Adapter konnte nicht geladen werden: {e}")
            
            # Crawler erstellen
            async with AsyncWebCrawler(
                crawler_strategy=crawler_strategy,
                config=browser_config
            ) as crawler:
                # Google-Suche URL konstruieren
                search_url = f"https://www.google.com/search?q={quote_plus(query)}"
                
                # Seite crawlen
                result = await crawler.arun(
                    url=search_url,
                    config=CrawlerRunConfig(
                        delay_before_return_html=3.0,  # Mehr Zeit für Consent-Dialog
                        page_timeout=30000,  # 30 Sekunden Timeout
                        magic=True,  # Automatisches Handling von Popups/Consent-Bannern
                        remove_overlay_elements=True,  # Overlay-Elemente entfernen
                        js_code="""
                        // Google Consent-Dialog manuell behandeln als Fallback
                        (function() {
                            const selectors = [
                                'button:has-text("Accept all")',
                                'button:has-text("Alle akzeptieren")',
                                'button:has-text("Alles akzeptieren")',
                                '#L2AGLb',
                                'button[id*="accept"]',
                                'form[action*="consent"] button[type="submit"]'
                            ];
                            
                            for (const sel of selectors) {
                                const btns = document.querySelectorAll(sel);
                                for (const btn of btns) {
                                    if (btn && btn.offsetParent !== null) {
                                        try {
                                            btn.click();
                                            console.log('Clicked consent:', sel);
                                            return;
                                        } catch (e) {}
                                    }
                                }
                            }
                        })();
                        """
                    )
                )
                
                if not result.success:
                    logger.error(f"Crawl4AI Fehler: {result.error_message}")
                    return []
                
                # HTML parsen und Ergebnisse extrahieren
                results = self._parse_google_results(result.html)
                
                # Rate-Limiting aufzeichnen
                self.rate_limiter.record_request('google_search')
                
                logger.debug(f"{len(results)} Ergebnisse gefunden")
                return results
                
        except Exception as e:
            logger.error(f"Fehler bei Crawl4AI Google-Suche: {e}")
            return []
    
    def _parse_google_results(self, html: str) -> List[SearchResult]:
        """Extrahiert Suchergebnisse aus Google HTML mit BeautifulSoup"""
        from bs4 import BeautifulSoup
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            results = []
            
            # Suchergebnis-Container finden (div.g)
            for g_div in soup.select('div.g')[:5]:
                try:
                    # Link-Element finden
                    link = g_div.select_one('a[href]')
                    if not link:
                        continue
                    
                    url = link.get('href')
                    if not url or url.startswith('/') or 'google.com' in url:
                        continue
                    
                    # Titel extrahieren
                    title_elem = g_div.select_one('h3')
                    title = title_elem.get_text() if title_elem else ""
                    
                    # Snippet extrahieren
                    snippet_elem = g_div.select_one('div[data-sncf], div[style*="line-height"]')
                    snippet = snippet_elem.get_text() if snippet_elem else ""
                    
                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet
                    ))
                    
                except Exception as e:
                    logger.debug(f"Fehler beim Parsen eines Ergebnisses: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Fehler beim HTML-Parsing: {e}")
            return []
    
    def search(self, query: str) -> List[SearchResult]:
        """Synchroner Wrapper für async search"""
        return asyncio.run(self.search_async(query))

class SerperGoogleSearch(SearchProvider):
    """Google-Suche mit Serper API (keine CAPTCHA-Probleme)"""
    
    def __init__(self, config, rate_limiter):
        self.config = config
        self.rate_limiter = rate_limiter
        self.api_key = os.getenv('SERPER_API_KEY')
        
        if not self.api_key:
            raise ValueError("SERPER_API_KEY nicht in .env gesetzt! Gehe zu https://serper.dev und hole dir einen API Key.")
    
    def search(self, query: str) -> List[SearchResult]:
        """Führt Google-Suche über Serper API aus"""
        import requests
        
        # Rate-Limiting
        self.rate_limiter.wait_if_needed('google_search')
        
        try:
            logger.debug(f"Serper API Suche: {query}")
            
            url = "https://google.serper.dev/search"
            
            payload = {
                "q": query,
                "num": 5  # Maximal 5 Ergebnisse
            }
            
            headers = {
                'X-API-KEY': self.api_key,
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Serper API Fehler {response.status_code}: {response.text}")
                return []
            
            data = response.json()
            
            # Organische Ergebnisse extrahieren
            results = []
            for item in data.get('organic', [])[:5]:
                url = item.get('link', '')
                title = item.get('title', '')
                snippet = item.get('snippet', '')
                
                logger.debug(f"Serper Ergebnis: {title[:50]}... | {url}")
                
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet
                ))
            
            # Rate-Limiting aufzeichnen
            self.rate_limiter.record_request('google_search')
            
            logger.debug(f"{len(results)} Ergebnisse von Serper API")
            return results
            
        except Exception as e:
            logger.error(f"Fehler bei Serper API Suche: {e}")
            return []

class LinkDiscovery:
    """Link-Discovery für alle Plattformen"""
    
    def __init__(self, config, rate_limiter):
        self.config = config
        self.rate_limiter = rate_limiter
        self.url_patterns = {
            'tecis': re.compile(config.get('url_patterns.tecis', r'^https?://(?:www\.)?tecis\.de/[a-zA-Z0-9-]+(?:(?:/kontaktuebersicht|/impressum)\.html|\.html)?$')),
            'linkedin': re.compile(config.get('url_patterns.linkedin', r'^https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9-]+/?$')),
            'xing': re.compile(config.get('url_patterns.xing', r'^https?://(?:www\.)?xing\.com/profile/[a-zA-Z0-9_]+/?$')),
            'creditreform': re.compile(config.get('url_patterns.creditreform', r'^https?://firmeneintrag\.creditreform\.de/\d+/\d+/.+$'))
        }
    
    def discover_urls(self, lead: Lead) -> dict:
        """Findet URLs für alle 4 Plattformen"""
        urls = {
            'tecis': None,
            'linkedin': None,
            'xing': None,
            'creditreform': None
        }
        
        queries = self._build_queries(lead)
        
        # Provider auswählen (config-gesteuert)
        use_serper = self.config.get('discovery.use_serper', False)
        use_crawl4ai = self.config.get('discovery.use_crawl4ai', False)
        
        if use_serper:
            logger.info("Verwende Serper API (zuverlässig, keine CAPTCHA)")
            search_provider = SerperGoogleSearch(self.config, self.rate_limiter)
            
            # Serper braucht keinen Context Manager
            for platform, query in queries.items():
                logger.info(f"Suche {platform}-URL für {lead.full_name}...")
                
                results = search_provider.search(query)
                url = self._validate_result(results, platform, lead)
                
                if url:
                    logger.info(f"{platform} URL gefunden: {url}")
                    urls[platform] = url
                else:
                    logger.info(f"Kein {platform}-Eintrag gefunden")
                    
        elif use_crawl4ai:
            logger.info("Verwende Crawl4AI mit Anti-Bot-Schutz für Link-Discovery")
            search_provider = Crawl4AIGoogleSearch(self.config, self.rate_limiter)
            
            # Crawl4AI braucht keinen Context Manager
            for platform, query in queries.items():
                logger.info(f"Suche {platform}-URL für {lead.full_name}...")
                
                results = search_provider.search(query)
                url = self._validate_result(results, platform, lead)
                
                if url:
                    logger.info(f"{platform} URL gefunden: {url}")
                    urls[platform] = url
                else:
                    logger.info(f"Kein {platform}-Eintrag gefunden")
        else:
            logger.info("Verwende Playwright (Fallback) für Link-Discovery")
            # Fallback auf Playwright mit Context Manager
            with PlaywrightGoogleSearch(self.config, self.rate_limiter) as search:
                for platform, query in queries.items():
                    logger.info(f"Suche {platform}-URL für {lead.full_name}...")
                    
                    results = search.search(query)
                    url = self._validate_result(results, platform, lead)
                    
                    if url:
                        logger.info(f"{platform} URL gefunden: {url}")
                        urls[platform] = url
                    else:
                        logger.info(f"Kein {platform}-Eintrag gefunden")
        
        return urls
    
    def _build_queries(self, lead: Lead) -> dict:
        """Erstellt Such-Queries für alle Plattformen (nutzt Full Name ohne Aufteilung)"""
        name = lead.full_name
        return {
            'tecis': f'site:tecis.de "{name}"',
            'linkedin': f'site:linkedin.com/in/ "{name}" tecis',
            'xing': f'site:xing.com/profile "{name}" tecis',
            'creditreform': f'site:firmeneintrag.creditreform.de "{name}" Versicherungsmakler'
        }
    
    def _validate_result(self, results: List[SearchResult], platform: str, lead: Lead) -> Optional[str]:
        """Validiert Suchergebnis gegen URL-Pattern und Name"""
        pattern = self.url_patterns.get(platform)
        
        for result in results:
            # URL-Pattern prüfen
            pattern_match = pattern.match(result.url)
            logger.debug(f"Prüfe URL: {result.url} | Pattern-Match: {bool(pattern_match)}")
            
            if not pattern_match:
                continue
            
            # Name im Titel oder URL prüfen
            text_to_check = (result.title + " " + result.url).lower()
            vorname_lower = lead.vorname.lower()
            nachname_lower = lead.nachname.lower()
            
            name_match = vorname_lower in text_to_check and nachname_lower in text_to_check
            logger.debug(f"Name-Check: Vorname={vorname_lower in text_to_check}, Nachname={nachname_lower in text_to_check}")
            
            if name_match:
                return result.url
        
        return None
