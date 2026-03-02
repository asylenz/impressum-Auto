"""
Company-Bot: Hauptmodul für das Scraping-System
"""

import logging
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import nest_asyncio

# Projektverzeichnis zum Python-Pfad hinzufügen
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Asyncio-Loop patchen für Playwright Sync API Kompatibilität
nest_asyncio.apply()

from src.config import Config
from src.sheets_io import SheetsIO
from src.bot import CompanyBot
from src.rate_limiter import RateLimitExceeded
from src.constants import TEL_KEINE, TEL_NA

def setup_logging(config: Config):
    """Logging konfigurieren mit strukturiertem Format"""
    log_config = config.get('logging', {})
    
    # Strukturiertes Log-Format
    log_format = '%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    logging.basicConfig(
        level=getattr(logging, log_config.get('level', 'INFO')),
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_config.get('file', 'bot.log'), encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # Playwright-Logs reduzieren
    logging.getLogger('playwright').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

def print_progress(current: int, total: int, start_time: datetime):
    """Gibt einen Fortschrittsbalken im Terminal aus"""
    bar_width = 20
    filled = int(bar_width * current / total)
    bar = '█' * filled + '░' * (bar_width - filled)
    pct = int(100 * current / total)

    elapsed_secs = (datetime.now() - start_time).total_seconds()
    if current > 0:
        avg_secs = elapsed_secs / current
        remaining_secs = avg_secs * (total - current)
        remaining_min = int(remaining_secs / 60)
        zeit_str = f"⏱ ~{remaining_min} min verbleibend"
    else:
        zeit_str = "⏱ wird berechnet..."

    print(f"  Fortschritt: [{bar}] {current}/{total} ({pct}%) | {zeit_str}")


def print_summary(stats: dict, start_time: datetime, retry_mode: bool):
    """Gibt die Abschluss-Zusammenfassung im Terminal aus"""
    dauer = datetime.now() - start_time
    total_secs = int(dauer.total_seconds())
    dauer_min = total_secs // 60
    dauer_sek = total_secs % 60

    titel = "RETRY ABGESCHLOSSEN" if retry_mode else "VERARBEITUNG ABGESCHLOSSEN"
    linie = "=" * 48

    print(f"\n{linie}")
    print(f"  {titel}")
    print(linie)
    print(f"  Verarbeitet:             {stats['verarbeitet']} Personen")
    print(f"  Telefonnummer gefunden:  {stats['telefon_gefunden']}")
    print(f"  Kein Ergebnis:           {stats['kein_ergebnis']}")
    print(f"  Dauer:                   {dauer_min} Min {dauer_sek} Sek")
    print(f"{linie}\n")


def main():
    """Hauptfunktion"""
    # Argument Parser setup
    parser = argparse.ArgumentParser(description='Company Lead Scraping Bot')
    parser.add_argument('--mode', type=str, help='Modus (z.B. tecis)', default=None)
    parser.add_argument('--retry', action='store_true', default=False,
                        help='Nur Zeilen verarbeiten wo Spalte Nochmal = x')
    args = parser.parse_args()

    # Logger initialisieren (wird später konfiguriert, aber wir brauchen ihn für Exception Handling)
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # Konfiguration laden (immer relativ zum Projektverzeichnis)
        config_path = project_root / "config.yaml"
        config = Config(str(config_path), mode=args.mode)
        setup_logging(config)
        
        logger.info("="*80)
        logger.info(f"Company-Bot startet im Modus: {config.mode}...")
        logger.info(f"Firma: {config.company_name}")
        if args.retry:
            logger.info("RETRY-MODUS aktiv: Verarbeite nur Zeilen mit 'x' in Spalte 'Nochmal'")
        logger.info("="*80)
        
        # Google Sheets Verbindung
        sheets_io = SheetsIO(config, retry_mode=args.retry)
        
        # Leads aus Google Sheets laden
        logger.info("Lade Leads aus Google Sheets...")
        leads = sheets_io.read_leads()
        logger.info(f"✓ {len(leads)} Lead(s) erfolgreich geladen")
        
        if not leads:
            logger.info("Keine unverarbeiteten Leads gefunden. Bot beendet.")
            return
        
        # Bot initialisieren
        bot = CompanyBot(config)
        
        # LinkedIn Rate-Limit Pre-Check
        logger.info("Prüfe LinkedIn Rate-Limit Status...")
        if not bot.rate_limiter.can_proceed('linkedin'):
            time_info = bot.rate_limiter.get_time_until_reset('linkedin')
            
            # Formatierte Ausgabe
            print("\n" + "=" * 80)
            print(f"⚠️  LINKEDIN TAGESLIMIT ERREICHT")
            print("=" * 80)
            print(f"Limit:           {time_info['limit']} Anfragen pro 24 Stunden")
            print(f"Aktuell:         {time_info['current_count']} verwendet")
            
            if time_info['reset_time']:
                reset_str = time_info['reset_time'].strftime("%d.%m.%Y %H:%M Uhr")
                window_start = time_info['reset_time'] - timedelta(hours=24)
                window_start_str = window_start.strftime("%d.%m.%Y %H:%M Uhr")
                
                print(f"Fenster Start:   {window_start_str}")
                print(f"Fenster Ende:    {reset_str}")
                print("")
                print(f"⏳ Noch {time_info['hours']} Stunden und {time_info['minutes']} Minuten bis zur Freigabe")
                print("")
                print(f"Der Bot wird jetzt beendet. Bitte starten Sie ihn nach {reset_str} erneut.")
            
            print("=" * 80 + "\n")
            
            logger.warning(f"LinkedIn Tageslimit erreicht ({time_info['current_count']}/{time_info['limit']}). Bot wird beendet.")
            sys.exit(0)
        
        logger.info("✓ LinkedIn Rate-Limit OK - Verarbeitung kann starten")
        
        # Leads verarbeiten
        start_time = datetime.now()
        stats = {'verarbeitet': 0, 'telefon_gefunden': 0, 'kein_ergebnis': 0}

        try:
            logger.info("="*80)
            logger.info("Starte Lead-Verarbeitung...")
            logger.info("="*80)
            for i, lead in enumerate(leads, 1):
                logger.info(f"[{i}/{len(leads)}] Verarbeite: {lead.vorname} {lead.nachname}")
                result = bot.process_lead(lead)
                logger.info(f"[{i}/{len(leads)}] Abgeschlossen: Tel={result.telefonnummer}, Stufe={result.stufe}")

                # Sofort in Google Sheets schreiben
                sheets_io.write_single_result(result)
                logger.info(f"[{i}/{len(leads)}] ✓ In Tabelle geschrieben")

                # Statistik aktualisieren
                stats['verarbeitet'] += 1
                hat_telefon = bool(
                    result.telefonnummer and
                    result.telefonnummer not in ('', TEL_KEINE, TEL_NA)
                )
                if hat_telefon:
                    stats['telefon_gefunden'] += 1
                else:
                    stats['kein_ergebnis'] += 1

                # Fortschrittsbalken ausgeben
                print_progress(i, len(leads), start_time)

        except RateLimitExceeded as e:
            # Lead wurde bereits geschrieben, jetzt System stoppen
            if e.platform == 'linkedin':
                logger.warning("LinkedIn Tageslimit während Verarbeitung erreicht")
                print(e.get_formatted_message())
                if stats['verarbeitet'] > 0:
                    print_summary(stats, start_time, args.retry)
                sys.exit(0)
            else:
                # Für andere Plattformen: warnen aber weitermachen
                logger.warning(f"{e.platform} Rate-Limit erreicht: {e}")
        except KeyboardInterrupt:
            logger.warning("⚠ Bot durch Benutzer abgebrochen")

        logger.info("="*80)
        logger.info("Company-Bot beendet.")

        # Abschluss-Zusammenfassung
        if stats['verarbeitet'] > 0:
            print_summary(stats, start_time, args.retry)
        
    except KeyboardInterrupt:
        logger.info("Bot durch Benutzer abgebrochen")
    except Exception as e:
        logger.error(f"Fehler im Bot: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
