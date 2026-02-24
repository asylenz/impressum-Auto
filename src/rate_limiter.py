"""
Rate Limiting für verschiedene Plattformen
"""

import time
import logging
import random
from datetime import datetime, timedelta
from typing import Dict
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate Limiter mit Tages- und Stunden-Limits"""
    
    def __init__(self, config):
        self.config = config
        self.state_file = Path("rate_limiter_state.json")
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """Lädt den gespeicherten Zustand"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            'linkedin': {'daily': 0, 'hourly': 0, 'day_window_start': None, 'last_reset_hour': None, 'last_request': None},
            'xing': {'hourly': 0, 'last_reset_hour': None, 'last_request': None},
            'tecis': {'last_request': None},
            'creditreform': {'last_request': None},
            'google_search': {'last_request': None}
        }
    
    def _save_state(self):
        """Speichert den aktuellen Zustand"""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _reset_if_needed(self, platform: str):
        """Setzt Counter zurück, wenn nötig"""
        now = datetime.now()
        state = self.state.get(platform, {})
        
        # Tages-Reset (nur LinkedIn) - 24h-Fenster
        if platform == 'linkedin':
            day_window_start = state.get('day_window_start')
            
            # Wenn kein Fenster existiert oder 24h abgelaufen sind
            if not day_window_start:
                # Neues Fenster starten
                state['daily'] = 0
                state['day_window_start'] = now.isoformat()
                logger.info(f"LinkedIn 24h-Fenster gestartet")
            else:
                window_start_time = datetime.fromisoformat(day_window_start)
                elapsed = now - window_start_time
                
                # Wenn 24h abgelaufen sind, neues Fenster starten
                if elapsed >= timedelta(hours=24):
                    state['daily'] = 0
                    state['day_window_start'] = now.isoformat()
                    logger.info(f"LinkedIn 24h-Fenster zurückgesetzt (24h abgelaufen)")
        
        # Stunden-Reset
        if platform in ['linkedin', 'xing']:
            last_hour = state.get('last_reset_hour')
            if not last_hour or datetime.fromisoformat(last_hour).hour != now.hour:
                state['hourly'] = 0
                state['last_reset_hour'] = now.isoformat()
                logger.debug(f"{platform.capitalize()} Stundenlimit zurückgesetzt")
        
        self.state[platform] = state
        self._save_state()
    
    def can_proceed(self, platform: str) -> bool:
        """Prüft, ob Request erlaubt ist"""
        self._reset_if_needed(platform)
        state = self.state.get(platform, {})
        
        # LinkedIn: Tages- und Stundenlimits prüfen
        if platform == 'linkedin':
            daily_limit = self.config.get_limit('linkedin', 'max_profiles_per_day', 50)
            
            if state.get('daily', 0) >= daily_limit:
                logger.warning(f"LinkedIn Tageslimit erreicht: {daily_limit}")
                return False
        
        # Xing: Stundenlimit prüfen
        if platform == 'xing':
            hourly_limit = self.config.get_limit('xing', 'max_profiles_per_hour', 30)
            
            if state.get('hourly', 0) >= hourly_limit:
                logger.warning(f"Xing Stundenlimit erreicht: {hourly_limit}")
                return False
        
        return True
    
    def get_time_until_reset(self, platform: str) -> dict:
        """
        Berechnet die verbleibende Zeit bis zum Reset des Tageslimits
        
        Returns:
            dict mit 'hours', 'minutes', 'reset_time' (datetime), 'current_count', 'limit'
        """
        state = self.state.get(platform, {})
        
        if platform == 'linkedin':
            day_window_start = state.get('day_window_start')
            daily_limit = self.config.get_limit('linkedin', 'max_profiles_per_day', 150)
            current_count = state.get('daily', 0)
            
            if not day_window_start:
                return {
                    'hours': 0,
                    'minutes': 0,
                    'reset_time': None,
                    'current_count': current_count,
                    'limit': daily_limit,
                    'is_blocked': False
                }
            
            window_start_time = datetime.fromisoformat(day_window_start)
            reset_time = window_start_time + timedelta(hours=24)
            now = datetime.now()
            
            if now >= reset_time:
                # Fenster ist bereits abgelaufen
                return {
                    'hours': 0,
                    'minutes': 0,
                    'reset_time': reset_time,
                    'current_count': current_count,
                    'limit': daily_limit,
                    'is_blocked': False
                }
            
            time_remaining = reset_time - now
            hours = int(time_remaining.total_seconds() // 3600)
            minutes = int((time_remaining.total_seconds() % 3600) // 60)
            
            return {
                'hours': hours,
                'minutes': minutes,
                'reset_time': reset_time,
                'current_count': current_count,
                'limit': daily_limit,
                'is_blocked': current_count >= daily_limit
            }
        
        return {
            'hours': 0,
            'minutes': 0,
            'reset_time': None,
            'current_count': 0,
            'limit': 0,
            'is_blocked': False
        }
    
    def wait_if_needed(self, platform: str):
        """Wartet zwischen Requests basierend auf konfiguriertem Delay"""
        state = self.state.get(platform, {})
        last_request = state.get('last_request')
        
        if last_request:
            last_time = datetime.fromisoformat(last_request)
            elapsed = (datetime.now() - last_time).total_seconds()
            
            # Delay-Range aus Config holen
            min_delay = self.config.get_limit(platform, 'delay_between_requests_min', 1)
            max_delay = self.config.get_limit(platform, 'delay_between_requests_max', 3)
            
            # Zufälligen Delay wählen
            required_delay = random.uniform(min_delay, max_delay)
            
            if elapsed < required_delay:
                wait_time = required_delay - elapsed
                logger.debug(f"Warte {wait_time:.1f}s vor nächstem {platform} Request")
                time.sleep(wait_time)
    
    def record_request(self, platform: str):
        """Zeichnet einen Request auf"""
        self._reset_if_needed(platform)
        state = self.state.get(platform, {})
        
        # Counter erhöhen
        if platform == 'linkedin':
            state['daily'] = state.get('daily', 0) + 1
            state['hourly'] = state.get('hourly', 0) + 1
            
            # Pause nach N Profilen?
            pause_after = self.config.get_limit('linkedin', 'pause_after_n_profiles', 20)
            if state['hourly'] % pause_after == 0 and state['hourly'] > 0:
                pause_duration = self.config.get_limit('linkedin', 'pause_duration', 300)
                logger.info(f"Pause nach {pause_after} LinkedIn-Profilen: {pause_duration}s")
                time.sleep(pause_duration)
        
        if platform == 'xing':
            state['hourly'] = state.get('hourly', 0) + 1
        
        # Letzte Request-Zeit speichern
        state['last_request'] = datetime.now().isoformat()
        
        self.state[platform] = state
        self._save_state()
        
        logger.debug(f"{platform}: Request aufgezeichnet (daily={state.get('daily', 'N/A')}, hourly={state.get('hourly', 'N/A')})")
    
    def acquire(self, platform: str):
        """Wartet und prüft, ob Request erlaubt ist; wirft Exception bei Limit"""
        if not self.can_proceed(platform):
            time_info = self.get_time_until_reset(platform)
            raise RateLimitExceeded(
                platform=platform,
                message=f"{platform} Rate-Limit erreicht",
                time_until_reset=time_info.get('reset_time'),
                current_count=time_info.get('current_count', 0),
                limit=time_info.get('limit', 0),
                hours_remaining=time_info.get('hours', 0),
                minutes_remaining=time_info.get('minutes', 0)
            )
        
        self.wait_if_needed(platform)
        self.record_request(platform)

class RateLimitExceeded(Exception):
    """Exception wenn Rate-Limit erreicht ist"""
    
    def __init__(self, platform: str, message: str, time_until_reset=None, 
                 current_count: int = 0, limit: int = 0, 
                 hours_remaining: int = 0, minutes_remaining: int = 0):
        super().__init__(message)
        self.platform = platform
        self.time_until_reset = time_until_reset
        self.current_count = current_count
        self.limit = limit
        self.hours_remaining = hours_remaining
        self.minutes_remaining = minutes_remaining
    
    def get_formatted_message(self) -> str:
        """Gibt eine benutzerfreundliche formatierte Nachricht zurück"""
        lines = [
            "",
            "=" * 80,
            f"⚠️  {self.platform.upper()} TAGESLIMIT ERREICHT",
            "=" * 80,
            f"Limit:           {self.limit} Anfragen pro 24 Stunden",
            f"Aktuell:         {self.current_count} verwendet",
        ]
        
        if self.time_until_reset:
            reset_str = self.time_until_reset.strftime("%d.%m.%Y %H:%M Uhr")
            window_start = self.time_until_reset - timedelta(hours=24)
            window_start_str = window_start.strftime("%d.%m.%Y %H:%M Uhr")
            
            lines.extend([
                f"Fenster Start:   {window_start_str}",
                f"Fenster Ende:    {reset_str}",
                "",
                f"⏳ Noch {self.hours_remaining} Stunden und {self.minutes_remaining} Minuten bis zur Freigabe",
                "",
                f"Der Bot wird jetzt beendet. Bitte starten Sie ihn nach {reset_str} erneut.",
            ])
        
        lines.append("=" * 80)
        return "\n".join(lines)
