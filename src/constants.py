"""
Konstanten und Magic Strings für den Tecis-Bot
"""

# Status-Werte (Appendix A)
STATUS_WECHSEL = "Nicht mehr in Branche"
STATUS_UNGUELTIG = "ungültig"
STATUS_UNBEKANNT = "Unbekannt"

# Telefonnummer-Werte
TEL_KEINE = "garkeine"
TEL_NA = "n/a"

# Stufe-Werte
STUFE_NA = "n/a"

# Zielgruppen-Kategorisierung (Appendix B)
# In Scope = Primäre Zielgruppe (gültig)
STUFEN_IN_SCOPE = [
    "Sales Consultant",
    "Senior Sales Consultant",
    "Sales Manager",
    "Senior Sales Manager",
    "Seniorberater",
    "Teamleiter",
    "Repräsentanzleiter",
    "Branch Manager",
    "Regional Manager",
    "General Sales Manager",
]

# Out of Scope = Nicht Zielgruppe (bekannte Stufen, aber ungültig)
STUFEN_OUT_OF_SCOPE = [
    "Divisional Manager",
    "General Manager",
    "Juniorberater",
    "Beraterassistent",
    "Trainee",
]

# LinkedIn Selektoren
LINKEDIN_CONTACT_INFO_BUTTON = "#top-card-text-details-contact-info"
LINKEDIN_CONTACT_INFO_MODAL = 'div[role="dialog"]'

# Xing Selektoren
XING_HEADLINE_ATTR = "data-mds"
XING_HEADLINE_VALUE = "Headline"

# Tecis Selektoren
TECIS_TITLE_CLASS = ".personal-information__title"
TECIS_CONTACT_LINKS = 'div.contacts-columns a[href^="tel:"]'

# Active Status Keywords
ACTIVE_KEYWORDS_DE = ["heute", "bis heute", "aktuell"]
ACTIVE_KEYWORDS_EN = ["present", "current"]
ACTIVE_KEYWORDS = ACTIVE_KEYWORDS_DE + ACTIVE_KEYWORDS_EN

# URL-Konstruktion
TECIS_KONTAKT_SUFFIX = "/kontaktuebersicht.html"
TECIS_IMPRESSUM_SUFFIX = "/impressum.html"
