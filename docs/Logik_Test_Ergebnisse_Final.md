Zum testen der Logik, werde ich dir jetzt mehrere Szenarios aufzeigen. Du sollst die szenarios mit der aktuellen logik durchgehen und mir die Schritte und Endergebnisse aufzeigen. Damit kann ich checken dass die Logik korrekt ist.

"""
Szenario A:
"
Tecis Seite existiert, Stufe richtig und Telefonnummer existiert
"

Szenario B:
"
Tecis Seite existiert, Stufe ungültig, Telefonnummer existiert
"

Szenario C:
"
Tecis Seite existiert, Stufe ungülgitg, Telefonnummer existiert nicht, LinkedIn Seite existiert auch nicht
"

Szenario D:
"
Tecis Seite existiert nicht, LinkedIn existiert aber mit ungültiger Stufe, Webseite auf LinekdIn vorhanden, Geschäftsführer korrekt und Telefonnummer existiert
"

Szenario E:
"
Tecis Seite existiert, Stufe ungültig und Telefonnummer existiert, LinkedIn existiert mit ungültiger Stufe
"

Szenario F:
"
Tecis Seite da, Stufe gültig, Telefonnummer da, LinkedIn Seite nicht da, Xing Seite da, Tecis Eintrag aktuell
"

Szenario G:
"
Tecis Seite da, Stufe gültig, Telefonnummer nicht da, LinkedIn Seite da, Tecis Eintrag nicht da, Xing Seite da, Tecis Eintrag aktuell
"

Szenario H:
"
Tecis Seite nicht da, LinkedIn da, Tecis Eintrag veraltet
"

Szenario I:
"
Tecis Seite nicht da, LinkedIn da, Tecis Eintrag aktuell, Stufe gültig, Webseite nicht vorhanden, Creditreform Seite da, Telefonnummer nicht da
"
"""

---

## Durchlauf mit aktueller Logik

**Abkürzungen:** Tel = Telefonnummer, Stufe = Stufe/Position, ZG = Zielgruppe.  
Phasen: **P1** = Tecis, **P2** = LinkedIn, **P3** = Xing, **P4** = Creditreform, **Output** = `_apply_output_logic`.

---

### Szenario A: Tecis existiert, Stufe gültig, Telefon existiert

| Schritt | Was passiert |
|--------|----------------|
| Link-Discovery | Tecis-URL (und ggf. LinkedIn/Xing/Creditreform) gefunden |
| P1 Tecis | URL da → Stufe (gültig/In Scope) + Telefon extrahiert → `flags.stufe_gefunden=True`, `flags.telefonnummer_gefunden=True` |
| P2 LinkedIn | Bedingung „nicht Tel oder nicht Stufe“ = false → **übersprungen** |
| P3 Xing | `not stufe_gefunden` = false → **übersprungen** |
| P4 Creditreform | `not telefonnummer_gefunden` = false → **übersprungen** |
| Output | has_telefon, has_stufe, Stufe In Scope → Zielgruppe „In Scope“, Status leer (Szenario 1) |

**Endergebnis:** Telefonnummer = {aus Tecis}, Zweite Tel = {falls vorhanden}, Stufe = {Stufe}, Zielgruppe = **In Scope**, Status = **(leer)**

---

### Szenario B: Tecis existiert, Stufe ungültig, Telefon existiert

| Schritt | Was passiert |
|--------|----------------|
| P1 Tecis | Stufe (ungültig/Out of Scope) + Telefon → Flags gesetzt |
| P2/P3/P4 | Übersprungen |
| Output | has_stufe → out_of_scope → Zielgruppe „Out of Scope“, **Status = „ungültig“**, Telefon bleibt |

**Endergebnis:** Telefonnummer = {aus Tecis}, Stufe = {ungültige Stufe}, Zielgruppe = **Out of Scope**, Status = **ungültig**

---

### Szenario C: Tecis existiert, Stufe ungültig, Telefon nicht, LinkedIn nicht

| Schritt | Was passiert |
|--------|----------------|
| P1 Tecis | Stufe (ungültig), keine Telefonnummer → stufe_gefunden=True, telefonnummer_gefunden=False |
| P2 LinkedIn | Keine LinkedIn-URL → **übersprungen** |
| P3 Xing | stufe_gefunden → **übersprungen** |
| P4 Creditreform | Läuft (kein Tel, Stufe da); ohne Treffer bleibt Tel leer |
| Output | has_telefon=False, has_stufe=True (ungültig) → out_of_scope → Status **ungültig**, Telefon = **garkeine** |

**Endergebnis:** Telefonnummer = **garkeine**, Stufe = {ungültige Stufe}, Zielgruppe = **Out of Scope**, Status = **ungültig**

---

### Szenario D: Tecis nicht, LinkedIn mit ungültiger Stufe, Webseite/Geschäftsführer/Telefon da

| Schritt | Was passiert |
|--------|----------------|
| P1 Tecis | Keine URL → übersprungen |
| P2 LinkedIn | Stufe (ungültig) + Telefon extrahiert, Eintrag aktuell → Flags gesetzt |
| P3/P4 | Übersprungen |
| Output | Wie B: Out of Scope, **Status = ungültig**, Telefon bleibt |

**Endergebnis:** Telefonnummer = {aus LinkedIn}, Stufe = {ungültige Stufe}, Zielgruppe = **Out of Scope**, Status = **ungültig**

---

### Szenario E: Tecis + LinkedIn, beide ungültige Stufe, Telefon da

Gleicher Ablauf wie B (LinkedIn wird übersprungen, da Tecis bereits Stufe + Tel liefert).  
**Endergebnis:** Wie B – Telefon = {aus Tecis}, Stufe = {ungültig}, Zielgruppe = **Out of Scope**, Status = **ungültig**

---

### Szenario F: Tecis da, Stufe gültig, Tel da, LinkedIn nicht, Xing da, Tecis-Eintrag aktuell

| Schritt | Was passiert |
|--------|----------------|
| P1 Tecis | Stufe + Telefon → alles aus Tecis |
| P2/P3/P4 | Übersprungen (Stufe + Tel bereits da) |
| Output | Szenario 1: In Scope, Status leer |

**Endergebnis:** Telefonnummer = {aus Tecis}, Stufe = {Stufe}, Zielgruppe = **In Scope**, Status = **(leer)**

---

### Szenario G: Tecis da, Stufe gültig, Tel nicht, LinkedIn da (ohne Tecis-Eintrag), Xing da, Tecis-Eintrag aktuell

| Schritt | Was passiert |
|--------|----------------|
| P1 Tecis | Stufe (gültig), keine Telefonnummer → stufe_gefunden=True, telefonnummer_gefunden=False |
| P2 LinkedIn | Läuft; „Tecis Eintrag nicht da“ = LinkedIn zeigt keinen Tecis-Eintrag, liefert ggf. Stufe; keine Tel von LinkedIn |
| P3 Xing | Stufe schon da → **übersprungen** |
| P4 Creditreform | Läuft (kein Tel, Stufe da); wenn keine Nummer gefunden → Tel bleibt leer |
| Output | has_telefon=False, has_stufe=True, In Scope → **Szenario 3**: Telefon = **garkeine**, Status **(leer)** |

**Endergebnis:** Telefonnummer = **garkeine**, Stufe = {gültige Stufe}, Zielgruppe = **In Scope**, Status = **(leer)**

---

### Szenario H: Tecis nicht, LinkedIn da, Tecis-Eintrag veraltet

| Schritt | Was passiert |
|--------|----------------|
| P1 Tecis | Keine Tecis-URL → übersprungen |
| P2 LinkedIn | Eintrag **veraltet** (nicht mehr bei Tecis) → `ist_aktiv=False` → **`_set_inactive_status(result)`**: Status = „Wechsel/Nicht mehr in Branche“, Telefon = n/a, Stufe = n/a |
| P3/P4 | Können laufen, result ist bereits auf Szenario 6 gesetzt |
| Output | has_telefon=False (n/a), has_stufe=False (n/a) → Szenario 4/5; Status wird nur gesetzt wenn **nicht** bereits STATUS_WECHSEL → **Wechsel-Status bleibt erhalten** |

**Endergebnis:** Telefonnummer = **n/a**, Stufe = **n/a**, Status = **Wechsel/Nicht mehr in Branche**

---

### Szenario I: Tecis nicht, LinkedIn da, Eintrag aktuell, Stufe gültig, Webseite nicht, Creditreform da, Telefon nicht

| Schritt | Was passiert |
|--------|----------------|
| P1 Tecis | Keine URL → übersprungen |
| P2 LinkedIn | Stufe (gültig) extrahiert, keine Telefonnummer (Webseite nicht vorhanden) → stufe_gefunden=True, telefonnummer_gefunden=False |
| P3 Xing | Stufe da → **übersprungen** |
| P4 Creditreform | Creditreform-URL da → wird ausgeführt; wenn Telefon auf Creditreform gefunden → result.telefonnummer gesetzt; wenn nicht gefunden → bleibt leer |
| Output | **Falls Tel von Creditreform:** has_telefon=True, has_stufe=True → Szenario 1: In Scope, Status leer. **Falls keine Tel:** Szenario 3: Telefon = garkeine, Status leer |

**Endergebnis (ohne Tel von Creditreform):** Telefonnummer = **garkeine**, Stufe = {gültige Stufe}, Zielgruppe = **In Scope**, Status = **(leer)**  
**Endergebnis (mit Tel von Creditreform):** Telefonnummer = {aus Creditreform}, Stufe = {Stufe}, Zielgruppe = **In Scope**, Status = **(leer)**