# Impressum-Scraper

**Automatisierter Bot zum Extrahieren von Geschäftsführer-Namen und Telefonnummern aus deutschen Impressum-Seiten.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/playwright-1.40+-green.svg)](https://playwright.dev/)

---

## Ablauf pro Firma

```
Firmenname (CSV)
      │
      ▼
1. Website finden
   → Google-Suche "[Firmenname] Impressum"
   → Serper API (primär) oder Playwright Google (Fallback)
   → Verzeichnisse & Social Media werden gefiltert
      │
      ▼
2. Impressum-URL finden
   → Bekannte Pfade direkt prüfen (/impressum, /impressum.html, …)
   → Homepage laden, Links mit "impressum" suchen
   → Fallback: /kontakt, /about laden
      │
      ▼
3. Daten extrahieren
   → Telefon: <a href="tel:..."> → Regex mit Kontext-Prüfung
   → Geschäftsführer: Regex (Geschäftsführer, Inhaber, CEO, Vorstand, …)
      │
      ▼
output.csv (sofort nach jeder Firma geschrieben)
```

---

## Installation

### 1. In den Projektordner wechseln

```bash
cd impressum-scraper
```

### 2. Virtuelle Umgebung erstellen

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate.bat     # Windows
```

### 3. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. `.env` Datei anlegen

```bash
cp .env.example .env
```

`.env` öffnen und den Serper API Key eintragen:

```
SERPER_API_KEY=dein-key-von-serper.dev
```

> Kostenlosen Key holen: [serper.dev](https://serper.dev) — 2500 Suchen/Monat gratis, keine Kreditkarte nötig.

---

## Verwendung

### Standard-Lauf

```bash
python main.py
```

Liest `firmen.csv`, schreibt Ergebnisse nach `output.csv`.

### Andere Eingabedatei

```bash
python main.py --input meine_firmenliste.csv
```

### Andere Ausgabedatei

```bash
python main.py --output ergebnisse_juni.csv
```

### Retry — nur fehlgeschlagene Firmen erneut verarbeiten

```bash
python main.py --retry
```

Verarbeitet nur Zeilen mit Status `kein Ergebnis` aus `output.csv` erneut.

### Kombination aller Optionen

```bash
python main.py --input firmen.csv --output output.csv --retry
```

---

## Eingabe-Format (`firmen.csv`)

```csv
Firmenname
Mustermann GmbH
Beispiel AG
Test Software GmbH & Co. KG
```

Mindestens eine Spalte `Firmenname` ist erforderlich. Weitere Spalten werden ignoriert.

---

## Ausgabe-Format (`output.csv`)

| Firmenname | Website | Impressum-URL | Geschäftsführer | Telefonnummer | Status |
|---|---|---|---|---|---|
| Mustermann GmbH | https://www.mustermann.de | https://www.mustermann.de/impressum | Max Mustermann | +49 30 123456 | OK |
| Beispiel AG | https://www.beispiel.de | https://www.beispiel.de/impressum | Anna Schmidt, Tom Müller | 089 654321 | OK |
| Fehler GmbH | | | | | keine Website |

### Status-Codes

| Status | Bedeutung |
|---|---|
| `OK` | Mindestens Geschäftsführer oder Telefonnummer gefunden |
| `kein Ergebnis` | Impressum geladen, aber keine Daten extrahierbar |
| `keine Website` | Keine valide Firmen-Website gefunden |
| `kein Impressum` | Website gefunden, Impressum nicht auffindbar |
| `timeout` | Seitenaufruf hat das Timeout überschritten |

---

## Fortschrittsanzeige

```
  Fortschritt: [████████░░░░░░░░░░░░] 40/100 (40%) | ⏱ ~12 min verbleibend

====================================================
  SCRAPING ABGESCHLOSSEN
====================================================
  Verarbeitet:              100 Firmen
  Geschäftsführer gefunden: 73
  Telefonnummer gefunden:   68
  Kein Ergebnis:            27
  Dauer:                    34 Min 12 Sek
====================================================
```

---

## Abbruch-Sicherheit

Der Bot schreibt das Ergebnis **sofort nach jeder Firma** in `output.csv`.
Bei einem Neustart werden bereits verarbeitete Firmen automatisch übersprungen — kein Datenverlust bei Abbruch.

---

## Konfiguration (`config.yaml`)

```yaml
browser:
  headless: true        # false = sichtbarer Browser (für Debugging)
  timeout: 10000        # Millisekunden Timeout pro Seite
  user_agent: "..."     # Browser User-Agent String

discovery:
  use_serper: true      # true = Serper API, false = Playwright Google

rate_limits:
  between_requests_min: 1    # Mindestverzögerung zwischen Requests (Sek.)
  between_requests_max: 3    # Maximalverzögerung zwischen Requests (Sek.)
  pause_after_n_sites: 20    # Lange Pause nach N Firmen
  pause_duration: 60         # Dauer der langen Pause (Sek.)

logging:
  level: INFO           # DEBUG, INFO, WARNING, ERROR
  file: scraper.log
```

---

## Projektstruktur

```
impressum-scraper/
├── main.py                  ← Einstiegspunkt (CLI, Fortschrittsanzeige, Zusammenfassung)
├── config.yaml              ← Alle Einstellungen
├── .env                     ← API Keys (nicht ins Git!)
├── .env.example             ← Vorlage für .env
├── requirements.txt         ← Python-Abhängigkeiten
├── firmen.csv               ← Eingabe (von dir befüllen)
├── output.csv               ← Ausgabe (wird automatisch erstellt)
├── scraper.log              ← Logs (wird automatisch erstellt)
└── src/
    ├── config.py            ← YAML-Konfigurationsklasse (Punkt-Notation)
    ├── models.py            ← Datenmodelle (FirmenResult, SearchResult)
    ├── rate_limiter.py      ← Pausen zwischen Requests + Pause nach N Seiten
    ├── utils.py             ← Hilfsfunktionen (Telefon-Extraktion, Normalisierung)
    ├── search.py            ← Website-Suche (Serper API + Playwright Fallback)
    ├── impressum_finder.py  ← Impressum-URL finden (3-stufige Strategie)
    ├── impressum_parser.py  ← Geschäftsführer + Telefon aus HTML extrahieren
    ├── csv_io.py            ← CSV lesen und schreiben
    └── scraper.py           ← Haupt-Orchestrierung + Browser-Management
```

---

## Technologie-Stack

| Bibliothek | Zweck |
|---|---|
| `playwright` | Browser-Automatisierung (JavaScript-Rendering, Navigation) |
| `beautifulsoup4` | HTML-Parsing |
| `requests` | Schnelle HEAD-Requests für Impressum-Pfad-Prüfung |
| `pyyaml` | YAML-Konfiguration lesen |
| `python-dotenv` | `.env` Datei laden |

---

## Suche ohne Serper API

Falls kein Serper API Key vorhanden ist, in `config.yaml` setzen:

```yaml
discovery:
  use_serper: false
```

Dann wird Playwright direkt für Google-Suchen verwendet. Funktioniert, ist aber langsamer und kann bei zu vielen Anfragen CAPTCHAs auslösen.

---

## Debugging

Sichtbaren Browser aktivieren (hilfreich um zu sehen was der Bot macht):

```yaml
# config.yaml
browser:
  headless: false
```

Detaillierte Debug-Logs aktivieren:

```yaml
# config.yaml
logging:
  level: DEBUG
```

Log-Datei live beobachten:

```bash
tail -f scraper.log
```
