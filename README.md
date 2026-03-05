# Impressum-Scraper

Automatisierter Bot zum Extrahieren von **Geschäftsführer-Namen** und **Telefonnummern** aus deutschen Impressum-Seiten.

Nutzt **Gemini 3 Flash** (KI) für präzise Datenextraktion und **Serper API** für die Website-Suche.

---

## Was macht der Bot?

1. Liest eine CSV-Datei mit Firmennamen ein
2. Sucht die offizielle Website jeder Firma via Google (Serper API)
3. Findet die Impressum-Seite automatisch
4. Extrahiert Geschäftsführer-Name und Telefonnummer mit **Gemini 3 Flash**
5. Schreibt alles sofort in eine `output.csv` — Semikolon-getrennt, direkt Excel- und CRM-kompatibel

> Falls die CSV bereits eine `website`-Spalte enthält, wird die Google-Suche übersprungen — spart Zeit und API-Credits.

---

## Voraussetzungen

- Python 3.10 oder neuer
- macOS / Linux / Windows
- **Serper API Key** → [serper.dev](https://serper.dev) — 2500 Suchen/Monat kostenlos
- **Gemini API Key** → [aistudio.google.com/apikey](https://aistudio.google.com/apikey) — kostenlos

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
# .venv\Scripts\activate.bat    # Windows
```

### 3. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. `.env` Datei einrichten

```bash
cp .env.example .env
```

`.env` öffnen und beide API Keys eintragen:

```env
SERPER_API_KEY=dein-key-von-serper.dev
GEMINI_API_KEY=dein-key-von-aistudio.google.com
```

| Key | Woher | Kosten |
|---|---|---|
| `SERPER_API_KEY` | [serper.dev](https://serper.dev) | 2500 Suchen/Monat gratis |
| `GEMINI_API_KEY` | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Kostenlos |

---

## Eingabe-CSV

Die Datei muss eine Spalte `Firmenname` **oder** `name` enthalten.  
Datei direkt in den `impressum-scraper/` Ordner legen als `firmen.csv`.

**Minimales Format:**
```csv
Firmenname
Firma Mustermann GmbH
Firma Beispiel AG
```

**Erweitertes Format** (mit Website — überspringt Google-Suche, schneller):
```csv
name,website
Firma Mustermann GmbH,https://www.mustermann.de
Firma Beispiel AG,
```

---

## Bot starten

> **Wichtig:** Immer nur **einen** Bot-Prozess gleichzeitig starten!

### Schritt 1 — In den Ordner wechseln

```bash
cd impressum-Auto/impressum-scraper
```

### Schritt 2 — Virtual Environment aktivieren

```bash
source .venv/bin/activate
```

> Windows: `.venv\Scripts\activate.bat`

### Schritt 3 — Alte Ausgabe löschen (nur beim Neustart nötig)

```bash
rm -f output.csv
```

> Weglassen wenn du dort weitermachen willst, wo du aufgehört hast.

### Schritt 4 — Bot starten

```bash
python main.py
```

Der Bot läuft durch alle Firmen und schreibt Ergebnisse live in `output.csv`.

---

## Pausieren & Fortsetzen

| Aktion | Was passieren |
|---|---|
| **Ctrl+C** (einmal) | Bot pausiert sofort nach der aktuellen Firma — Fortschritt gespeichert |
| **Enter** | Bot läuft weiter (nach Pause) |
| **Ctrl+C** (nochmal, während pausiert) | Bot beendet sich vollständig |
| **Bot neu starten** (`python main.py`) | Automatisch dort weitermachen wo er aufgehört hat |

**Beispiel: Heute 1000 Firmen, morgen weitermachen:**

```bash
# Bot läuft...
# [1000/3485] Verarbeite: XY GmbH
# → Ctrl+C drücken
# ⏸  PAUSIERT — Fortschritt bis hierher gespeichert.
#    → Drücke ENTER zum Fortsetzen
#    → Drücke Ctrl+C nochmal zum vollständigen Beenden

# Ctrl+C nochmal → Bot beendet sich

# Am nächsten Tag:
python main.py
# Bot startet automatisch bei Firma 1001 weiter
```

---

## Weitere Befehle

```bash
python main.py --input andere_liste.csv    # andere Eingabedatei
python main.py --output ergebnis.csv       # andere Ausgabedatei
python main.py --retry                     # nur Firmen mit "kein Ergebnis" nochmal versuchen
python main.py --start 1200               # direkt ab Zeile 1200 starten
```

### `--start N` — Manuell ab einer bestimmten Zeile starten

Falls das Terminal geschlossen wurde oder du genau weißt bei welcher Zeilennummer du warst:

```bash
python main.py --start 1200
# → Startet direkt bei Firma Nr. 1200 in der firmen.csv
# → Zeigt: "MANUELLER START ab Zeile 1200 — Erste Firma: XY GmbH"
```

Die Zeilennummer siehst du während des Laufens im Terminal:
```
[1200/3485] Verarbeite: XY GmbH
```

---

## Ausgabe (`output.csv`)

Semikolon-getrennt, alle Felder gequotet — direkt in **Excel** öffnen oder ins **CRM** importieren.

| Firmenname | Website | Impressum-URL | Geschäftsführer | Telefonnummer | Status |
|---|---|---|---|---|---|
| Firma Mustermann GmbH | https://mustermann.de | https://mustermann.de/impressum | Max Mustermann | +49 89 123456 | OK |
| Firma Beispiel AG | https://beispiel.de | https://beispiel.de/impressum | Anna Schmidt, Lars Bauer | 089 654321 | OK |
| Firma Fehler GmbH | | | | | keine Website |

### Status-Codes

| Status | Bedeutung |
|---|---|
| `OK` | Mindestens Geschäftsführer oder Telefon gefunden |
| `kein Ergebnis` | Impressum geladen, aber keine Daten extrahierbar |
| `keine Website` | Keine valide Firmen-Website gefunden |
| `kein Impressum` | Website gefunden, Impressum nicht auffindbar |
| `timeout` | Seitenaufruf hat zu lange gedauert |

---

## Abbruch-Sicherheit

Der Bot schreibt nach **jeder einzelnen Firma** sofort in `output.csv`.  
Kein Datenverlust bei Stromausfall, Absturz oder manuellem Stopp.  
Beim nächsten `python main.py` werden bereits verarbeitete Firmen automatisch übersprungen — der Bot macht genau dort weiter wo er aufgehört hat.

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
  headless: true        # false = sichtbarer Browser (nützlich zum Debuggen)
  timeout: 10000        # Millisekunden pro Seitenaufruf

discovery:
  use_serper: true      # false = Playwright Google (kein API Key nötig, langsamer)

rate_limits:
  between_requests_min: 1    # Mindestpause zwischen Requests (Sekunden)
  between_requests_max: 3    # Maximalpause zwischen Requests (Sekunden)
  pause_after_n_sites: 20    # Lange Pause nach N Firmen
  pause_duration: 60         # Dauer der langen Pause (Sekunden)

logging:
  level: INFO           # DEBUG für detaillierte Logs
  file: scraper.log     # Log-Datei
```

---

## Ohne Serper API Key

In `config.yaml` setzen:

```yaml
discovery:
  use_serper: false
```

Dann nutzt der Bot Playwright direkt für Google-Suchen — kein API Key nötig, aber langsamer und anfälliger für CAPTCHAs.

---

## Technologie-Stack

| Bibliothek | Zweck |
|---|---|
| `playwright` | Browser-Automatisierung (JavaScript-Rendering, Impressum laden) |
| `beautifulsoup4` | HTML-Parsing |
| `requests` | Schnelle HEAD-Requests (Impressum-Pfad-Prüfung) |
| `google-genai` | Gemini 3 Flash — KI-Extraktion von GF-Name und Telefon |
| `pyyaml` | YAML-Konfiguration |
| `python-dotenv` | `.env` Datei laden |

---

## Projektstruktur

```
impressum-scraper/
├── main.py                  ← Einstiegspunkt (CLI, Fortschrittsanzeige)
├── config.yaml              ← Einstellungen
├── .env                     ← API Keys (nicht ins Git!)
├── .env.example             ← Vorlage für .env
├── requirements.txt         ← Python-Abhängigkeiten
├── firmen.csv               ← Deine Eingabedatei
├── output.csv               ← Ergebnisse (wird automatisch erstellt, nicht ins Git)
├── scraper.log              ← Log-Datei (wird automatisch erstellt)
└── src/
    ├── config.py            ← YAML-Konfiguration laden
    ├── models.py            ← Datenmodelle (FirmenResult, SearchResult)
    ├── rate_limiter.py      ← Pausen zwischen Requests
    ├── utils.py             ← Hilfsfunktionen (Telefon, URL-Normalisierung)
    ├── search.py            ← Website-Suche (Serper API + Playwright Fallback)
    ├── impressum_finder.py  ← Impressum-URL automatisch finden
    ├── impressum_parser.py  ← GF + Telefon via Gemini 3 Flash extrahieren
    ├── csv_io.py            ← CSV lesen/schreiben (Semikolon, QUOTE_ALL)
    └── scraper.py           ← Haupt-Orchestrierung aller Schritte
```
