# 🚀 Onboarding Guide – Tecis-Bot Setup

Willkommen! Diese Anleitung führt dich Schritt für Schritt durch das komplette Setup des Tecis-Bots.

**Geschätzte Zeit:** 30-45 Minuten (beim ersten Mal)

---

## 📋 Voraussetzungen-Check

Bevor du startest, stelle sicher, dass du folgendes hast:

- [ ] **Computer:** macOS, Linux oder Windows
- [ ] **Python:** Version 3.10 oder höher installiert
- [ ] **Google-Account:** Mit Zugriff auf Google Sheets
- [ ] **LinkedIn-Account:** Gültiges Login (Free, Premium oder Sales Navigator)
- [ ] **Internet:** Stabile Verbindung (für Downloads und API-Zugriffe)
- [ ] **Terminal-Kenntnisse:** Basis-Kenntnisse in der Kommandozeile

**Python-Version prüfen:**
```bash
python3 --version
# Sollte ausgeben: Python 3.10.x oder höher
```

---

## 🏗️ Schritt 1: Projekt-Setup

### 1.1 Projektverzeichnis öffnen

```bash
cd "/Users/mehmetalikarayusuf/Desktop/Asylenz/Nyka/BK Automatisierung"
```

### 1.2 Virtual Environment erstellen

```bash
# Virtual Environment erstellen
python3 -m venv venv

# Aktivieren (macOS/Linux)
source venv/bin/activate

# Aktivieren (Windows)
# venv\Scripts\activate
```

**✅ Erfolgreich, wenn:** Dein Terminal-Prompt jetzt mit `(venv)` beginnt.

### 1.3 Dependencies installieren

```bash
# Python-Pakete installieren
pip install -r requirements.txt

# Playwright Browser installieren
playwright install chromium
```

**⏱️ Dauer:** 3-5 Minuten (je nach Internetverbindung)

**✅ Erfolgreich, wenn:** Keine roten Fehlermeldungen erscheinen.

---

## ☁️ Schritt 2: Google Cloud Console Setup

Das ist der **wichtigste und komplexeste** Teil des Setups. Nimm dir Zeit dafür!

### 2.1 Google Cloud Console öffnen

1. Öffne im Browser: **https://console.cloud.google.com/**
2. Melde dich mit deinem **Google-Account** an (derselbe, mit dem du auch Google Sheets nutzt)

### 2.2 Neues Projekt erstellen

1. **Oben links** auf den Projekt-Dropdown klicken (steht dort etwas wie "Projekt auswählen")
2. Im Popup-Fenster **"Neues Projekt"** klicken
3. Projekt-Details eingeben:
   - **Projektname:** `Tecis Bot` (oder ein anderer Name deiner Wahl)
   - **Organisation:** "Keine Organisation" (Standard)
4. **"Erstellen"** klicken
5. **Warten**, bis die Benachrichtigung "Projekt wurde erstellt" erscheint (dauert 10-30 Sekunden)
6. **Wichtig:** Oben links prüfen, ob jetzt "Tecis Bot" als aktives Projekt angezeigt wird
   - Falls nicht: Auf Projekt-Dropdown klicken → "Tecis Bot" auswählen

**✅ Checkpoint:** Das aktive Projekt oben links sollte jetzt "Tecis Bot" sein.

---

### 2.3 Google Sheets API aktivieren

1. In der **linken Seitenleiste** auf **"APIs und Dienste"** klicken
2. Dann auf **"Bibliothek"** klicken
3. In der **Suchleiste oben** eingeben: `Google Sheets API`
4. In den Suchergebnissen auf **"Google Sheets API"** klicken (von Google Inc.)
5. Auf den blauen Button **"Aktivieren"** klicken
6. **Warten**, bis die API-Übersichtsseite lädt

**✅ Checkpoint:** Du siehst jetzt "Google Sheets API" mit Status "Aktiviert" und Nutzungsstatistiken.

---

### 2.4 OAuth-Zustimmungsbildschirm konfigurieren

Bevor du Credentials erstellen kannst, musst du den Zustimmungsbildschirm einrichten.

1. In der **linken Seitenleiste:** "APIs und Dienste" → **"OAuth-Zustimmungsbildschirm"**
2. **Nutzertyp auswählen:**
   - Wähle **"Extern"** (damit du dich selbst als Testnutzer hinzufügen kannst)
   - Klicke **"Erstellen"**

#### Seite 1: App-Informationen

Fülle folgende Felder aus:

| Feld | Was eintragen |
|------|---------------|
| **App-Name** | `Tecis Bot` |
| **Benutzer-Support-E-Mail** | Deine E-Mail-Adresse auswählen |
| **App-Logo** | Leer lassen (optional) |
| **App-Domänen** | Leer lassen |
| **Autorisierte Domänen** | Leer lassen |
| **Entwickler-Kontaktinformationen** | Deine E-Mail-Adresse |

Klicke **"Speichern und fortfahren"**

#### Seite 2: Bereiche (Scopes)

- **Nichts** auswählen
- Einfach **"Speichern und fortfahren"** klicken

*(Der Bot fügt den benötigten Scope später automatisch hinzu)*

#### Seite 3: Testnutzer ⚠️ WICHTIG!

**Das ist ein kritischer Schritt!** Ohne Testnutzer wird der Bot blockiert.

1. Klicke **"+ Testnutzer hinzufügen"**
2. Gib **deine Google-E-Mail-Adresse** ein (die, mit der du Google Sheets nutzt)
3. Klicke **"Hinzufügen"**
4. Deine E-Mail sollte jetzt in der Liste erscheinen
5. Klicke **"Speichern und fortfahren"**

#### Seite 4: Zusammenfassung

- Prüfe, ob alles korrekt ist
- Klicke **"Zurück zum Dashboard"**

**✅ Checkpoint:** Auf dem Dashboard sollte stehen:
- Veröffentlichungsstatus: **"Testen"**
- Testnutzer: **1** (deine E-Mail)

---

### 2.5 OAuth-Credentials erstellen

Jetzt erstellen wir den "Ausweis" für den Bot.

1. In der **linken Seitenleiste:** "APIs und Dienste" → **"Anmeldedaten"**
2. Oben auf **"+ Anmeldedaten erstellen"** klicken
3. Im Dropdown **"OAuth-Client-ID"** auswählen
4. **Anwendungstyp:** Wähle **"Desktopanwendung"**
5. **Name:** `Tecis Bot Desktop` (oder ein anderer Name)
6. Klicke **"Erstellen"**
7. Ein Popup erscheint mit "OAuth-Client wurde erstellt"
   - Du kannst es mit **"OK"** schließen

#### Credentials herunterladen

1. Du bist jetzt auf der Seite "Anmeldedaten"
2. Unter **"OAuth 2.0-Client-IDs"** findest du deinen Eintrag "Tecis Bot Desktop"
3. **Ganz rechts** bei diesem Eintrag auf das **Download-Symbol** (↓) klicken
   - Oder: Auf die **3 Punkte** (⋮) → "JSON herunterladen"
4. Die Datei wird heruntergeladen (z.B. `client_secret_123456789.json`)

#### Datei ins Projekt verschieben

1. **Finde** die heruntergeladene JSON-Datei (meist im Downloads-Ordner)
2. **Benenne** sie um in: **`credentials.json`** (genau so, Groß-/Kleinschreibung beachten!)
3. **Verschiebe** sie in dein Projektverzeichnis:
   ```
   /Users/mehmetalikarayusuf/Desktop/Asylenz/Nyka/BK Automatisierung/credentials.json
   ```

**Verifizieren:**
```bash
# Im Projektverzeichnis ausführen
ls -la credentials.json
# Sollte die Datei anzeigen, z.B.:
# -rw-r--r--  1 user  staff  427 Feb 11 00:30 credentials.json
```

**✅ Checkpoint:** Die Datei `credentials.json` liegt im Projektverzeichnis (neben `main.py`).

---

### 2.6 Google Cloud Setup abschließen

Das war's mit Google Cloud! Du musst die Console jetzt nicht mehr nutzen (außer du willst etwas ändern).

**Zusammenfassung was du gemacht hast:**
- ✅ Projekt erstellt
- ✅ Google Sheets API aktiviert
- ✅ OAuth-Zustimmungsbildschirm konfiguriert
- ✅ Dich als Testnutzer hinzugefügt
- ✅ OAuth-Credentials erstellt und heruntergeladen
- ✅ `credentials.json` ins Projekt verschoben

---

## 📊 Schritt 3: Google Sheet vorbereiten

### 3.1 Test-Sheet erstellen

1. Öffne **https://sheets.google.com/**
2. Erstelle eine **neue Tabelle**: "Tecis Bot Test"

### 3.2 Header-Zeile (Zeile 1)

Kopiere folgende Spaltenüberschriften in die **erste Zeile**:

| A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|
| Full Name | Company | Telefonnummer | Zweite Telefonnummer | Stufe | Zielgruppe |

**Wichtig:**
- Die Spaltenüberschriften müssen **exakt** so heißen
- `Full Name` (nicht "Vorname" + "Nachname")
- `Company` (nicht "Unternehmen")

### 3.3 Test-Daten (Zeile 2+)

Füge ein paar Test-Zeilen ein:

| Full Name | Company | Telefonnummer | Zweite Telefonnummer | Stufe | Zielgruppe |
|-----------|---------|---------------|---------------------|-------|-----------|
| Max Mustermann | tecis Finanzdienstleistungen AG | | | | |
| Anna Schmidt | tecis Finanzdienstleistungen AG | | | | |

**Hinweis:** Die Spalten C-F bleiben leer – der Bot füllt sie aus!

### 3.4 Sheet-ID kopieren

1. Öffne dein Google Sheet
2. Schau in die **Adresszeile** des Browsers
3. Die URL sieht so aus:
   ```
   https://docs.google.com/spreadsheets/d/1a2B3c4D5e6F7g8H9i0J1k2L3m4N5o6P7q8R9s0T/edit#gid=0
                                          └─────────────────────┬─────────────────────┘
                                                           DAS IST DIE SHEET-ID
   ```
4. **Kopiere** nur den Teil zwischen `/d/` und `/edit`

**Beispiel:**
- URL: `https://docs.google.com/spreadsheets/d/1a2B3c4D5e6F7g8H9i0J1k2L3m4N5o6P7q8R9s0T/edit`
- Sheet-ID: `1a2B3c4D5e6F7g8H9i0J1k2L3m4N5o6P7q8R9s0T`

**✅ Checkpoint:** Du hast die Sheet-ID kopiert (eine lange Zeichenfolge).

---

## 🔐 Schritt 4: Umgebungsvariablen konfigurieren

### 4.1 `.env` Datei erstellen

```bash
# Im Projektverzeichnis ausführen
cp .env.example .env
```

### 4.2 `.env` mit Editor öffnen

```bash
# Mit einem Texteditor öffnen (z.B. nano, vim, oder VSCode)
nano .env
# oder
code .env
```

### 4.3 Werte ausfüllen

Fülle die `.env` Datei mit deinen echten Daten:

```env
# LinkedIn Credentials
LINKEDIN_EMAIL=deine-echte-email@example.com
LINKEDIN_PASSWORD=dein-linkedin-passwort

# Google Sheets
SHEET_ID=1a2B3c4D5e6F7g8H9i0J1k2L3m4N5o6P7q8R9s0T

# Serper API (Optional - siehe unten)
SERPER_API_KEY=dein-api-key-hier

# Limits (Optional - nur wenn du Defaults überschreiben willst)
# LINKEDIN_MAX_PROFILES_PER_DAY=50
# LINKEDIN_MAX_PROFILES_PER_HOUR=25
```

**Was du eintragen musst:**

| Variable | Wo bekommst du den Wert? | Beispiel |
|----------|--------------------------|----------|
| `LINKEDIN_EMAIL` | Deine LinkedIn-Login-E-Mail | `max@example.com` |
| `LINKEDIN_PASSWORD` | Dein LinkedIn-Passwort | `MeinSicheres!Passwort123` |
| `SHEET_ID` | Aus der Google Sheets URL (siehe oben) | `1a2B3c...` |
| `SERPER_API_KEY` | Optional: https://serper.dev (2.500 Suchen/Monat gratis) | `abc123...` |

**Speichern:**
- **nano:** `Ctrl+O` (speichern), `Enter`, `Ctrl+X` (beenden)
- **VSCode:** `Cmd+S` (macOS) oder `Ctrl+S` (Windows/Linux)

**✅ Checkpoint:** Die `.env` Datei existiert und enthält deine echten Credentials.

---

### 4.4 Serper API einrichten (Optional, aber empfohlen)

**Warum Serper?**
- Der Bot nutzt Google-Suche, um URLs zu finden
- **Ohne Serper:** Playwright öffnet Google im Browser (langsam, anfällig für Captchas)
- **Mit Serper:** API-Zugriff (schnell, zuverlässig, 2.500 Suchen/Monat gratis)

**Setup (5 Minuten):**

1. Gehe zu **https://serper.dev**
2. Klicke **"Sign Up"** (kostenlos)
3. Registriere dich mit Google oder E-Mail
4. Nach Login: Dashboard → **"API Key"** anzeigen
5. **Kopiere** den API-Key
6. Füge ihn in `.env` ein:
   ```env
   SERPER_API_KEY=dein-kopierter-key
   ```

**Aktivieren in der Config:**

```bash
# Öffne config.yaml
nano config.yaml  # oder code config.yaml
```

Stelle sicher, dass folgende Zeile auf `true` steht:

```yaml
discovery:
  use_serper: true  # true = Serper API | false = Playwright
```

**✅ Checkpoint:** Serper API Key ist in `.env` und `use_serper: true` in `config.yaml`.

---

## ⚙️ Schritt 5: LinkedIn-Limits anpassen

Die Limits in `config.yaml` sind für **Free Accounts** voreingestellt. Passe sie an deinen Account-Typ an!

### 5.1 LinkedIn Account-Typ prüfen

1. Gehe zu **https://www.linkedin.com/settings/**
2. Links: **"Konto"** → **"Abonnement-Typ"**
3. Notiere dir, welchen Typ du hast:
   - **Free** (Kostenlos)
   - **Premium Career** / **Premium Business**
   - **Sales Navigator**

### 5.2 Limits in `config.yaml` anpassen

```bash
# Öffne config.yaml
nano config.yaml  # oder code config.yaml
```

Passe die Limits gemäß deinem Account-Typ an:

```yaml
limits:
  linkedin:
    # Account-Typ:        Free  | Premium | Sales Nav
    max_profiles_per_day: 50    # 80      | 150     | 250
    max_profiles_per_hour: 13   # 20      | 30      | 50
    delay_between_requests_min: 0
    delay_between_requests_max: 0
    pause_after_n_profiles: 20
    pause_duration: 300  # 5 Minuten
```

**Empfehlung für den Anfang:**
- Starte **konservativ** (z.B. 30 Profile/Tag für Free)
- Beobachte 1-2 Wochen
- Erhöhe schrittweise, wenn stabil

**✅ Checkpoint:** Limits in `config.yaml` passen zu deinem LinkedIn Account-Typ.

---

## 🧪 Schritt 6: Erster Test-Lauf

Jetzt ist alles vorbereitet! Zeit für den ersten Test.

### 6.1 Debug-Modus aktivieren (empfohlen für ersten Test)

```bash
# Öffne config.yaml
nano config.yaml
```

Setze:

```yaml
browser:
  headless: false  # Sichtbarer Browser für ersten Test
```

**Warum?** Du siehst was der Bot macht (hilfreich bei Problemen).

### 6.2 Bot starten

```bash
# Virtual Environment sollte aktiv sein (Terminal zeigt "(venv)")

# Standard-Modus (Tecis)
python main.py

# Oder spezifischer Modus (z.B. Swiss Life Select oder TauRes)
python main.py --mode swiss_life_select
python main.py --mode taures
```

### 6.3 Was jetzt passiert

#### 1. Google OAuth (nur beim ersten Mal)

Ein **Browser-Fenster öffnet sich** automatisch:

1. **Google-Account auswählen** (derselbe wie bei Google Cloud)
2. Meldung: "Tecis Bot möchte auf dein Google-Konto zugreifen"
3. Klicke **"Weiter"** oder **"Zulassen"**
4. Evtl. Warnung: "Diese App wurde nicht von Google bestätigt"
   - Klicke **"Erweitert"** → **"Zu Tecis Bot wechseln (unsicher)"**
   - Das ist OK, weil du dich als Testnutzer eingetragen hast!
5. Bestätige die Berechtigungen
6. Browser zeigt: "Die Authentifizierung war erfolgreich"
7. **Schließe** das Browser-Fenster

**Wichtig:** Diese Autorisierung musst du nur **einmal** machen. Der Bot speichert die Berechtigung in `token.json`.

#### 2. LinkedIn Login (nur beim ersten Mal)

Der Bot öffnet LinkedIn und versucht sich einzuloggen:

- **Automatischer Login:** Bot gibt deine Credentials ein
- **2FA aktiviert?** 
  - Der Browser bleibt offen
  - Gib den 2FA-Code **manuell** ein
  - Bot wartet und fährt dann fort
- **Session wird gespeichert:** Beim nächsten Start kein erneuter Login nötig

#### 3. Lead-Verarbeitung

Der Bot:
1. Lädt Leads aus Google Sheets
2. Findet URLs über Serper/Google
3. Besucht Tecis.de, LinkedIn, Xing, Creditreform
4. Extrahiert Telefonnummern und Stufen
5. Schreibt Ergebnisse zurück in Google Sheets

**Console-Output Beispiel:**

```
================================================================================
Tecis-Bot startet...
================================================================================
✓ 2 Lead(s) erfolgreich geladen
Prüfe LinkedIn Rate-Limit Status...
✓ LinkedIn Rate-Limit OK - Verarbeitung kann starten
================================================================================
[1/2] Verarbeite: Max Mustermann
--- Link-Discovery ---
  ✓ Tecis URL gefunden
  ✓ LinkedIn URL gefunden
--- Phase 1: Tecis ---
  ✓ Stufe gefunden: Senior Sales Manager
  ✓ Telefonnummer gefunden: +49 123 456789
[1/2] ✓ In Tabelle geschrieben
[2/2] Verarbeite: Anna Schmidt
...
```

#### 4. Ergebnisse prüfen

1. Öffne dein **Google Sheet**
2. Prüfe die **Ausgabe-Spalten** (D, E, F, G):
   - Telefonnummer gefüllt?
   - Stufe gefüllt?
   - Zielgruppe gefüllt?

**✅ Erfolg, wenn:** Mindestens eine Zeile wurde mit Daten gefüllt!

---

## 🐛 Häufige Setup-Probleme

### Problem: "credentials.json nicht gefunden"

**Ursache:** Datei liegt nicht im richtigen Verzeichnis oder hat falschen Namen.

**Lösung:**
```bash
# Prüfe, ob Datei existiert
ls -la credentials.json

# Sollte ausgeben:
# -rw-r--r--  1 user  staff  427 Feb 11 00:30 credentials.json

# Falls nicht: Nochmal von Google Cloud herunterladen und ins Projekt legen
```

---

### Problem: "LINKEDIN_EMAIL not set"

**Ursache:** `.env` Datei nicht erstellt oder fehlerhaft.

**Lösung:**
```bash
# Prüfe, ob .env existiert
cat .env

# Stelle sicher, dass die Zeilen so aussehen:
# LINKEDIN_EMAIL=max@example.com
# (keine Leerzeichen um das "=", keine Anführungszeichen)
```

---

### Problem: "Invalid grant" bei Google OAuth

**Ursache:** Dein Google-Account ist nicht als Testnutzer eingetragen.

**Lösung:**
1. Google Cloud Console → OAuth-Zustimmungsbildschirm
2. Testnutzer → Prüfe, ob deine E-Mail da steht
3. Falls nicht: **"+ Testnutzer hinzufügen"** → Deine E-Mail eintragen
4. `token.json` löschen und Bot neu starten:
   ```bash
   rm token.json
   python main.py
   ```

---

### Problem: LinkedIn-Login schlägt fehl / Captcha

**Ursache:** LinkedIn erkennt Bot-Verhalten oder verlangt 2FA.

**Lösung 1 – 2FA:**
```yaml
# config.yaml
browser:
  headless: false  # Sichtbarer Browser
```
→ Bot startet Browser, du gibst 2FA-Code manuell ein

**Lösung 2 – Captcha:**
1. Browser bleibt offen (headless: false)
2. Löse Captcha manuell
3. Bot wartet und fährt dann fort

**Lösung 3 – Session manuell erstellen:**
```bash
# Browser-Daten löschen und neu starten
rm -rf browser_data/linkedin/
python main.py
```

---

### Problem: "Sheet-ID not found"

**Ursache:** Falsche Sheet-ID oder Bot hat keinen Zugriff.

**Lösung:**
1. **Sheet-ID nochmal prüfen:**
   - URL: `https://docs.google.com/spreadsheets/d/ABC123XYZ/edit`
   - Sheet-ID: `ABC123XYZ` (nur der Teil zwischen `/d/` und `/edit`)
2. **Zugriff prüfen:**
   - Öffne Sheet im Browser mit demselben Google-Account
   - Sheet muss von dir erstellt sein ODER du musst Zugriff haben
3. **`.env` prüfen:**
   ```bash
   cat .env | grep SHEET_ID
   # Sollte ausgeben: SHEET_ID=ABC123XYZ
   ```

---

### Problem: Google-Suche findet keine URLs

**Ursache 1:** Test-Leads mit erfundenen Namen.

**Lösung:** Nutze echte Tecis-Berater-Namen für Tests (z.B. aus tecis.de Website).

**Ursache 2:** Serper API nicht konfiguriert und Playwright wird von Google blockiert.

**Lösung:** Serper API einrichten (siehe Schritt 4.4).

---

### Problem: Rate-Limit sofort erreicht

**Ursache:** `rate_limiter_state.json` enthält alte Daten von vorherigen Tests.

**Lösung:**
```bash
# Rate-Limiter zurücksetzen
rm rate_limiter_state.json

# Bot neu starten
python main.py
```

---

## ✅ Setup-Checkliste

Gehe diese Liste durch, bevor du den Bot produktiv nutzt:

### Basis-Setup
- [ ] Python 3.10+ installiert und geprüft
- [ ] Virtual Environment erstellt und aktiviert
- [ ] Dependencies installiert (`pip install -r requirements.txt`)
- [ ] Playwright Browser installiert (`playwright install chromium`)

### Google Cloud
- [ ] Google Cloud Projekt erstellt
- [ ] Google Sheets API aktiviert
- [ ] OAuth-Zustimmungsbildschirm konfiguriert
- [ ] Testnutzer hinzugefügt (deine E-Mail)
- [ ] OAuth-Credentials erstellt
- [ ] `credentials.json` heruntergeladen und ins Projekt gelegt
- [ ] Erster Bot-Start: Google OAuth im Browser durchgeführt
- [ ] `token.json` wurde erstellt

### Google Sheet
- [ ] Test-Sheet erstellt
- [ ] Header-Zeile korrekt (Full Name, Company, Telefonnummer, ...)
- [ ] Test-Daten eingefügt (2-3 Zeilen)
- [ ] Sheet-ID kopiert

### Umgebungsvariablen
- [ ] `.env` Datei erstellt (`cp .env.example .env`)
- [ ] LinkedIn E-Mail eingetragen
- [ ] LinkedIn Passwort eingetragen
- [ ] Google Sheet-ID eingetragen
- [ ] (Optional) Serper API Key eingetragen

### Konfiguration
- [ ] LinkedIn-Limits an Account-Typ angepasst
- [ ] (Optional) Debug-Modus aktiviert für ersten Test
- [ ] (Optional) Serper API aktiviert (`use_serper: true`)

### Erster Test
- [ ] Bot gestartet: `python main.py`
- [ ] Google OAuth erfolgreich
- [ ] LinkedIn Login erfolgreich
- [ ] Mindestens 1 Lead verarbeitet
- [ ] Ergebnisse in Google Sheet sichtbar

### Production-Ready
- [ ] Headless-Modus aktiviert (`headless: true`)
- [ ] Rate-Limits final festgelegt
- [ ] Mehrere Test-Läufe erfolgreich
- [ ] Log-Datei geprüft: `tecis_bot.log`

---

## 🚀 Nächste Schritte nach Setup

1. **Teste mit 5-10 Leads** (echte Tecis-Berater)
2. **Überwache Logs** für 1-2 Tage
3. **Passe Rate-Limits** falls nötig
4. **Aktiviere Headless-Modus** für Production
5. **Erstelle Backup** deiner `.env` und `config.yaml`

---

## 📞 Support

**Bei Problemen:**

1. **Log-Datei prüfen:**
   ```bash
   tail -n 50 tecis_bot.log
   ```

2. **Debug-Level aktivieren:**
   ```yaml
   # config.yaml
   logging:
     level: "DEBUG"
   ```

3. **README konsultieren:**
   - Installation: Siehe README.md → Installation
   - Troubleshooting: Siehe README.md → Troubleshooting
   - Konfiguration: Siehe README.md → Konfiguration

4. **Google Cloud Hilfe:**
   - Offizielle Docs: https://cloud.google.com/docs/authentication
   - Sheets API: https://developers.google.com/sheets/api

---

## 🎉 Fertig!

Wenn alle Checkboxen oben aktiviert sind, ist dein Setup vollständig!

Der Bot ist jetzt einsatzbereit für den produktiven Betrieb.

**Viel Erfolg!** 🚀
