# src/api/spotify_client.py
import re
import logging
import os
import requests
from urllib.parse import quote
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class SpotifyClient:
    """Клиент для извлечения информации о треках из Spotify."""
    
    SPOTIFY_PATTERNS = [
        r'open\.spotify\.com/track/',
        r'open\.spotify\.com/album/',
        r'open\.spotify\.com/playlist/',
        r'open\.spotify\.com/artist/',
        r'spotify\.com/track/',
        r'spotify\.com/album/',
        r'spotify\.com/playlist/',
    ]
    
    def __init__(self):
        self.session = None
        self._client = None
    
    def is_spotify_url(self, url: str) -> bool:
        """Проверяет, является ли ссылка ссылкой на Spotify."""
        for pattern in self.SPOTIFY_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False
    
    def get_session(self):
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
        return self.session
    
    def _get_scraper(self):
        """Получает экземпляр SpotifyClient из spotify_scraper."""
        if self._client is not None:
            return self._client
        
        try:
            from spotify_scraper import SpotifyClient as _SpotifyClient
            self._client = _SpotifyClient()
            return self._client
        except ImportError:
            logger.warning("spotify_scraper не установлен")
            return None
        except Exception as e:
            logger.warning(f"Ошибка инициализации spotify_scraper: {e}")
            return None
    
    def extract_track_info(self, url: str) -> Optional[Dict]:
        """Извлекает информацию о треке из Spotify ссылки."""
        try:
            # Извлекаем ID из URL
            patterns = [
                r'open\.spotify\.com/track/([a-zA-Z0-9]+)',
                r'spotify\.com/track/([a-zA-Z0-9]+)',
            ]
            
            track_id = None
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    track_id = match.group(1)
                    break
            
            if not track_id:
                return None
            
            # Способ 1: Через spotify_scraper
            scraper = self._get_scraper()
            if scraper:
                try:
                    track_url = f"https://open.spotify.com/track/{track_id}"
                    track = scraper.get_track_info(track_url)
                    if track:
                        artists = track.get('artists', [])
                        artist = artists[0].get('name', 'Unknown') if artists else 'Unknown'
                        title = track.get('name', 'Unknown')
                        
                        if artist != 'Unknown' and title != 'Unknown':
                            return {
                                'artist': artist,
                                'title': title,
                                'album': track.get('album', {}).get('name', ''),
                                'url': url,
                                'source': 'spotify',
                                'track_id': track_id
                            }
                except Exception as e:
                    logger.warning(f"spotify_scraper.get_track не сработал: {e}")
            
            # Способ 2: Через веб-скрапинг (embed URL)
            try:
                embed_url = f"https://open.spotify.com/embed/track/{track_id}"
                response = self.get_session().get(embed_url, timeout=10)
                if response.status_code == 200:
                    # Ищем JSON в HTML
                    import json
                    json_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', response.text, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group(1))
                        track_data = data.get('props', {}).get('pageProps', {}).get('track', {})
                        if track_data:
                                artist = track_data.get('artists', [{}])[0].get('name')
                                title = track_data.get('name')
                                if not artist or not title or artist == 'Unknown' or title == 'Unknown':
                                    return None
                                return {
                                    'artist': artist,
                                    'title': title,
                                    'album': track_data.get('album', {}).get('name', ''),
                                    'url': url,
                                    'source': 'spotify',
                                    'track_id': track_id
                                }

            except Exception as e:
                logger.warning(f"Веб-скрапинг Spotify embed не сработал: {e}")
            
            # Способ 3: Через og:title meta tag
            try:
                response = self.get_session().get(url, timeout=10)
                if response.status_code == 200:
                    title_match = re.search(r'<meta property="og:title" content="([^"]+)"', response.text)
                    if title_match:
                        full_title = title_match.group(1)
                        if ' - ' in full_title:
                            artist, title = full_title.split(' - ', 1)
                        else:
                            return None
                        
                        return {
                            'artist': artist.strip(),
                            'title': title.strip(),
                            'url': url,
                            'source': 'spotify',
                            'track_id': track_id
                        }
            except Exception as e:
                logger.warning(f"Веб-скрапинг og:title не сработал: {e}")
            
            # Способ 4: Fallback через yt-dlp
            try:
                import subprocess
                import json
                ytdlp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".venv", "Scripts", "yt-dlp.exe")
                result = subprocess.run([ytdlp_path, "-j", url], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    artist = data.get('artist') or data.get('uploader')
                    title = data.get('track') or data.get('title')
                    if artist and title:
                        return {
                            'artist': artist,
                            'title': title,
                            'url': url,
                            'source': 'spotify',
                            'track_id': track_id
                        }
            except Exception as e:
                logger.warning(f"yt-dlp fallback не сработал: {e}")
            
            return None
        except Exception as e:
            logger.error(f"Ошибка извлечения Spotify трека: {e}")
            return None
    
    def extract_playlist_info(self, url: str) -> Optional[Dict]:
        """Извлекает информацию о плейлисте из Spotify."""
        try:
            playlist_match = re.search(r'open\.spotify\.com/playlist/([a-zA-Z0-9]+)', url)
            if not playlist_match:
                return None
            
            playlist_id = playlist_match.group(1)
            
            # Через spotify_scraper
            scraper = self._get_scraper()
            if scraper:
                try:
                    playlist_url = f"https://open.spotify.com/playlist/{playlist_id}"
                    playlist = scraper.get_playlist_info(playlist_url)
                    if playlist:
                        tracks_data = playlist.get('tracks', {})
                        items = tracks_data.get('items', []) if isinstance(tracks_data, dict) else []
                        tracks = []
                        for track in items:
                            artists = track.get('artists', [])
                            artist = artists[0].get('name', '') if artists else ''
                            title = track.get('name', '')
                            if artist and title:
                                tracks.append({
                                    'artist': artist,
                                    'title': title,
                                    'source': 'spotify'
                                })
                        
                        return {
                            'name': playlist.get('name', ''),
                            'tracks': tracks,
                            'url': url,
                            'source': 'spotify'
                        }
                except Exception as e:
                    logger.warning(f"spotify_scraper.get_playlist не сработал: {e}")
            
            return None
        except Exception as e:
            logger.error(f"Ошибка извлечения Spotify плейлиста: {e}")
            return None
    
    def search_track(self, artist: str, title: str) -> Optional[Dict]:
        """Поиск трека в Spotify через веб-скрапинг."""
        try:
            query = f"{artist} {title}"
            encoded_query = quote(query)
            search_url = f"https://open.spotify.com/search/{encoded_query}/tracks"
            
            response = self.get_session().get(search_url, timeout=10)
            if response.status_code != 200:
                return None
            
            import json
            json_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', response.text, re.DOTALL)
            if not json_match:
                return None
            
            data = json.loads(json_match.group(1))
            tracks_data = data.get('props', {}).get('pageProps', {}).get('contents', {})
            items = tracks_data.get('items', [])
            
            if not items:
                return None
            
            best_match = None
            best_score = 0
            
            for item in items:
                data_obj = item.get('data', {})
                if data_obj.get('__typename') != 'Track':
                    continue
                
                track_artists = data_obj.get('artists', {}).get('items', [])
                track_artist = track_artists[0].get('profile', {}).get('name', '') if track_artists else ''
                track_title = data_obj.get('name', '')
                
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
                        'url': f"https://open.spotify.com/track/{data_obj.get('id', '')}",
                        'source': 'spotify'
                    }
            
            return best_match
        except Exception as e:
            logger.error(f"Ошибка поиска Spotify: {e}")
            return None
