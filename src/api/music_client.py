# src/api/music_client.py
import re
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class MusicClient:
    """Универсальный клиент для работы с различными музыкальными сервисами."""
    
    PATTERNS = {
        'spotify': [r'open\.spotify\.com/track/', r'spotify\.com/track/'],
        'yandex': [r'music\.yandex\.ru/album/', r'music\.yandex\.com/album/'],
        'mts': [r'music\.mts\.ru/track/']
    }
    
    def __init__(self):
        # Инициализация других клиентов если нужно
        pass
    
    def get_service(self, url: str) -> Optional[str]:
        for service, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return service
        return None

    def extract_info(self, url: str) -> Optional[Dict]:
        """Извлекает информацию о треке в зависимости от сервиса."""
        service = self.get_service(url)
        
        if service == 'spotify':
            # Логика из старого spotify_client.py
            from src.api.spotify_client import SpotifyClient
            return SpotifyClient().extract_track_info(url)
            
        elif service in ['yandex', 'mts']:
            # Используем yt-dlp для Yandex Music и MTS Music, 
            # так как они поддерживаются yt-dlp
            return self._extract_via_ytdlp(url, service)
            
        return None

    def _extract_via_ytdlp(self, url: str, service: str) -> Optional[Dict]:
        try:
            import subprocess
            import json
            import os
            ytdlp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".venv", "Scripts", "yt-dlp.exe")
            
            # yt-dlp отлично справляется с Yandex Music и MTS Music
            result = subprocess.run([ytdlp_path, "-j", url], capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                
                # Попытка извлечь артиста и название
                artist = data.get('artist') or data.get('uploader')
                title = data.get('track') or data.get('title')
                
                return {
                    'artist': artist or "Unknown",
                    'title': title or "Unknown",
                    'url': url,
                    'source': service
                }
        except Exception as e:
            logger.error(f"Ошибка получения данных с {service} через yt-dlp: {e}")
        return None
