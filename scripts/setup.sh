#!/bin/bash
# Quick-Start-Skript für Tecis-Bot

echo "=== Tecis-Bot Setup ==="
echo ""

# 1. Virtual Environment
if [ ! -d "venv" ]; then
    echo "✓ Erstelle Virtual Environment..."
    python3 -m venv venv
else
    echo "✓ Virtual Environment existiert bereits"
fi

# 2. Virtual Environment aktivieren
echo "✓ Aktiviere Virtual Environment..."
source venv/bin/activate

# 3. Dependencies installieren
echo "✓ Installiere Dependencies..."
pip install -q -r requirements.txt

# 4. Playwright installieren
echo "✓ Installiere Playwright Browser..."
playwright install chromium

# 5. .env prüfen
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  .env-Datei fehlt!"
    echo "   Kopiere .env.example nach .env und fülle die Werte aus:"
    echo "   cp .env.example .env"
    echo "   nano .env"
    exit 1
else
    echo "✓ .env-Datei gefunden"
fi

# 6. credentials.json prüfen
if [ ! -f "credentials.json" ]; then
    echo ""
    echo "⚠️  credentials.json fehlt!"
    echo "   Lade Google OAuth Credentials herunter und speichere als credentials.json"
    echo "   Siehe SETUP.md Schritt 3"
    exit 1
else
    echo "✓ credentials.json gefunden"
fi

echo ""
echo "=== Setup abgeschlossen! ==="
echo ""
echo "Bot starten mit:"
echo "  python main.py"
echo ""
echo "Für detaillierte Anleitung siehe SETUP.md"
