# Zielgruppen-Kategorisierung - Tecis Stufen

## ✅ In Scope (Primäre Zielgruppe)

Diese Stufen sind die **Hauptzielgruppe** und werden als **gültig** eingestuft:

| Nr. | Stufe | Status |
|-----|-------|--------|
| 1 | 🟢 Sales Consultant | ✓ Gültig |
| 2 | 🟢 Senior Sales Consultant | ✓ Gültig |
| 3 | 🟢 Sales Manager | ✓ Gültig |
| 4 | 🟢 Senior Sales Manager | ✓ Gültig |
| 5 | 🟢 Seniorberater | ✓ Gültig |
| 6 | 🟢 Teamleiter | ✓ Gültig |
| 7 | 🟢 Repräsentanzleiter | ✓ Gültig |
| 8 | 🟢 Branch Manager | ✓ Gültig |
| 9 | 🟢 Regional Manager | ✓ Gültig |
| 10 | 🟢 General Sales Manager | ✓ Gültig |

**Gesamt: 10 Stufen**

---

## ⚠️ Out of Scope (Nicht Zielgruppe)

Diese Stufen sind **nicht Teil der Zielgruppe** und führen zu Status **"ungültig"**:

| Nr. | Stufe | Status |
|-----|-------|--------|
| 1 | 🟠 Divisional Manager | ✗ Ungültig |
| 2 | 🟠 General Manager | ✗ Ungültig |
| 3 | 🟠 Juniorberater | ✗ Ungültig |
| 4 | 🟠 Beraterassistent | ✗ Ungültig |
| 5 | 🟠 Trainee | ✗ Ungültig |

**Gesamt: 5 Stufen**

---

## Bot-Verhalten

### Wenn "In Scope" Stufe gefunden:
- ✅ Stufe wird eingetragen
- ✅ Status bleibt leer (außer bei "Wechsel")
- ✅ Lead wird als valide Zielgruppe markiert

### Wenn "Out of Scope" Stufe gefunden:
- ⚠️ Stufe wird NICHT eingetragen (→ `n/a`)
- ⚠️ Status wird auf **"ungültig"** gesetzt
- ⚠️ Lead wird als nicht-zielgruppenrelevant markiert

### Beispiele:

**Beispiel 1: Sales Manager (In Scope)**
```
Telefonnummer: +49 123 456789
Stufe: Sales Manager
Status: (leer)
```

**Beispiel 2: Trainee (Out of Scope)**
```
Telefonnummer: +49 123 456789
Stufe: n/a
Status: ungültig
```

**Beispiel 3: Divisional Manager (Out of Scope)**
```
Telefonnummer: +49 123 456789
Stufe: n/a
Status: ungültig
```

---

## Konfiguration

Die Whitelist befindet sich in:
- **`config.yaml`** → `valid_stufen`
- **`Abwerbe Automatisierung.md`** → Appendix B

Bei Änderungen beide Dateien synchron halten!
