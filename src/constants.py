"""
Konstanten und Magic Strings für den Bot
"""

# Status-Werte (Appendix A)
STATUS_WECHSEL = "Wechsel/Nicht mehr in Branche"
STATUS_UNGUELTIG = "ungültig"
STATUS_UNBEKANNT = "Unbekannt"

# Telefonnummer-Werte
TEL_KEINE = "garkeine"
TEL_NA = "n/a"

# Stufe-Werte
STUFE_NA = "n/a"

# LinkedIn Selektoren
LINKEDIN_CONTACT_INFO_BUTTON = "#top-card-text-details-contact-info"
LINKEDIN_CONTACT_INFO_MODAL = 'div[role="dialog"]'

# Xing Selektoren
XING_HEADLINE_ATTR = "data-mds"
XING_HEADLINE_VALUE = "Headline"

# Active Status Keywords
ACTIVE_KEYWORDS_DE = ["heute", "bis heute", "aktuell"]
ACTIVE_KEYWORDS_EN = ["present", "current"]
ACTIVE_KEYWORDS = ACTIVE_KEYWORDS_DE + ACTIVE_KEYWORDS_EN
