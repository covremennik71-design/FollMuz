import logging
import re
from typing import Dict, List, Optional

from src.config import config

logger = logging.getLogger(__name__)


class PlaylistParser:
    def __init__(self):
        self._spotify_client = None
        self._spotify_session = None

    def _get_spotify_client(self):
        """Ленивая инициализация Spotify клиента."""
        if self._spotify_client is None:
            try:
                from spotify_scraper import SpotifyClient

                self._spotify_client = SpotifyClient()
                logger.info("SpotifyScraper initialized")
            except ImportError:
                logger.warning("SpotifyScraper is not installed. Install with: pip install spotifyscraper")
                return None
        return self._spotify_client

    def _get_spotify_session(self):
        if self._spotify_session is None:
            import requests
            self._spotify_session = requests.Session()
        return self._spotify_session

    def _extract_spotify_playlist_id(self, url: str) -> Optional[str]:
        match = re.search(r'(?:playlist/|spotify:playlist:)([A-Za-z0-9]+)', url)
        return match.group(1) if match else None

    def _get_spotify_access_token(self) -> Optional[str]:
        try:
            response = self._get_spotify_session().get(
                'https://open.spotify.com/get_access_token',
                params={'reason': 'transport', 'productType': 'web_player'},
                timeout=5,
            )
            if response.ok:
                data = response.json()
                return data.get('accessToken')
        except Exception as error:
            logger.error(f"Spotify token error: {error}")
        return None

    def _fetch_spotify_playlist_api(self, url: str) -> Optional[List[Dict]]:
        playlist_id = self._extract_spotify_playlist_id(url)
        if not playlist_id:
            return None

        token = self._get_spotify_access_token()
        if not token:
            return None

        session = self._get_spotify_session()
        headers = {'Authorization': f'Bearer {token}'}
        offset = 0
        limit = 100
        tracks = []

        while True:
            response = session.get(
                f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks',
                headers=headers,
                params={
                    'limit': limit,
                    'offset': offset,
                    'fields': 'items(track(name,artists(name))),total,next',
                },
                timeout=8,
            )
            if not response.ok:
                return None

            data = response.json()
            items = data.get('items', [])
            for item in items:
                track = item.get('track') or {}
                artists = track.get('artists') or [{}]
                tracks.append({
                    'artist': artists[0].get('name', 'Unknown'),
                    'title': track.get('name', 'Unknown'),
                    'modification': '',
                })

            offset += len(items)
            total = data.get('total', 0)
            if offset >= total or not items:
                break

        return tracks or None

    def parse(self, url: str) -> Optional[List[Dict]]:
        url = (url or "").strip()
        if not url:
            return None

        if "spotify.com" in url:
            return self._parse_spotify(url)
        if "vk.com" in url and "audio" in url:
            return self._parse_vk(url)
        if "youtube.com" in url or "youtu.be" in url:
            return self._parse_youtube(url)
        if "music.yandex.ru" in url:
            logger.warning("Yandex Music is not supported")
            return None
        return None

    def _parse_spotify(self, url: str) -> Optional[List[Dict]]:
        api_tracks = self._fetch_spotify_playlist_api(url)
        if api_tracks:
            print(f"✓ Найдено {len(api_tracks)} треков в плейлисте")
            return api_tracks

        client = self._get_spotify_client()
        if not client:
            print("⚠ SpotifyScraper не установлен. Установите: pip install spotifyscraper")
            return None

        try:
            playlist_info = client.get_playlist_info(url)
            tracks = []
            tracks_data = playlist_info.get("tracks", {})
            items = tracks_data.get("items", []) if isinstance(tracks_data, dict) else tracks_data
            for track in items:
                track_data = track.get("data") or track.get("track") or {}
                artists = track_data.get("artists") or [{}]
                artist_name = ""
                for artist in artists:
                    if isinstance(artist, dict):
                        artist_name = artist.get("name", artist.get("profile", {}).get("name", "Unknown"))
                        if artist_name:
                            break
                    elif isinstance(artist, str):
                        artist_name = artist
                        break
                if not artist_name:
                    artist_name = "Unknown"
                title = track_data.get("name", "Unknown")
                if artist_name and title and artist_name != "Unknown":
                    tracks.append({
                        "artist": artist_name,
                        "title": title,
                        "modification": "",
                    })

            print(f"✓ Найдено {len(tracks)} треков в плейлисте")
            return tracks
        except Exception as error:
            logger.error(f"Ошибка парсинга Spotify: {error}")
            return None
        finally:
            if client:
                try:
                    client.close()
                except Exception:
                    pass
                self._spotify_client = None

    def _parse_vk(self, url: str) -> Optional[List[Dict]]:
        try:
            import vk_api

# Removed VK usage
            if not token:
                logger.error("VK token is missing")
                return None

            vk_session = vk_api.VkApi(token=token)
            vk = vk_session.get_api()

            match = re.search(r'audios([\-\d]+).*playlists_(\d+)', url)
            tracks: List[Dict] = []
            if match:
                owner_id = int(match.group(1))
                playlist_id = int(match.group(2))
                offset = 0
                while True:
                    audios = vk.audio.get(owner_id=owner_id, playlist_id=playlist_id, count=100, offset=offset)
                    items = audios.get("items", [])
                    if not items:
                        break
                    for audio in items:
                        tracks.append({
                            "artist": audio.get("artist", "Unknown"),
                            "title": audio.get("title", "Unknown"),
                            "modification": "",
                        })
                    offset += len(items)
                    if len(items) < 100:
                        break
                return tracks
            else:
                owner_match = re.search(r'audios([\-\d]+)', url)
                if not owner_match:
                    return None
                owner_id = int(owner_match.group(1))
                offset = 0
                while True:
                    audios = vk.audio.get(owner_id=owner_id, count=100, offset=offset)
                    items = audios.get("items", [])
                    if not items:
                        break
                    for audio in items:
                        tracks.append({
                            "artist": audio.get("artist", "Unknown"),
                            "title": audio.get("title", "Unknown"),
                            "modification": "",
                        })
                    offset += len(items)
                    if len(items) < 100:
                        break
                return tracks
        except ModuleNotFoundError:
            logger.error("vk-api is not installed")
        except Exception as error:
            logger.error(f"VK error: {error}")
        return None

    def _parse_youtube(self, url: str) -> Optional[List[Dict]]:
        """Получение всех треков из YouTube плейлиста с пагинацией."""
        try:
            import yt_dlp

            ydl_opts = {
                "quiet": True,
                "extract_flat": True,
                "force_generic_extractor": False,
                "skip_download": True,
                "ignoreerrors": True,
                "extractor_args": {
                    "youtube": {
                        "player_client": ["android", "web"],
                    }
                },
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            tracks = []
            entries = info.get("entries") if isinstance(info, dict) else None
            if entries:
                for entry in entries:
                    if not entry:
                        continue
                    tracks.append(self._normalize_track(entry))
            elif isinstance(info, dict):
                tracks.append(self._normalize_track(info))

            print(f"✅ Найдено {len(tracks)} треков в плейлисте")
            return tracks or None
        except Exception as error:
            logger.error(f"YouTube error: {error}")
            return None

    def _normalize_track(self, info: Dict) -> Dict:
        uploader = info.get("uploader") or info.get("channel") or "Unknown"
        title = info.get("title") or "Unknown"

        parts = re.split(r"\s+-\s+", title, maxsplit=1)
        if len(parts) == 2 and parts[0] and parts[1]:
            artist, normalized_title = parts[0].strip(), parts[1].strip()
            if artist and normalized_title:
                return {"artist": artist, "title": normalized_title, "modification": ""}

        return {"artist": uploader.strip(), "title": title.strip(), "modification": ""}
