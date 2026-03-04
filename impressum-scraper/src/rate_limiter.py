"""
Rate-Limiting für den Impressum-Scraper.
Adaptiert aus BK-Automatisierung — vereinfacht für Website-Scraping.
"""

import time
import random
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Einfaches Rate-Limiting:
    - Zufällige Pause zwischen Requests (between_requests_min – between_requests_max Sekunden)
    - Lange Pause nach jeweils N Seiten (pause_after_n_sites × pause_duration Sekunden)
    """

    def __init__(self, config):
        self.config = config
        self.request_count = 0

    def wait_between_requests(self):
        """Schläft eine zufällige Zeit zwischen zwei Requests"""
        min_delay = self.config.get("rate_limits.between_requests_min", 1)
        max_delay = self.config.get("rate_limits.between_requests_max", 3)
        delay = random.uniform(min_delay, max_delay)
        logger.debug(f"Warte {delay:.1f}s vor nächstem Request")
        time.sleep(delay)

    def record_and_maybe_pause(self):
        """
        Zeichnet einen Request auf. Legt nach jeweils N Seiten
        eine längere Pause ein, um Server-Überlastung zu vermeiden.
        """
        self.request_count += 1
        pause_after = self.config.get("rate_limits.pause_after_n_sites", 20)
        pause_duration = self.config.get("rate_limits.pause_duration", 60)

        if self.request_count % pause_after == 0:
            logger.info(
                f"Pause nach {pause_after} Seiten: {pause_duration}s warten..."
            )
            time.sleep(pause_duration)
