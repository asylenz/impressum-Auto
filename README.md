# Impressum-Scraper

Automatisierter Bot zum Extrahieren von **Geschäftsführer-Namen** und **Telefonnummern** aus deutschen Impressum-Seiten.

---

## Was macht der Bot?

1. Liest eine CSV-Datei mit Firmennamen ein
2. Sucht die offizielle Website jeder Firma via Google (Serper API)
3. Findet die Impressum-Seite automatisch
4. Extrahiert Geschäftsführer-Name und Telefonnummer
5. Schreibt alles sofort in eine `output.csv`

Falls die CSV bereits eine `website`-Spalte enthält, wird die Google-Suche übersprungen — das spart Zeit und API-Credits.

---

## Voraussetzungen

- Python 3.10 oder neuer
- macOS / Linux / Windows
- Serper API Key (kostenlos auf [serper.dev](https://serper.dev) — 2500 Suchen/Monat gratis)

---

## Installation

### 1. Repository klonen

```bash
git clone https://github.com/asylenz/impressum-Auto.git
cd impressum-Auto/impressum-scraper
```

### 2. Virtuelle Umgebung erstellen und aktivieren

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

### 4. API Key einrichten

```bash
cp .env.example .env
```

`.env` öffnen und den Serper Key eintragen:

```
SERPER_API_KEY=dein-key-von-serper.dev
```

---

## Eingabe-CSV vorbereiten

Die CSV-Datei muss entweder eine Spalte `Firmenname` **oder** `name` enthalten.
Optional: eine Spalte `website` — dann wird die Google-Suche übersprungen.

**Minimales Format:**
```csv
Firmenname
Mustermann GmbH
Beispiel AG
```

**Erweitertes Format (mit Website — schneller):**
```csv
Firmenname,website
Mustermann GmbH,https://www.mustermann.de
Beispiel AG,
```

Die Datei kommt direkt in den `impressum-scraper/` Ordner.

---

## Bot starten

```bash
python main.py
```

### Weitere Befehle

```bash
python main.py --input meine_firmen.csv     # andere Eingabedatei
python main.py --output ergebnis.csv        # andere Ausgabedatei
python main.py --retry                      # nur fehlgeschlagene Firmen nochmal
```

---

## Ausgabe (`output.csv`)

| Firmenname | Website | Impressum-URL | Geschäftsführer | Telefonnummer | Status |
|---|---|---|---|---|---|
| Mustermann GmbH | https://www.mustermann.de | https://www.mustermann.de/impressum | Max Mustermann | +49 30 123456 | OK |
| Beispiel AG | https://www.beispiel.de | https://www.beispiel.de/impressum | Anna Schmidt | 089 654321 | OK |
| Fehler GmbH | | | | | keine Website |

### Status-Codes

| Status | Bedeutung |
|---|---|
| `OK` | Mindestens Geschäftsführer oder Telefon gefunden |
| `kein Ergebnis` | Impressum geladen, aber keine Daten gefunden |
| `keine Website` | Keine valide Firmen-Website gefunden |
| `kein Impressum` | Website gefunden, Impressum nicht auffindbar |
| `timeout` | Seitenaufruf hat zu lange gedauert |

---

## Abbruch und Fortsetzen

Der Bot schreibt das Ergebnis **sofort nach jeder Firma** in `output.csv`.
Bei `Ctrl+C` stoppt er sauber. Beim nächsten Start werden bereits verarbeitete Firmen automatisch übersprungen.

---

## Fortschrittsanzeige

```
  Fortschritt: [████████░░░░░░░░░░░░] 800/3485 (23%) | ⏱ ~47 min verbleibend

====================================================
  SCRAPING ABGESCHLOSSEN
====================================================
  Verarbeitet:              3485 Firmen
  Geschäftsführer gefunden: 2100
  Telefonnummer gefunden:   1950
  Kein Ergebnis:            435
  Dauer:                    3 Std 12 Min
====================================================
```

---

## Konfiguration (`config.yaml`)

```yaml
browser:
  headless: true        # false = sichtbarer Browser zum Debuggen
  timeout: 10000        # Millisekunden pro Seitenaufruf

discovery:
  use_serper: true      # false = Playwright Google (kein API Key nötig, langsamer)

rate_limits:
  between_requests_min: 1    # Mindestpause zwischen Requests (Sekunden)
  between_requests_max: 3    # Maximalpause zwischen Requests (Sekunden)
  pause_after_n_sites: 20    # Lange Pause nach N Firmen
  pause_duration: 60         # Dauer der langen Pause (Sekunden)
```

---

## Ohne Serper API Key

In `config.yaml` setzen:

```yaml
discovery:
  use_serper: false
```

Dann wird Playwright direkt für Google-Suchen verwendet — kein API Key nötig, aber etwas langsamer und anfälliger für CAPTCHAs.

---

## Projektstruktur

```
impressum-scraper/
├── main.py                  ← Einstiegspunkt
├── config.yaml              ← Einstellungen
├── .env                     ← API Keys (nicht ins Git!)
├── .env.example             ← Vorlage für .env
├── requirements.txt         ← Abhängigkeiten
├── firmen.csv               ← Deine Eingabedatei
├── output.csv               ← Ergebnisse (wird automatisch erstellt)
└── src/
    ├── config.py            ← YAML-Konfiguration
    ├── models.py            ← Datenmodelle
    ├── rate_limiter.py      ← Pausen zwischen Requests
    ├── utils.py             ← Hilfsfunktionen
    ├── search.py            ← Website-Suche (Serper + Playwright)
    ├── impressum_finder.py  ← Impressum-URL finden
    ├── impressum_parser.py  ← Daten aus Impressum extrahieren
    ├── csv_io.py            ← CSV lesen/schreiben
    └── scraper.py           ← Haupt-Orchestrierung
```
