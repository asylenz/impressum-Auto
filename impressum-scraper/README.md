# Impressum-Scraper

Automatisierter Bot zum Extrahieren von **Geschäftsführer-Namen** und **Telefonnummern** aus Impressum-Seiten deutscher Websites.

## Ablauf pro Firma

```
Firmenname (CSV)
      │
      ▼
1. Website finden (Google-Suche via Serper API / Playwright)
      │
      ▼
2. Impressum-URL finden (bekannte Pfade → Homepage-Links → Fallback)
      │
      ▼
3. Daten extrahieren (tel:-Links → Regex Telefon | GF-Regex)
      │
      ▼
output.csv (sofort nach jeder Firma geschrieben)
```

---

## Installation

### 1. Repository klonen / in den Ordner wechseln

```bash
cd impressum-scraper
```

### 2. Virtuelle Umgebung erstellen

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate.bat     # Windows
```

### 3. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. `.env` Datei erstellen

```bash
cp .env.example .env
```

Öffne `.env` und trage deinen Serper API Key ein:

```
SERPER_API_KEY=dein-key-von-serper.dev
```

> Kostenlosen Key holen: [serper.dev](https://serper.dev) — 2500 Suchen/Monat gratis

---

## Bot starten

### Schritt 1 — In den Ordner wechseln

```bash
cd "/Users/lorentaliu/Desktop/Website-Softwäre /Impressum scrape/impressum-scraper"
```

> Wenn du das Repo neu geklont hast:
> ```bash
> cd impressum-Auto/impressum-scraper
> ```

### Schritt 2 — Virtual Environment aktivieren

```bash
source .venv/bin/activate
```

> Bei Windows: `.venv\Scripts\activate.bat`

### Schritt 3 — (Optional) Alte Ausgabe löschen für einen Neustart

```bash
rm -f output.csv
```

> Wenn du weitermachen willst wo du aufgehört hast, diesen Schritt überspringen.

### Schritt 4 — Bot starten

```bash
python main.py
```

Der Bot läuft durch alle Firmen und schreibt live in `output.csv`.  
Mit **Ctrl+C** jederzeit stoppen — beim nächsten Start macht er automatisch weiter.

---

### Weitere Befehle

```bash
python main.py --input meine_firmenliste.csv    # andere Eingabedatei
python main.py --output ergebnisse_2024.csv     # andere Ausgabedatei
python main.py --retry                          # nur fehlgeschlagene Firmen nochmal
python main.py --input firmen.csv --retry       # Kombination
```

---

## Eingabe-Format (`firmen.csv`)

```csv
Firmenname
Mustermann GmbH
Beispiel AG
Test Software GmbH & Co. KG
```

Mindestens eine Spalte `Firmenname` ist erforderlich.

---

## Ausgabe-Format (`output.csv`)

| Firmenname | Website | Impressum-URL | Geschäftsführer | Telefonnummer | Status |
|---|---|---|---|---|---|
| Mustermann GmbH | https://www.mustermann.de | https://www.mustermann.de/impressum | Max Mustermann | +49 30 123456 | OK |
| Fehler AG | | | | | keine Website |

### Status-Codes

| Status | Bedeutung |
|---|---|
| `OK` | Mindestens GF oder Telefon gefunden |
| `kein Ergebnis` | Impressum geladen, aber keine Daten extrahiert |
| `keine Website` | Keine valide Firmen-Website gefunden |
| `kein Impressum` | Website gefunden, aber kein Impressum |
| `timeout` | Seitenaufruf hat zu lange gedauert |

---

## Konfiguration (`config.yaml`)

```yaml
browser:
  headless: true          # false = sichtbarer Browser (für Debugging)
  timeout: 10000          # Millisekunden Timeout pro Seite
  user_agent: "..."       # Browser User-Agent

discovery:
  use_serper: true        # true = Serper API, false = Playwright Google

rate_limits:
  between_requests_min: 1   # Mindestverzögerung zwischen Requests (Sekunden)
  between_requests_max: 3   # Maximalverzögerung zwischen Requests (Sekunden)
  pause_after_n_sites: 20   # Lange Pause nach N Seiten
  pause_duration: 60        # Dauer der langen Pause (Sekunden)

logging:
  level: INFO              # DEBUG, INFO, WARNING, ERROR
  file: scraper.log        # Log-Datei
```

---

## Projektstruktur

```
impressum-scraper/
├── main.py                  ← Einstiegspunkt (CLI, Fortschrittsanzeige)
├── config.yaml              ← Konfiguration
├── .env.example             ← Vorlage für API Keys
├── .env                     ← Deine Keys (nicht ins Git!)
├── requirements.txt         ← Python-Abhängigkeiten
├── firmen.csv               ← Eingabe (von dir befüllen)
├── output.csv               ← Ausgabe (wird automatisch erstellt)
├── scraper.log              ← Log-Datei (wird automatisch erstellt)
└── src/
    ├── config.py            ← YAML-Konfigurationsklasse
    ├── models.py            ← Datenmodelle (FirmenResult, SearchResult)
    ├── rate_limiter.py      ← Rate-Limiting (Pausen zwischen Requests)
    ├── utils.py             ← Hilfsfunktionen (Telefon, Normalisierung)
    ├── search.py            ← Website-Suche (Serper API + Playwright Fallback)
    ├── impressum_finder.py  ← Impressum-URL finden
    ├── impressum_parser.py  ← GF + Telefon aus HTML extrahieren
    ├── csv_io.py            ← CSV lesen/schreiben
    └── scraper.py           ← Haupt-Orchestrierung
```

---

## Technologie-Stack

| Bibliothek | Zweck |
|---|---|
| `playwright` | Browser-Automatisierung (JavaScript-Rendering) |
| `beautifulsoup4` | HTML-Parsing |
| `requests` | Schnelle HEAD-Requests (Impressum-Pfad-Prüfung) |
| `pyyaml` | YAML-Konfiguration |
| `python-dotenv` | `.env` Datei laden |

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
Bei erneutem Start werden bereits verarbeitete Firmen automatisch übersprungen.

---

## Debugging

Für sichtbaren Browser (hilfreich beim Entwickeln):

```yaml
# config.yaml
browser:
  headless: false
```

Detaillierte Logs aktivieren:

```yaml
# config.yaml
logging:
  level: DEBUG
```
