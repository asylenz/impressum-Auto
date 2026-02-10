# **Prompt für den Coding-Bot: Tecis-Berater Scraping & Validierungs-System**

**Ziel:** Entwickle einen robusten Python-Bot, der Tecis-Beraterdaten (Telefonnummern und Karrierestufen) über vier priorisierte Quellen (Tecis.de, LinkedIn, Xing, Creditreform) extrahiert und validiert.

## **Zielgruppe (Stufen-Kategorisierung)**

Die folgenden Stufen definieren die Zielgruppe und deren Priorisierung:

### ✅ **In Scope** (Primäre Zielgruppe)
- 🟢 Sales Consultant
- 🟢 Senior Sales Consultant
- 🟢 Sales Manager
- 🟢 Senior Sales Manager
- 🟢 Seniorberater
- 🟢 Teamleiter
- 🟢 Repräsentanzleiter
- 🟢 Branch Manager
- 🟢 Regional Manager
- 🟢 General Sales Manager

### ⚠️ **Out of Scope** (Nicht Zielgruppe)
- 🟠 Divisional Manager
- 🟠 General Manager
- 🟠 Juniorberater
- 🟠 Beraterassistent
- 🟠 Trainee

**Kernaufgaben:**
1.  **Input:** Liste von Personen (Vorname, Nachname, Unternehmen).
2.  **Pre-Discovery:** Sammle sequenziell initial alle URLs zu den Zielpersonen auf den vier Plattformen.
3.  **Sequenzielle Logik (Hauptlogik):**
    *   Starte bei Tecis.de (Offizielle Quelle).
    *   Fallback bei fehlenden/ungültigen Daten auf LinkedIn, dann Xing, zuletzt Creditreform.
    *   Nutze Flags (z.B. "Nur Status-Check", "Nur Stufe suchen"), um bereits gefundene Daten nicht erneut zu suchen.
4.  **Validierung:**
    *   Prüfe "Aktiver Status" (arbeitet noch bei Tecis?).
    *   Validierung der "Stufe" gegen eine Whitelist (Appendix B).
    *   LinkedIn gilt als "Authoritative Source" für den Status (Aktiv/Inaktiv).
5.  **Output:** Konsolidierte Daten (Tel 1, Tel 2, Stufe, Status) gemäß definierten Szenarien (Appendix A).

**Wichtige Regeln:**
*   **Keine Halluzinationen:** Extrahiere nur echte Daten.
*   **Platform-Specifcs:** Nutze die detaillierten Navigations-Anweisungen (CSS/XPath) für jede Plattform.
*   **Edge Cases:** Beachte die Logik für "Inaktiv/Wechsel", "Stufe ungültig" und "Mehrere Telefonnummern".

---

# **Inhaltsverzeichnis**

1.  [Zielgruppe (Stufen-Kategorisierung)](#zielgruppe-stufen-kategorisierung)
2.  [Hauptlogik (Prozess-Ablauf)](#hauptlogik-prozess-ablauf)
    *   [Phase 1: Tecis.de](#phase-1-tecisde-offizielle-landingpage)
    *   [Phase 2: LinkedIn](#phase-2-linkedin-profil-suche)
    *   [Phase 3: Xing](#phase-3-xing-profil-suche)
    *   [Phase 4: Creditreform](#phase-4-creditreform-bonitäts--gewerbe-check)
3.  [Appendix A: Output-Logik](#appendix-a-output-logik)
4.  [Appendix B: Stufen-Validation](#appendix-b-stufen-validation)
5.  [Link-Discovery & Validierungs-Strategie](#link-discovery--validierungs-strategie)
6.  [Navigation & Selektoren](#navigation)
    *   [Tecis.de](#1-tecisde-offizielle-berater-landingpage)
    *   [LinkedIn](#2-linkedin-karriere-profil)
    *   [Xing](#3-xing-karriere-profil-de)
    *   [Creditreform](#4-creditreform-bonitäts--gewerbe-check-1)

---

# **Hauptlogik (Prozess-Ablauf)**

*(Dieser Ablauf beschreibt die Priorisierung der Quellen. Der Bot durchläuft die Phasen sequenziell. Sobald eine Telefonnummer gefunden wurde oder ein Abbruch-Kriterium (z.B. "Nicht mehr in Branche") erfüllt ist, endet der Prozess für diesen Lead.)*

**Initialisierung:**
1.  **Reset:** Leere alle `target_url_[platform]` Variablen.
2.  **Discovery:** Suche URLs für alle Plattformen (Tecis, LinkedIn, Xing, Creditreform) gemäß "Link-Discovery & Validierungs-Strategie" (siehe unten).
3.  **Speichern:** Speichere valide Treffer als `target_url_[platform]`.

---

## **Phase 1: Tecis.de (Offizielle Landingpage)**
1.  **Check:** Wurde eine `target_url_tecis` gefunden?
    *   **JA:** Öffne URL und prüfe **Stufe/Position** (siehe Navigation: Tecis.de -> Datenpunkt: Titel).
     * *Stufe validierbar (Format korrekt gemäß Appendix B)?* -> Extrahiere Stufe. -> **Gehe zu Schritt 3 (Kontakt).**
     * *Stufe ungültig / nicht gefunden?* -> **Führe Schritt 3 (Kontakt) aus.**
       * *Telefon gefunden?* -> Speichere Telefon(e). -> **Springe zu Phase 2 (LinkedIn)** (mit Flag: *Nur nach Stufe suchen*).
       * *Kein Telefon?* -> **Springe zu Phase 2 (LinkedIn).**
   * **NEIN:** **Springe zu Phase 2 (LinkedIn).**

3. **Kontakt-Daten (Tecis.de):**
   * Navigiere zur Kontakt-Unterseite (`/kontaktuebersicht.html`) (siehe Navigation: Tecis.de -> Navigation: Wechsel zur Kontaktseite).
   * Prüfe auf **Telefonnummer(n)** (Mobil/Büro) (siehe Navigation: Tecis.de -> Datenpunkt: Telefonnummer(n)).
     * *Nummer gefunden?* -> Extrahiere.
       * *Stufe bereits vorhanden?* -> **Springe zu Phase 2 (LinkedIn)** (mit Flag: *Nur Status-Check*).
       * *Stufe fehlt noch?* -> (siehe Logik oben: Sprung zu Phase 2 mit Flag *Nur nach Stufe suchen*).
     * *Keine Nummer?* -> **Suche LinkedIn Profil** (Google: `{Name} LinkedIn tecis`).
       * *LinkedIn gefunden?* -> Öffne Profil -> "Contact Info".
         * *Telefon gefunden?* -> Extrahiere.
           * *Stufe bereits vorhanden?* -> **Springe zu Phase 2 (LinkedIn)** (mit Flag: *Nur Status-Check*).
           * *Stufe fehlt noch?* -> **Springe zu Phase 2 (LinkedIn)** (mit Flag: *Nur nach Stufe suchen*).
         * *Kein Telefon, aber Webseite?* (Alles außer `tecis.de` Domain) -> Öffne Impressum -> Prüfe Geschäftsführer (Abgleich mit gesuchtem Namen) -> Extrahiere Tel. -> **Springe zu Phase 2 (LinkedIn)** (mit Flag: *Nur Status-Check*).
         * *Kein Telefon UND keine Webseite?*
           * *Stufe bereits vorhanden?* -> **Springe zu Phase 2 (LinkedIn)** (mit Flag: *Status-Check & Weiter zu Creditreform*).
           * *Stufe fehlt noch?* -> **Springe zu Phase 2 (LinkedIn)** (mit Flag: *Stufe suchen & Weiter zu Creditreform*).
       * *Kein LinkedIn gefunden?*
         * *Stufe bereits vorhanden?* -> **Springe zu Phase 3 (Xing)** (mit Flag: *Status-Check & Weiter zu Creditreform*).
         * *Stufe fehlt noch?* -> **Springe zu Phase 3 (Xing)**.

---

## **Phase 2: LinkedIn (Profil-Suche)**
*(Fallback, wenn Tecis.de keine Ergebnisse liefert ODER Stufe fehlt ODER Status-Check nötig)*

**Hinweis:** Wenn bereits eine Telefonnummer in Phase 1 gefunden wurde (Flag: *Nur Stufe suchen*), wird Schritt 3 (Kontakt-Daten) übersprungen.

1.  **Check:** Wurde eine `target_url_linkedin` gefunden?
    *   **JA:** Öffne Profil.
     * Suche **Tecis-Eintrag** im Bereich "Experience" (siehe Navigation: LinkedIn -> Bereich: Experience Section).
     * *Person noch aktiv?* (Zeitraum: "Present" / "Heute") (siehe Navigation: LinkedIn -> Bereich: Validierung "Aktiver Status").
       * **JA (Aktiv):**
         * *Flag "Nur Status-Check" aktiv?* -> **ENDE (Erfolg: Validiert).**
         * *Flag "Status-Check & Weiter zu Creditreform" aktiv?* -> **Springe zu Phase 4 (Creditreform).**
         * *Stufe validierbar (Format korrekt gemäß Appendix B)?* -> Extrahiere Stufe.
           * *Flag "Nur Stufe suchen" aktiv?* -> **ENDE (Erfolg: Telefon & Stufe vorhanden).**
           * *Kein Flag?* -> **Gehe zu Schritt 3 (Kontakt).**
         * *Stufe ungültig?* -> 
           * *Flag "Nur Stufe suchen" aktiv?* -> **Springe zu Phase 3 (Xing)** (mit Flag: *Nur nach Stufe suchen (Status=Active confirmed)*).
           * *Kein Flag?* -> **Führe Schritt 3 (Kontakt) aus.**
             * *Telefon gefunden?* -> Speichere Telefon(e). -> **Springe zu Phase 3 (Xing)** (mit Flag: *Nur nach Stufe suchen (Status=Active confirmed)*).
             * *Kein Telefon?* -> **Springe zu Phase 3 (Xing)** (mit Flag: *Status-Check & Weiter zu Creditreform (Status=Active confirmed)*).
       * **NEIN (Ehemalig):** Setze Status "Wechsel/Nicht mehr in Branche" und Telefon "n/a". -> **ENDE (Abbruch).**
     * *Kein Tecis-Eintrag gefunden?* ->
       * *Flag "Status-Check & Weiter zu Creditreform" aktiv?* -> **Springe zu Phase 3 (Xing)** (Flag bleibt aktiv).
       * *Flag "Stufe suchen & Weiter zu Creditreform" aktiv?* -> **Springe zu Phase 3 (Xing)** (Flag bleibt aktiv).
       * **Springe zu Phase 3 (Xing)** (auch bei Flag *Nur Status-Check*).
   * **NEIN:** 
     * *Flag "Status-Check & Weiter zu Creditreform" aktiv?* -> **Springe zu Phase 3 (Xing)** (Flag bleibt aktiv).
     * *Flag "Stufe suchen & Weiter zu Creditreform" aktiv?* -> **Springe zu Phase 3 (Xing)** (Flag bleibt aktiv).
     * **Springe zu Phase 3 (Xing)** (auch bei Flag *Nur Status-Check*).

3. **Kontakt-Daten (LinkedIn):**
   *(Nur ausführen, wenn noch keine Telefonnummer vorhanden)*
   * Öffne "Contact Info" Modal (siehe Navigation: LinkedIn -> Bereich: Contact Info).
   * Prüfe auf **Telefonnummer**.
     * *Nummer gefunden?* -> Extrahiere.
       * *Stufe validierbar (gemäß Appendix B)?* -> **ENDE (Erfolg).**
       * *Stufe ungültig?* -> **Springe zu Phase 3 (Xing)** (mit Flag: *Nur nach Stufe suchen (Status=Active confirmed)*).
   * Prüfe auf **Webseite** (Drittanbieter, außer `tecis.de`).
     * *Webseite gefunden?* -> Öffne Impressum -> Prüfe Geschäftsführer (Abgleich mit gesuchtem Namen) -> Extrahiere Tel (siehe Navigation: LinkedIn -> Bereich: Externe Webseiten).
       * *Erfolg?* ->
         * *Stufe validierbar (gemäß Appendix B)?* -> **ENDE (Erfolg).**
         * *Stufe ungültig?* -> **Springe zu Phase 3 (Xing)** (mit Flag: *Nur nach Stufe suchen (Status=Active confirmed)*).
       * *Fehlschlag (Keine Tel / Falscher GF)?* -> **Springe zu Phase 4 (Creditreform).**
   * *Keine Daten gefunden?* -> **Springe zu Phase 4 (Creditreform).**

---

## **Phase 3: Xing (Profil-Suche)**
*(Fallback, wenn LinkedIn keine Ergebnisse liefert ODER Stufe fehlt ODER Status-Check nötig)*

**Hinweis:** Wenn bereits eine Telefonnummer in Phase 2 gefunden wurde (Flag: *Nur Stufe suchen*), wird Schritt 3 (Kontakt-Daten) übersprungen.

1.  **Check:** Wurde eine `target_url_xing` gefunden?
    *   **JA:** Öffne Profil.
     * Suche **Tecis-Eintrag** im Bereich "Berufserfahrung" (siehe Navigation: Xing -> Bereich: Berufserfahrung & Status).
     * *Person noch aktiv?* (Zeitraum: "bis heute").
       * **JA (Aktiv):**
         * *Stufe validierbar (gemäß Appendix B)?* -> Extrahiere Stufe.
           * *Flag "Nur Status-Check" aktiv?* -> **ENDE (Erfolg: Validiert).**
           * *Flag "Status-Check & Weiter zu Creditreform" aktiv?* -> **Springe zu Phase 4 (Creditreform).**
           * *Flag "Stufe suchen & Weiter zu Creditreform" aktiv?* -> **Springe zu Phase 4 (Creditreform).**
           * *Flag "Nur Stufe suchen (Status=Active confirmed)" aktiv?* -> **ENDE (Erfolg: Telefon & Stufe vorhanden).**
           * *Flag "Nur Stufe suchen" aktiv?* -> **ENDE (Erfolg: Telefon & Stufe vorhanden).**
           * *Kein Flag?* -> **Springe zu Phase 4 (Creditreform).**
         * *Stufe ungültig?* ->
           * *Flag "Nur Stufe suchen (Status=Active confirmed)" aktiv?* -> **ENDE (Erfolg: Telefon vorhanden, Stufe fehlt, Status: Unbekannt).**
           * *Sonst?* -> Setze Status "Unbekannt". -> **Springe zu Phase 4 (Creditreform).**
       * **NEIN (Ehemalig):**
         * *Flag "Nur Stufe suchen (Status=Active confirmed)" aktiv?* -> **ENDE (Erfolg: Telefon vorhanden, Stufe fehlt, Status: Unbekannt).** (Xing widerspricht LinkedIn Status, Stufe wird nicht übernommen).
         * *Kein Flag?* -> Setze Status "Wechsel/Nicht mehr in Branche" und Telefon "n/a". -> **ENDE (Abbruch).**
     * *Kein Tecis-Eintrag gefunden?* -> 
       * *Flag "Nur Status-Check" aktiv?* -> **ENDE (Erfolg: Validiert durch Tecis-Seite, kein Widerspruch gefunden).**
       * *Flag "Status-Check & Weiter zu Creditreform" aktiv?* -> **Springe zu Phase 4 (Creditreform).**
       * *Flag "Stufe suchen & Weiter zu Creditreform" aktiv?* -> **Springe zu Phase 4 (Creditreform).**
       * *Flag "Nur Stufe suchen (Status=Active confirmed)" aktiv?* -> **ENDE (Erfolg: Telefon vorhanden, Stufe fehlt, Status: Unbekannt).**
       * *Sonst?* -> Setze Status "Unbekannt". -> **Springe zu Phase 4 (Creditreform).**
   * **NEIN:** 
     * *Flag "Nur Status-Check" aktiv?* -> **ENDE (Erfolg: Validiert durch Tecis-Seite, kein Widerspruch gefunden).**
     * *Flag "Status-Check & Weiter zu Creditreform" aktiv?* -> **Springe zu Phase 4 (Creditreform).**
     * *Flag "Stufe suchen & Weiter zu Creditreform" aktiv?* -> **Springe zu Phase 4 (Creditreform).**
     * *Flag "Nur Stufe suchen (Status=Active confirmed)" aktiv?* -> **ENDE (Erfolg: Telefon vorhanden, Stufe fehlt, Status: Unbekannt).**
     * *Sonst?* -> Setze Status "Unbekannt". -> **Springe zu Phase 4 (Creditreform).**

---

## **Phase 4: Creditreform (Bonitäts- & Gewerbe-Check)**
*(Letzte Instanz, um eine Telefonnummer zu finden, wenn Stufe bekannt aber kein Kontakt)*

1.  **Check:** Wurde eine `target_url_creditreform` gefunden?
    *   **JA:** Öffne URL (firmeneintrag.creditreform.de).
     * Suche im Container `#kontakt` nach Telefonnummer (Regex-Check) (siehe Navigation: Creditreform -> Bereich: Kontakt).
     * *Nummer gefunden?* -> Extrahiere Telefon(e). -> **ENDE.**
     * *Keine Nummer?* -> Setze Tel "garkeine". -> **ENDE.**
   * **NEIN:** Setze Tel auf "garkeine". -> **ENDE.**

---

### **Appendix A: Output-Logik**

*(Anzuwenden beim Abschluss der Suche, um die Ziel-Spalten zu füllen. Diese Logik greift vor allem, wenn die Person grundsätzlich gefunden wurde oder der Prozess regulär endet.)*

**Ziel-Spalten:**
1. `Telefonnummer`
2. `Zweite Telefonnummer`
3. `Stufe/Position`
4. `Status`

**Szenario 1: Wenn Telefonnummer(n) und Stufe gefunden**
> **Telefonnummer:** `{Tel. Nr.}`
> **Zweite Telefonnummer:** `{Tel. Nr.}` (falls vorhanden, sonst leer)
> **Stufe/Position:** `{Stufe}`
> **Status:** (leer)

**Szenario 2: Wenn Telefonnummer(n) aber KEINE Stufe**
> **Telefonnummer:** `{Tel. Nr.}`
> **Zweite Telefonnummer:** `{Tel. Nr.}` (falls vorhanden, sonst leer)
> **Stufe/Position:** `n/a`
> **Status:** `Unbekannt`

**Szenario 3: Wenn Stufe aber KEINE Telefonnummer**
> **Telefonnummer:** `garkeine`
> **Zweite Telefonnummer:** (leer)
> **Stufe/Position:** `{Stufe}`
> **Status:** (leer)

**Szenario 4: Wenn KEINE Telefonnummer und KEINE Stufe**
> **Telefonnummer:** `garkeine`
> **Zweite Telefonnummer:** (leer)
> **Stufe/Position:** `n/a`
> **Status:** `Unbekannt`

**Szenario 5: Wenn KEIN Tecis Eintrag**
> **Telefonnummer:** `n/a`
> **Zweite Telefonnummer:** (leer)
> **Stufe/Position:** `n/a`
> **Status:** `Unbekannt`

**Szenario 6: Wenn NICHT mehr bei Tecis**
> **Telefonnummer:** `n/a`
> **Zweite Telefonnummer:** (leer)
> **Stufe/Position:** `n/a`
> **Status:** `Wechsel/Nicht mehr in Branche`

---

### **Appendix B: Stufen-Validation**

Eine Stufe gilt **NUR** dann als **gültig**, wenn sie exakt (oder mit vernachlässigbaren Abweichungen wie Groß-/Kleinschreibung) einem der folgenden Begriffe entspricht. Alles andere wird als **"ungültig"** klassifiziert.

**Gültige Stufen (In Scope - Zielgruppe):**
*   🟢 "Sales Consultant"
*   🟢 "Senior Sales Consultant"
*   🟢 "Sales Manager"
*   🟢 "Senior Sales Manager"
*   🟢 "Seniorberater"
*   🟢 "Teamleiter"
*   🟢 "Repräsentanzleiter"
*   🟢 "Branch Manager"
*   🟢 "Regional Manager"
*   🟢 "General Sales Manager"

**Ungültige Stufen (Out of Scope - Nicht Zielgruppe):**
*   🟠 "Divisional Manager"
*   🟠 "General Manager"
*   🟠 "Juniorberater"
*   🟠 "Beraterassistent"
*   🟠 "Trainee"

**Hinweis:** Wenn eine Person eine "Out of Scope" Stufe hat, wird Status auf **"ungültig"** gesetzt.

# **Link-Discovery & Validierungs-Strategie**

**Globale Strategie:** "SERP-First" (Search Engine Results Page).

Der Scraper errät keine URLs. Er nutzt Google Search Operators (Dorks), um die Indexierung von Google als Filter zu nutzen.

**Input-Daten pro Lead:**

1. {Vorname}  
2. {Nachname}  
3. {Unternehmen}

### **Zusammenfassung der Architektur für den Entwickler**

Um dieses Modul zu bauen, benötigt der Bot folgende Logik-Kette:

1. **Input:** Nimm Vorname & Nachname aus der Datenbank.  
2. **Reset (Scope):** **WICHTIG:** Vor jedem neuen Lead müssen alle `target_url_[platform]` Variablen geleert werden. Es darf keine Persistenz von Links über mehrere Personen hinweg geben. Jede Suche ist ein isolierter Vorgang.
3. **Loop:** Iteriere durch die 4 definierten **Such-Queries**.  
4. **Request:** Sende Query an Google (via API/Proxy).  
5. **Parsing:** Nimm das **erste** organische Ergebnis (keine Ads).  
6. **Check & Validierung:**  
   * Passt die URL zur **Erwarteten Struktur**?  
   * **JA** -> Prüfe: Stimmt der Name im Link/Titel mit der gesuchten Person überein?
     * **MATCH** -> Speichere URL als `target_url_[platform]` **exklusiv für diesen Lead**.  
     * **NO MATCH** -> Verwerfen.
   * **NEIN** -> Markiere als "Kein Eintrag gefunden".

## **1\. Tecis.de (Offizielle Berater-Landingpage)**

Dies ist die vertrauenswürdigste Quelle. Wenn diese Seite existiert, ist der Lead (meist) aktiv und verifiziert.

* **Strategie:** Direkte Suche auf der Domain des Unternehmens.  
* **Google Such-Query (Pattern):**  
  site:tecis.de "{Vorname} {Nachname}"  
* **Erwartete URL-Struktur:**  
  https://www.tecis.de/{vorname}-{nachname}.html  
  1. *Hinweis:* Manchmal auch ohne .html oder mit Variationen bei Namensgleichheit (z.B. ...-2.html).  
* **Validierungs-Logik (Match):**  
  1. Domain muss exakt tecis.de sein (keine Subdomains wie blog.tecis.de oder login...).  
  2. Der Slug (der Teil nach dem /) sollte den Namen des Leads enthalten.

## **2\. LinkedIn (Karriere-Profil)**

Hier ist die Verwechslungsgefahr am größten. Die Verknüpfung mit dem Keyword "tecis" ist zwingend erforderlich.

* **Strategie:** Suche nach Profilen, die den Namen UND "tecis" im sichtbaren Text haben.  
* **Google Such-Query (Pattern):**  
  site:linkedin.com/in/ "{Vorname} {Nachname}" tecis  
* **Erwartete URL-Struktur:**  
  https://www.linkedin.com/in/{slug-id}/  
  1. *Beispiel:* https://www.linkedin.com/in/niklas-fay-908365222/  
  2. *Sauberer Slug:* https://www.linkedin.com/in/niklas-fay/  
* **Validierungs-Logik (Match):**  
  1. URL muss /in/ enthalten (schließt Job-Postings /jobs/ oder Artikel /pulse/ aus).  
  2. Der Bot muss später prüfen, ob "tecis" im Bereich "Aktuelle Position" steht (da Google auch alte Einträge finden könnte).

## **3\. Xing (Karriere-Profil DE)**

Ähnlich wie LinkedIn, aber oft mit anderer URL-Struktur für Portfolio-Seiten.

* **Strategie:** Suche im Profil-Pfad.  
* **Google Such-Query (Pattern):**  
  site:xing.com/profile "{Vorname} {Nachname}" tecis  
* **Erwartete URL-Struktur:**  
  https://www.xing.com/profile/{Slug\_Mit\_ID}  
  1. *Beispiel:* https://www.xing.com/profile/Christian\_Mueller2142  
* **Validierungs-Logik (Match):**  
  1. URL muss /profile/ enthalten.  
  2. URL sollte keine generischen Suchseiten von Xing sein (z.B. [xing.com/search/](http://xing.com/search/)...).  
  3. Der Bot muss später prüfen, ob "tecis" im Bereich "Aktuelle Position" steht (da Google auch alte Einträge finden könnte).

## **4\. Creditreform (Bonitäts- & Gewerbe-Check)**

Da Tecis-Berater oft selbstständige Handelsvertreter sind, suchen wir nach ihrem persönlichen Gewerbeeintrag. Der Firmenname weicht oft ab (z.B. "Schneider Finanzdienstleistungen"), daher ist die Suche über den Namen im Verzeichnis entscheidend.

* **Strategie:** Suche im Verzeichnis firmeneintrag.creditreform.de nach dem Personennamen in Kombination mit Finanz-Keywords, um Bäcker oder Handwerker gleichen Namens auszuschließen.  
* **Google Such-Query (Pattern):**  
  site:firmeneintrag.creditreform.de "{Vorname} {Nachname}" Versicherungsmakler  
* **Erwartete URL-Struktur:**  
  https://firmeneintrag.creditreform.de/{PLZ}/{ID}/{SLUG}  
  1. *Beispiel:* .../26135/2370245796/THORSTEN\_SCHNEIDER\_FINANZDIENSTLEISTUNGEN  
* **Validierungs-Logik (Match):**  
  1. Domain muss firmeneintrag.creditreform.de sein.  
  2. URL oder Seitentitel muss {Nachname} enthalten.  
  3. **Ausschluss:** Wenn Keywords wie "GmbH", "UG" fehlen und stattdessen Branchenfremde Begriffe (z.B. "Maler", "Bäcker") im Snippet auftauchen \-\> Ignorieren. Wir suchen meist Einzelunternehmer oder e.K.

# **Navigation**

## **1\. Tecis.de (Offizielle Berater-Landingpage)**

**Globale Logik:**

Der Bot besucht erst die Haupt-Landingpage (z.B. tecis.de/max-mustermann.html), zieht dort die Stufe, und navigiert dann zur Unterseite /kontaktuebersicht.html, um die Daten zu holen.

#### **1\. Datenpunkt: Karrierestufe / Titel**

| Feld | Selektor-Strategie (CSS/XPath) | Erklärung |
| :---- | :---- | :---- |
| **Titel (Stufe)** | **CSS:** .personal-information\_\_title | Das Element ist sehr stabil. Es ist ein \<span\> Tag innerhalb der "personal-information"-Box. |
| **Alternative** | **XPath:** //h1/following-sibling::span\[contains(@class, 'title')\] | Falls sich der Klassenname ändert, nimm das Span-Element direkt unter dem Namen (H1). |

#### **2\. Navigation: Wechsel zur Kontaktseite**

*Strategie: URL-Konstruktion*

Statt nach einem Button zu suchen, ist es schneller, die URL umzubauen.

* **Logik:** Nimm die aktuelle URL (z.B. .../max-mustermann.html).  
* **Aktion:** Ersetze .html am Ende durch /kontaktuebersicht.html.  
* **Ergebnis:** .../max-mustermann/kontaktuebersicht.html

#### **3\. Datenpunkt: Telefonnummer(n)**

Wir nutzen das **Protokoll-Attribut**.

| Feld | Selektor-Strategie (CSS/XPath) | Erklärung |
| :---- | :---- | :---- |
| **Telefon (Mobil & Büro)** | **CSS:** div.contacts-columns a\[href^="tel:"\] | **Wichtig:** Dieser Selektor findet *alle* Links innerhalb der Spalte, die mit tel: beginnen. Das ist 100% treffsicher, egal an welcher Stelle sie stehen. |
| **Logik für mehrere Nummern** | findall() | Wenn der Selektor 2 Ergebnisse liefert, speichere das erste als "Telefon 1" und das zweite als "Telefon 2". |
| **Email (Optional)** | **CSS:** div.contacts-columns a\[href^="mailto:"\] | Findet sicher die E-Mail-Adresse, unabhängig von der Position. |

---


### **Zusammenfassung:**

**Tecis-Seite Extraktion:**

1. Auf der Landingpage: Extrahiere Text aus Klasse .personal-information\_\_title für die "Stufe".  
2. Konstruiere Kontakt-URL: Base-URL minus .html plus /kontaktuebersicht.html.  
3. Auf Kontaktseite: Suche im Container .contacts-columns.  
   * NICHT per Index (1., 2., 3.) scrapen\!  
   * Nutze Attribut-Selektor a\[href^="tel:"\] um alle Telefonnummern zu finden.  
   * Extrahiere die Nummer entweder aus dem href (bereinige "tel:") oder dem sichtbaren Text.

## **2\. LinkedIn (Karriere-Profil)**

### **Bereich: Externe Webseiten (via LinkedIn gefunden)**

Wenn eine Webseite über LinkedIn gefunden wird (z.B. im Impressum), ist die Struktur nicht vordefiniert. Hier muss generisch gesucht werden.

**Globale Logik:**
1.  Öffne die gefundene URL.
2.  Suche nach **Impressum** Link/Button.
3.  Öffne Impressum.
4.  Vergleiche **Geschäftsführer** mit gesuchter Person und extrahiere **Telefonnummer**.

#### **1\. Navigation zum Impressum**

| Aktion | Selektor-Strategie (XPath) | Erklärung |
| :---- | :---- | :---- |
| **Finde Impressum** | `//a[contains(translate(text(), 'IMPRESSUM', 'impressum'), 'impressum')]` | Sucht nach Links, die das Wort "Impressum" enthalten (case-insensitive). |
| **Alternative** | `//footer//a[contains(@href, 'impressum')]` | Sucht im Footer nach Links mit "impressum" in der URL. |

#### **2\. Datenpunkt: Geschäftsführer (Validierung)**

Wir müssen sicherstellen, dass die Webseite zur gesuchten Person gehört.

*   **Logik:** Suche auf der Impressums-Seite nach dem Namen des Leads (Vorname + Nachname).
*   **Match:** Wenn der Name im Text vorkommt (z.B. "Geschäftsführer: Max Mustermann"), gilt die Seite als verifiziert.

#### **3\. Datenpunkt: Telefonnummer**

| Feld | Selektor-Strategie | Erklärung |
| :---- | :---- | :---- |
| **Telefon** | `//a[starts-with(@href, 'tel:')]` | Suche nach klickbaren Telefon-Links. |
| **Alternative** | Regex Suche im gesamten Text (Body) | Suche nach Mustern wie `(\+49|0)[0-9\s\-\/]{6,}`. |

---

### **Bereich: LinkedIn \- Experience Section (Berufserfahrung)**

**Ziel:** Extrahiere den Jobtitel, der zum Unternehmen "tecis Finanzdienstleistungen AG" gehört.

*Suche im Experience-Bereich nach dem Listenelement, das 'tecis Finanzdienstleistungen AG' enthält. Extrahiere daraus die erste Zeile Text (den Jobtitel).*

#### **1\. Der Container (Wo suchen wir?)**

* Suche nach der Sektion mit der id="experience" (oder alternativ data-view-name="profile-card-experience").  
* Innerhalb dieser Sektion gibt es eine Liste von Positionen (\<ul\> mit \<li\> Einträgen).

#### **2\. Der Anker (Wie finden wir den richtigen Eintrag?)**

* Iteriere durch die Listenelemente (\<li\>).  
* Prüfe in jedem Element, ob der Text **"tecis Finanzdienstleistungen AG"** vorkommt.  
  * *Hinweis für Dev:* Am stabilsten ist oft der alt\-Text des Logos oder der zweite \<span\> im Textblock.  
  * Im Screenshot sieht man: alt="tecis Finanzdienstleistungen AG logo". Das ist der sicherste Anker\!

#### **3\. Das Ziel (Was extrahieren wir?)**

* Wenn der Anker gefunden wurde: Gehe im selben Listenelement (\<li\>) zum **ersten Textelement** (meist ein \<span\> mit aria-hidden="true" für die visuelle Darstellung).  
* Der Titel steht in der Hierarchie **über** dem Firmennamen.

---

#### **⚠️ Zusatzregel: Mehrere Tecis-Positionen (Historie)**

Da viele Berater mehrere Karrierestufen durchlaufen haben (z.B. erst Trainee, dann Consultant), taucht "tecis" oft mehrfach in der Liste auf.

**Die "First-Match"-Regel:**

Da LinkedIn die Einträge chronologisch absteigend sortiert (neueste oben), muss der Bot **zwingend den ersten gefundenen Treffer von oben** nehmen.

* **Logik:** Iteriere von oben nach unten durch die \<li\>\-Liste.  
* **Aktion:** Sobald das *erste* Element mit "tecis Finanzdienstleistungen AG" gefunden wurde \-\> **Daten extrahieren und Loop abbrechen (Break).**  
* **Grund:** Alle weiteren Treffer weiter unten sind veraltete Positionen und würden falsche Daten liefern.

---

#### Technische Übersetzung (XPath Logik)

Damit dein Entwickler genau weiß, was gemeint ist, gib ihm diese **XPath-Logik** (das ist eine Wegbeschreibung durch den HTML-Code) dazu. Das ist viel robuster als CSS-Klassen:

"Nutze einen relativen XPath, der vom Firmennamen rückwärts zum Titel sucht:"

XQuery

```
//li[descendant::span[contains(text(), 'tecis Finanzdienstleistungen AG')]]//span[@aria-hidden='true'][1]
```

**Erklärung der Logik:**

1. //li\[...\]: Finde das Listenelement...  
2. descendant::... 'tecis...': ...in dem irgendwo "tecis Finanzdienstleistungen AG" steht.  
3. //span\[@aria-hidden='true'\]\[1\]: Nimm darin das **erste** sichtbare Textfeld. Das ist bei LinkedIn-Standard-Layouts immer der Jobtitel (z.B. "Seniorberater").

---

### **Bereich: LinkedIn \- Validierung "Aktiver Status"**

**Ziel:** Prüfen, ob der gefundene Tecis-Eintrag noch aktuell ist oder in der Vergangenheit liegt.

#### **1\. Der Container (Wiederholung des Ankers)**

Wir befinden uns im selben \<li\> (Listen-Element), das wir im vorherigen Schritt über den Text "tecis Finanzdienstleistungen AG" gefunden haben.

#### **2\. Der Datums-Selektor**

Innerhalb dieses Containers suchen wir nach dem Text, der den Zeitraum beschreibt.

| Feld | Selektor-Strategie (XPath) | Erklärung |
| :---- | :---- | :---- |
| **Zeitraum (Rohdaten)** | .//span\[contains(text(), 'Present') or contains(text(), 'Heute') or contains(text(), 'bis heute') or contains(text(), ' \- ')\] | Wir suchen im Tecis-Container nach einem Text-Element, das typische Datums-Indikatoren enthält. LinkedIn nutzt meist einen Bindestrich oder das Wort "Present" oder “Heute”. |
| **Alternative (Struktur)** | .//span\[contains(text(), 'tecis')\]/following::span\[contains(@class, 't-black--light')\]\[1\] | Nimm das erste ausgegraute Text-Element (t-black--light), das *nach* dem Firmennamen kommt. Das ist visuell immer der Zeitraum. |

#### **3\. Die Logik-Regel (Status-Check)**

Der Bot muss flexibel auf die Sprache (Deutsch/Englisch) reagieren:

**Status-Algorithmus:**

1. Extrahiere den Datums-String (z.B. "Nov 2024 \- Present" oder "Jan 2020 \- Dec 2022").  
2. **Prüfung auf "AKTIV":**  
   * Enthält der String das Wort **"Present"**? \-\> STATUS: AKTIV  
   * Enthält der String das Wort **"Heute"** oder **"bis heute"**? \-\> STATUS: AKTIV  
3. **Prüfung auf "INAKTIV" (Ehemalig):**  
   * Wenn keines der oberen Worte vorkommt, sondern ein Enddatum (z.B. "Dec 2022"), dann hat der Berater aufgehört. \-\> STATUS: INAKTIV \-\> *Diesen Lead verwerfen.*

---

#### **⚠️ Zusatzregel: Mehrere Tecis-Positionen (Historie)**

Da viele Berater mehrere Karrierestufen durchlaufen haben (z.B. erst Trainee, dann Consultant), taucht "tecis" oft mehrfach in der Liste auf.

**Die "First-Match"-Regel:**

Da LinkedIn die Einträge chronologisch absteigend sortiert (neueste oben), muss der Bot **zwingend den ersten gefundenen Treffer von oben** nehmen.

* **Logik:** Iteriere von oben nach unten durch die \<li\>\-Liste.  
* **Aktion:** Sobald das *erste* Element mit "tecis Finanzdienstleistungen AG" gefunden wurde \-\> **Daten extrahieren und Loop abbrechen (Break).**  
* **Grund:** Alle weiteren Treffer weiter unten sind veraltete Positionen und würden falsche Daten liefern.

---

### **Zusammenfassung für den Entwickler (Copy & Paste)**

**Zusatzmodul: LinkedIn Status-Validierung**

* **Kontext:** Arbeite innerhalb des \<li\> Elements, das als "tecis" identifiziert wurde.  
* **Aktion:** Suche das span\-Element, das den Text "Present", "Heute" oder einen Bindestrich " \- " enthält (meist direkt unter dem Firmennamen).  
* **Validierung:**

```py
date_text = element.text.lower()
active_keywords = ["present", "heute", "current", "aktuell"]

if any(keyword in date_text for keyword in active_keywords):
    return True  # Lead ist aktiv
else:
    return False # Lead ist ehemalig (hat Enddatum)
```

**Möchtest du jetzt die Zusammenfassung aller Teile in einer finalen Datei-Struktur haben, oder fehlt noch eine Plattform/Funktion?**

### **Bereich: LinkedIn \- Contact Info (Modal / Popup)**

**Ablauf:**

1. Der Bot sucht auf der Profilseite den Link "Contact info".  
2. Er klickt darauf und **wartet**, bis das Popup (role="dialog") geladen ist.  
3. Er iteriert durch die Sektionen im Popup, um Website und Telefon zu finden.

#### **1\. Interaktion: Das Modal öffnen**

| Aktion | Selektor-Strategie | Erklärung |
| :---- | :---- | :---- |
| **Klick auf "Contact info"** | **ID:** top-card-text-details-contact-info | Diese ID liegt auf dem Anker-Tag \<a\> (oder dem direkten Wrapper). Das ist der stabilste Einstiegspunkt. |
| **Fallback** | **XPath:** //a\[contains(@href, 'detail/contact-info') or contains(@href, 'overlay/contact-info')\] | Sucht nach einem Link, der "contact-info" in der URL hat. Funktioniert auch, wenn sich IDs ändern. |

#### **2\. Extraktion: Daten aus dem Modal ziehen**

*Hinweis: Da die Klassen hier kryptisch sind (z.B. \_7315fc4a), nutzen wir die **Sektions-Überschriften** (h3) als Anker.*

| Feld | Selektor-Strategie (XPath) | Logik & Filter |
| :---- | :---- | :---- |
| **Telefonnummer** | //section\[.//h3\[text()='Phone' or text()='Telefon'\]\]//ul/li/span\[1\] | 1\. Suche die Section, die eine Überschrift (h3) mit "Phone" oder "Telefon" hat. 2\. Nimm darin die erste Textzeile aus der Liste. |
| **Webseite (URL)** | //section\[.//h3\[text()='Website' or text()='Websites'\]\]//a/@href | 1\. Suche Section mit Überschrift "Website(s)". 2\. Extrahiere alle href Attribute. |

---

#### Zusammenfassung

**Zusatzmodul: LinkedIn Contact Info**

1. Suche Element \#top-card-text-details-contact-info und führe .click() aus.  
2. Warte auf Element mit role="dialog" (Das Modal).  
3. **Telefon:** Suche nach Sektion mit Header "Phone"/"Telefon". Extrahiere Text.  
4. **Webseite:** Suche nach Sektion mit Header "Website". Extrahiere href.  
   * *WICHTIG:* Ignoriere URLs, die linkedin.com oder tecis.de enthalten. Speichere nur dritt-Domains (z.B. schneider-finanz.de).  
5. Schließe das Modal (Klick auf button\[aria-label="Dismiss"\]) oder navigiere direkt weiter.

Das ist der letzte wichtige Baustein. Xing ist technisch etwas anders aufgebaut als LinkedIn (nutzt viele "Styled Components", erkennbar an klassen wie sc-15...), aber es gibt hier sehr gute **Data-Attribute**, die wir nutzen können.

Das Bild image\_2ef3da.jpg zeigt deutlich, dass wir uns auf Attribute wie data-mds und data-qa verlassen können.

Hier ist der Eintrag für dein Aufbereitungsdokument:

### 

## **3\. Xing (Karriere-Profil DE)**

### **Bereich: Xing \- Berufserfahrung & Status**

**Globale Strategie:**

Xing nutzt dynamische CSS-Klassen (z.B. sc-55d8c26d...), die sich täglich ändern können. **Verboten\! diese Klassen zu nutzen.**

Stattdessen navigieren wir über **Text-Anker** ("tecis") und stabile **Data-Attribute** (data-mds="Headline").

#### **1\. Der Container (Die richtige Station finden)**

Genau wie bei LinkedIn müssen wir erst den richtigen Eintrag in der Timeline finden.

* **Logik:** Suche nach dem Listen-Element, das das Unternehmen "tecis Finanzdienstleistungen AG" enthält.  
* **Selektor (XPath):**

XQuery

```
//div[contains(@class, 'entry')]//a[contains(text(), 'tecis Finanzdienstleistungen AG')]/ancestor::div[contains(@data-qa, 'timeline-item') or contains(@class, 'entry')]
```

* *(Erklärung: Finde den Link mit dem Firmennamen und gehe dann im HTML-Baum nach oben zum umschließenden Container/Kasten).*  
* **"First-Match"-Regel:** Auch hier gilt: Nimm den **obersten** Treffer. Xing sortiert chronologisch absteigend.

#### **2\. Datenpunkt: Job-Titel (Stufe)**

Im Screenshot sehen wir, dass der Titel in einem \<h4\> Tag steht, das ein sehr wertvolles Attribut hat: data-mds="Headline".

| Feld | Selektor-Strategie (XPath) | Erklärung |
| :---- | :---- | :---- |
| **Titel (Stufe)** | .//h4\[@data-mds="Headline"\] | Wir suchen *innerhalb* des gefundenen Tecis-Containers nach der Überschrift, die als "Headline" markiert ist. Das ist extrem stabil. |
| **Fallback** | .//a\[contains(text(), 'tecis')\]/preceding-sibling::h4 | Falls das Attribut fehlt: Der Titel steht im Code meist *vor* oder *über* dem Firmen-Link. |

#### 

#### **3\. Validierung: "Aktiver Status" (Bis heute)**

In der HTML Struktur sehen wir das Datum "bis heute" in einem \<strong\> Tag (fettgedruckt) oder einem \<span\>.

* **Logik:** Prüfe, ob im Datums-Bereich das Signalwort für "Aktuell" steht.  
* **Selektor für den Text:**  
  Suche innerhalb des Tecis-Containers nach Text-Elementen, die Datums-Informationen enthalten.

| Feld | Selektor-Strategie | Logik-Prüfung |
| :---- | :---- | :---- |
| **Status-Text** | .//p\[contains(text(), 'heute')\] oder .//strong\[contains(text(), 'heute')\] | Suche nach dem Wort "heute" (oder "Present" bei englischer Einstellung). |

**Der Algorithmus:**

**Xing Status-Check:**

1. Isoliere den Container der Tecis-Station.  
2. Extrahiere den gesamten sichtbaren Text dieses Containers (z.B. via .innerText).  
3. Wende folgende Prüfung an:

```py
container_text = element.text.lower()
# Xing nutzt oft "bis heute" oder "seit ..." für aktuelle Jobs
if "bis heute" in container_text or "present" in container_text:
    return True  # Aktiv
elif "seit" in container_text and not (" - " in container_text):
     # Wenn da nur "Seit 2023" steht ohne Enddatum, ist es auch aktiv
    return True
else:
    return False # Wahrscheinlich ehemalig (z.B. "2020 - 2022")
```

---

### **Zusammenfassung**

**Modul: Xing Profil Extraktion**

* **Warnung:** Keine sc-xyz Klassen nutzen\!  
* **Schritt 1 (Finden):** Suche den Container (meist li oder div), der den Link-Text "tecis Finanzdienstleistungen AG" enthält. Nimm nur den ersten (obersten) Treffer.  
* **Schritt 2 (Titel):** Suche innerhalb dieses Containers nach h4\[@data-mds="Headline"\]. Extrahiere den Text.  
* **Schritt 3 (Status):** Prüfe den Textinhalt des Containers.  
  * Enthält er **"bis heute"**, **"Present"** oder **"Seit \[Jahr\]"** (ohne Endjahr)? \-\> **Status: Aktiv**.  
  * Sonst \-\> **Status: Inaktiv/Ehemalig**.

## **4\. Creditreform (Bonitäts- & Gewerbe-Check)**

Die Creditreform-Seite ist strukturierter als LinkedIn oder Xing, aber sie nutzt generische Klassennamen ("adress-white"), die für alles Mögliche (Straße, PLZ, Telefon) genutzt werden.

---

### **Bereich: Creditreform \- Kontakt / Telefonnummer**

#### **1\. Der Container (Die Sektion finden)**

Wir nutzen die ID der Sektion, da diese extrem stabil ist.

* **Anker:** id="kontakt"  
* **Strategie:** Der Bot soll seinen Suchbereich auf das div mit dieser ID beschränken.

#### **2\. Datenpunkt: Telefonnummer**

Das Problem hier: Die Klasse adress-white wird vermutlich auch für die Straße und den Ort verwendet. Wir können also nicht einfach "den ersten Treffer" nehmen.

| Feld | Selektor-Strategie (CSS/XPath) | Logik & Filter |
| :---- | :---- | :---- |
| **Telefonnummer** | \#kontakt .adress-white | 1\. Sammle **alle** Elemente innerhalb von \#kontakt, die die Klasse .adress-white haben. 2\. Prüfe den Textinhalt mit Regex (siehe unten), um die Straße auszusortieren und die Nummer zu finden. |

#### **3\. Der Algorithmus für den Entwickler**

Da wir nicht wissen, an welcher Stelle die Nummer steht (Zeile 1, 2 oder 3), muss der Bot den Inhalt prüfen.

**Creditreform Telefon-Logik:**

1. Suche Container \#kontakt.  
2. Extrahiere alle Textelemente mit Klasse .adress-white (oder einfach alle spans in diesem Bereich).  
3. **Regex-Filter:**  
   Iteriere durch die Texte. Wenn ein Text fast nur aus Zahlen, Pluszeichen und Leerzeichen besteht, ist es die Telefonnummer.

````py
import re
# Erlaubt +, Zahlen, Leerzeichen, Bindestriche/Klammern. Mindestens 5 Ziffern.
phone_pattern = re.compile(r'^[\+\(\)\d\s\/-]{5,}$')

for element in elements:
    text = element.text.strip()
    if phone_pattern.match(text):
        return text # Gefunden!
```
````

---

### **Zusammenfassung**

**Modul: Creditreform Kontakt**

* **Container:** Suche nach div mit id="kontakt".  
* **Selektion:** Finde alle span oder p Tags mit der Klasse .adress-white.  
* **Validierung:**  
  * Die Klasse wird für Adresse UND Telefon genutzt.  
  * Wende einen **Regex-Check** an (suche nach String mit Ziffern und "+"), um Straßennamen zu ignorieren.  
  * Extrahiere nur den Match, der wie eine Telefonnummer aussieht.