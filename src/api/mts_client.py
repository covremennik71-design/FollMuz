# src/api/mts_client.py
import re
import logging
import os
import json
from typing import Optional, Dict
from ..config import config

logger = logging.getLogger(__name__)

class MTSClient:
    """Клиент для поиска и скачивания аудио из MTS Music."""
    
    MTS_PATTERNS = [
        r'music\.mts\.ru',
        r'mts\.ru/music',
        r'stream\.mts\.ru',
    ]
    
    def __init__(self):
        self.session = None
        self.api_base = "https://music.mts.ru/api/v1"
    
    def is_mts_url(self, url: str) -> bool:
        """Проверяет, является ли ссылка ссылкой на MTS Music."""
        for pattern in self.MTS_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False
    
    def get_session(self):
        if self.session is None:
            import requests
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            })
        return self.session
    
    def extract_track_info(self, url: str) -> Optional[Dict]:
        """Извлекает информацию о треке из MTS Music ссылки."""
        try:
            session = self.get_session()
            
            track_id = self._extract_track_id(url)
            if track_id:
                return self._fetch_track_info(track_id)
            
            # Пробуем распарсить как search URL
            artist, title = self._parse_url(url)
            if artist and title:
                return {
                    'artist': artist,
                    'title': title,
                    'url': url,
                    'source': 'mts'
                }
            
            return None
        except Exception as e:
            logger.error(f"Ошибка извлечения MTS трека: {e}")
            return None
    
    def _extract_track_id(self, url: str) -> Optional[str]:
        """Извлекает ID трека из URL."""
        patterns = [
            r'/track/(\d+)',
            r'track[_-]?id[=:]?(\d+)',
            r'id=(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _parse_url(self, url: str) -> tuple:
        """Парсит artist/title из URL."""
        try:
            response = self.get_session().get(url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                html = response.text
                
                artist_match = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
                title_match = re.search(r'<meta[^>]+property="music:musician"[^>]+content="([^"]+)"', html)
                
                if artist_match and title_match:
                    return title_match.group(1), artist_match.group(1)
                
                og_title = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
                if og_title:
                    full = og_title.group(1)
                    if ' - ' in full:
                        parts = full.split(' - ', 1)
                        return parts[0].strip(), parts[1].strip()
        except Exception as e:
            logger.debug(f"Не удалось распарсить URL: {e}")
        
        return None, None
    
    def _fetch_track_info(self, track_id: str) -> Optional[Dict]:
        """Получает информацию о треке по ID."""
        try:
            session = self.get_session()
            
            response = session.get(
                f"{self.api_base}/track/{track_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'artist': data.get('artist', {}).get('name', 'Unknown'),
                    'title': data.get('title', 'Unknown'),
                    'url': data.get('stream_url', data.get('preview_url', '')),
                    'duration': data.get('duration', 0),
                    'source': 'mts'
                }
            
            return None
        except Exception as e:
            logger.debug(f"Не удалось получить информацию о треке: {e}")
            return None
    
    def search_track(self, artist: str, title: str) -> Optional[Dict]:
        """Поиск трека на MTS Music."""
        try:
            session = self.get_session()
            
            query = f"{artist} {title}"
            encoded_query = query.replace(' ', '%20')
            
            response = session.get(
                f"{self.api_base}/search",
                params={'q': encoded_query, 'type': 'track', 'limit': 10},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                tracks = data.get('tracks', {}).get('items', [])
                
                best_match = None
                best_score = 0
                
                for track in tracks:
                    track_artist = track.get('artist', {}).get('name', '')
                    track_title = track.get('title', '')
                    
                    score = 0
                    if artist.lower() in track_artist.lower():
                        score += 5
                    if title.lower() in track_title.lower():
                        score += 5
                    
                    if score > best_score:
                        best_score = score
                        best_match = {
                            'artist': track_artist,
                            'title': track_title,
                            'url': track.get('stream_url', track.get('preview_url', '')),
                            'duration': track.get('duration', 0),
                            'source': 'mts'
                        }
                
                return best_match if best_score > 0 else None
            
            return None
        except Exception as e:
            logger.debug(f"Ошибка поиска MTS: {e}")
            return None
    
    def download_track(self, track_info: Dict, output_path: str) -> Optional[str]:
        """Скачивает трек с MTS Music."""
        try:
            url = track_info.get('url')
            if not url:
                logger.warning("MTS: нет URL для скачивания")
                return None
            
            session = self.get_session()
            artist = track_info.get('artist', 'Unknown')
            title = track_info.get('title', 'Unknown')
            
            from ..utils import sanitize_filename
            safe_artist = sanitize_filename(artist)
            safe_title = sanitize_filename(title)
            filename = f"{safe_artist} - {safe_title}.mp3"
            filepath = os.path.join(output_path, filename)
            
            response = session.get(url, timeout=60, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Скачано из MTS: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Ошибка скачивания MTS: {e}")
            return None
