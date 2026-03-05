"""
Impressum-Scraper — Einstiegspunkt

Befehle:
    python main.py                          Standard-Lauf (firmen.csv → output.csv)
    python main.py --input meine.csv        Andere Eingabedatei
    python main.py --output ergebnis.csv    Andere Ausgabedatei
    python main.py --retry                  Nur Firmen mit Status "kein Ergebnis" erneut

Pause / Fortsetzen:
    Ctrl+C              → Bot PAUSIERT (Fortschritt wird gespeichert)
                          Danach: Enter zum Fortsetzen  |  Ctrl+C nochmal zum Beenden
    Bot neu starten     → Automatisch dort weitermachen wo er aufgehört hat
"""

import argparse
import logging
import os
import signal
import sys
import threading
from datetime import datetime
from pathlib import Path

# Projektverzeichnis zum Python-Pfad hinzufügen (damit src.* imports funktionieren)
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv()

from src.config import Config
from src.scraper import ImpressumScraper
from src.csv_io import (
    ensure_output_file,
    read_existing_results,
    read_firmen,
    read_pending_retry,
    write_result,
)


# ---------------------------------------------------------------------------
# Pause / Stop Steuerung
# ---------------------------------------------------------------------------

# _pause_flag gesetzt (set) = läuft normal; gelöscht (clear) = pausiert
_pause_flag = threading.Event()
_pause_flag.set()

_stop_flag = threading.Event()


def _install_sigint_handler() -> None:
    """
    Ctrl+C → pausiert den Bot (statt ihn sofort zu beenden).
    Während der Pause: Enter = Fortsetzen, Ctrl+C nochmal = Beenden.
    """
    def handler(signum, frame):
        if not _pause_flag.is_set():
            # Bereits pausiert → jetzt wirklich stoppen
            _stop_flag.set()
            _pause_flag.set()  # Haupt-Loop entsperren
            print("\n\n🛑  Bot wird beendet — Fortschritt wurde gespeichert.\n")
        else:
            # Läuft → pausieren
            _pause_flag.clear()
            print(
                "\n\n⏸  PAUSIERT — Fortschritt bis hierher gespeichert.\n"
                "   → Drücke ENTER zum Fortsetzen\n"
                "   → Drücke Ctrl+C nochmal zum vollständigen Beenden\n"
            )
            # Hintergrund-Thread wartet auf Enter-Taste
            def _wait_for_enter():
                try:
                    input()
                    if not _stop_flag.is_set() and not _pause_flag.is_set():
                        _pause_flag.set()
                        print("▶  FORTGESETZT\n")
                except Exception:
                    pass

            t = threading.Thread(target=_wait_for_enter, daemon=True)
            t.start()

    signal.signal(signal.SIGINT, handler)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(config: Config) -> None:
    log_cfg = config.get("logging", {}) or {}
    log_level = getattr(logging, log_cfg.get("level", "INFO"), logging.INFO)
    log_format = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"

    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(
                log_cfg.get("file", "scraper.log"), encoding="utf-8"
            ),
            logging.StreamHandler(sys.stdout),
        ],
    )
    # Externe Bibliotheken auf WARNING reduzieren
    for noisy in ("playwright", "urllib3", "asyncio", "requests"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# UI-Ausgaben
# ---------------------------------------------------------------------------

def print_progress(current: int, total: int, start_time: datetime) -> None:
    """Gibt einen Fortschrittsbalken im Terminal aus."""
    bar_width = 20
    filled = int(bar_width * current / total) if total else 0
    bar = "█" * filled + "░" * (bar_width - filled)
    pct = int(100 * current / total) if total else 0

    elapsed = (datetime.now() - start_time).total_seconds()
    if current > 0:
        remaining_min = int((elapsed / current) * (total - current) / 60)
        zeit_str = f"⏱ ~{remaining_min} min verbleibend"
    else:
        zeit_str = "⏱ wird berechnet..."

    print(f"  Fortschritt: [{bar}] {current}/{total} ({pct}%) | {zeit_str}")


def print_summary(stats: dict, start_time: datetime, retry_mode: bool) -> None:
    """Gibt die Abschluss-Zusammenfassung aus."""
    dauer = datetime.now() - start_time
    secs = int(dauer.total_seconds())
    titel = "SCRAPING ABGESCHLOSSEN (RETRY)" if retry_mode else "SCRAPING ABGESCHLOSSEN"
    linie = "=" * 52

    print(f"\n{linie}")
    print(f"  {titel}")
    print(linie)
    print(f"  Verarbeitet:              {stats['verarbeitet']} Firmen")
    print(f"  Geschäftsführer gefunden: {stats['gf_gefunden']}")
    print(f"  Telefonnummer gefunden:   {stats['tel_gefunden']}")
    print(f"  Kein Ergebnis:            {stats['kein_ergebnis']}")
    print(f"  Dauer:                    {secs // 60} Min {secs % 60} Sek")
    print(f"{linie}\n")


# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Impressum-Scraper: Geschäftsführer & Telefonnummer aus Impressum-Seiten"
    )
    parser.add_argument(
        "--input", default="firmen.csv", help="Eingabe-CSV (Standard: firmen.csv)"
    )
    parser.add_argument(
        "--output", default="output.csv", help="Ausgabe-CSV (Standard: output.csv)"
    )
    parser.add_argument(
        "--retry",
        action="store_true",
        help="Nur Firmen mit Status 'kein Ergebnis' erneut verarbeiten",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=None,
        metavar="N",
        help="Ab Zeile N in der Eingabeliste starten (1-basiert, z.B. --start 1200)",
    )
    args = parser.parse_args()

    # Konfiguration laden
    config_path = project_root / "config.yaml"
    config = Config(str(config_path))
    setup_logging(config)
    logger = logging.getLogger(__name__)

    _install_sigint_handler()

    logger.info("=" * 60)
    logger.info("Impressum-Scraper startet...")
    logger.info(f"  Eingabe:  {args.input}")
    logger.info(f"  Ausgabe:  {args.output}")
    logger.info(f"  Retry:    {args.retry}")
    logger.info(f"  PID:      {os.getpid()}")
    logger.info("=" * 60)
    print("  Steuerung: Ctrl+C = Pausieren | Enter = Fortsetzen | Ctrl+C (2x) = Beenden\n")

    # Firmenliste laden
    try:
        all_firmen = read_firmen(args.input)
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Fehler beim Lesen der Eingabedatei: {e}")
        sys.exit(1)

    # Bereits verarbeitete Firmen prüfen (Fortsetzung nach Abbruch)
    existing = read_existing_results(args.output)

    # Zu verarbeitende Firmen ermitteln
    if args.retry:
        firmen_todo = read_pending_retry(args.output)
        logger.info(f"RETRY-MODUS: {len(firmen_todo)} Firmen werden erneut verarbeitet")
    else:
        # --start N: ab Zeile N in der Originalliste starten (überschreibt output.csv-Prüfung)
        if args.start is not None:
            start_idx = max(1, args.start) - 1          # 1-basiert → 0-basiert
            start_idx = min(start_idx, len(all_firmen)) # Nicht über die Liste hinaus
            firmen_todo = all_firmen[start_idx:]
            startname = firmen_todo[0]["firmenname"] if firmen_todo else "—"
            print(
                f"\n▶  MANUELLER START ab Zeile {args.start} von {len(all_firmen)}\n"
                f"   Erste Firma: {startname}\n"
            )
            logger.info(f"Manueller Start ab Zeile {args.start}: '{startname}'")
        else:
            firmen_todo = [f for f in all_firmen if f["firmenname"] not in existing]
            skipped = len(all_firmen) - len(firmen_todo)
            if skipped:
                naechste = firmen_todo[0]["firmenname"] if firmen_todo else "—"
                print(
                    f"\n▶  FORTSETZUNG — {skipped} von {len(all_firmen)} Firmen bereits verarbeitet.\n"
                    f"   Weiter bei: {naechste}\n"
                )
                logger.info(
                    f"Fortsetzung: {skipped} bereits verarbeitet, starte bei '{naechste}'"
                )

    if not firmen_todo:
        print("\n✅  Alle Firmen wurden bereits verarbeitet. Nichts zu tun.\n")
        logger.info("Alle Firmen bereits verarbeitet — Bot beendet.")
        return

    logger.info(f"{len(firmen_todo)} Firmen werden verarbeitet...")

    # Output-Datei vorbereiten (Header schreiben falls neu)
    if not args.retry:
        ensure_output_file(args.output)

    # Scraping
    start_time = datetime.now()
    stats = {
        "verarbeitet": 0,
        "gf_gefunden": 0,
        "tel_gefunden": 0,
        "kein_ergebnis": 0,
    }
    total = len(firmen_todo)
    # Offset für die Anzeige: bei --start X beginnt die Anzeige bei X, sonst bei 1
    display_offset = (args.start - 1) if (args.start is not None) else 0

    with ImpressumScraper(config) as scraper:
        for i, eintrag in enumerate(firmen_todo, 1):
            display_i = display_offset + i
            # Pause-Punkt: wartet hier bis Benutzer Enter drückt (oder direkt weiter)
            _pause_flag.wait()

            if _stop_flag.is_set():
                logger.warning("Bot durch Benutzer gestoppt — Fortschritt gespeichert")
                break

            firmenname = eintrag["firmenname"]
            logger.info(f"[{display_i}/{len(all_firmen)}] Verarbeite: {firmenname}")

            result = scraper.scrape(
                firmenname,
                website_hint=eintrag.get("website", ""),
            )

            # Sofort in CSV schreiben (Abbruch-sicher)
            write_result(args.output, result, retry_mode=args.retry)

            logger.info(
                f"[{display_i}/{len(all_firmen)}] Fertig — Status: {result.status} | "
                f"GF: {(result.geschaeftsfuehrer[:40] + '…') if len(result.geschaeftsfuehrer) > 40 else result.geschaeftsfuehrer or '-'} | "
                f"Tel: {result.telefonnummer or '-'}"
            )

            # Statistik
            stats["verarbeitet"] += 1
            if result.geschaeftsfuehrer:
                stats["gf_gefunden"] += 1
            if result.telefonnummer:
                stats["tel_gefunden"] += 1
            if not result.geschaeftsfuehrer and not result.telefonnummer:
                stats["kein_ergebnis"] += 1

            print_progress(display_i, len(all_firmen), start_time)

    logger.info("=" * 60)
    logger.info("Impressum-Scraper beendet.")
    print_summary(stats, start_time, args.retry)


if __name__ == "__main__":
    main()
