# src/api/musicbrainz_client.py
import requests
import time
import json
import sqlite3
from difflib import SequenceMatcher
from ..logger_config import LoggerMixin
from ..constants import MUSICBRAINZ_URL, USER_AGENT
from ..exceptions import NetworkError, MetadataError
from ..database import get_db

def fuzzy_match(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def exact_match(a: str, b: str) -> bool:
    if not a or not b:
        return False
    return a.strip().lower() == b.strip().lower()

def musicbrainz_match_score(query, candidate) -> float:
    score = 0.0
    q_artist = getattr(query, 'artist_hint', '') or getattr(query, 'artist', '') or ''
    q_title = getattr(query, 'title_hint', '') or getattr(query, 'title', '') or ''
    q_year = getattr(query, 'year_hint', None)
    q_duration = getattr(query, 'duration_ms', None)

    c_artist = candidate.get('artist', '')
    c_title = candidate.get('title', '')
    c_year = candidate.get('year')
    c_length = candidate.get('length_ms')

    if exact_match(q_artist, c_artist):
        score += 0.40
    elif fuzzy_match(q_artist, c_artist) > 0.85:
        score += 0.25

    if exact_match(q_title, c_title):
        score += 0.40
    elif fuzzy_match(q_title, c_title) > 0.85:
        score += 0.25

    if q_year and c_year and int(q_year) == int(c_year):
        score += 0.10

    if q_duration and c_length:
        diff = abs(int(q_duration) - int(c_length))
        if diff < 5000:
            score += 0.10

    return min(score, 1.0)

class MusicBrainzClient(LoggerMixin):
    _last_request_time = 0.0

    def __init__(self):
        self.base_url = MUSICBRAINZ_URL
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'application/json'
        })
        self.logger.info("MusicBrainzClient инициализирован с расширенным кэшированием и rate-limiter")

    def _rate_limit(self):
        elapsed = time.time() - MusicBrainzClient._last_request_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        MusicBrainzClient._last_request_time = time.time()

    def _get_cache(self, key: str):
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT data, expires_at FROM api_cache WHERE cache_key = ?", (key,))
            row = cursor.fetchone()
            conn.close()
            if row:
                data, expires_at = row
                if time.time() < expires_at:
                    return json.loads(data)
        except Exception as e:
            self.logger.error(f"Cache read error: {e}")
        return None

    def _set_cache(self, key: str, data, ttl: int = 86400 * 30):
        try:
            conn = get_db()
            cursor = conn.cursor()
            expires_at = time.time() + ttl
            cursor.execute(
                "INSERT OR REPLACE INTO api_cache (cache_key, data, expires_at) VALUES (?, ?, ?)",
                (key, json.dumps(data, ensure_ascii=False), expires_at)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Cache write error: {e}")

    def _make_request(self, endpoint, params=None, retry=3):
        cache_key = f"mb:{endpoint}:{str(params)}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        url = f"{self.base_url}/{endpoint}"
        for attempt in range(retry):
            try:
                self._rate_limit()
                response = self.session.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    self._set_cache(cache_key, data)
                    return data
                elif response.status_code == 503:
                    self.logger.warning(f"MusicBrainz 503, попытка {attempt+1}/{retry}")
                    time.sleep(2 * (attempt + 1))
                else:
                    self.logger.error(f"Ошибка MusicBrainz API: {response.status_code}")
                    return None
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Ошибка запроса: {e}")
                if attempt < retry - 1:
                    time.sleep(2 * (attempt + 1))
                else:
                    raise NetworkError(f"Не удалось связаться с MusicBrainz: {e}")
        return None

    def search_recording(self, artist, title, limit=5):
        try:
            artist_clean = str(artist).replace('"', '').strip()
            title_clean = str(title).replace('"', '').strip()
            query = f'artist:"{artist_clean}" AND recording:"{title_clean}"'
            
            params = {
                'query': query,
                'fmt': 'json',
                'limit': limit
            }
            
            self.logger.info(f"Поиск в MusicBrainz: {artist_clean} - {title_clean}")
            result = self._make_request('recording', params)
            
            if result and 'recordings' in result and result['recordings']:
                return result['recordings']
            return []
        except Exception as e:
            self.logger.error(f"Ошибка при поиске: {e}")
            raise MetadataError(f"Ошибка поиска в MusicBrainz: {e}")

    def get_recording_details(self, recording_id, includes=None):
        if includes is None:
            includes = ['artists', 'releases', 'tags']
        params = {
            'fmt': 'json',
            'inc': ' '.join(includes)
        }
        return self._make_request(f'recording/{recording_id}', params)

    def extract_metadata(self, recording_data):
        try:
            metadata = {}
            if 'title' in recording_data:
                metadata['title'] = recording_data['title']
            if 'id' in recording_data:
                metadata['recording_id'] = recording_data['id']
            if 'artist-credit' in recording_data and recording_data['artist-credit']:
                ac = recording_data['artist-credit'][0]
                if 'artist' in ac:
                    metadata['artist'] = ac['artist'].get('name', '')
                    metadata['artist_id'] = ac['artist'].get('id', '')
            if 'releases' in recording_data and recording_data['releases']:
                rel = recording_data['releases'][0]
                metadata['album'] = rel.get('title', '')
                metadata['release_id'] = rel.get('id', '')
                if 'date' in rel:
                    metadata['date'] = rel['date'][:4]
                    metadata['year'] = int(rel['date'][:4])
                if 'country' in rel:
                    metadata['country'] = rel['country']
            if 'length' in recording_data and recording_data['length']:
                metadata['length_ms'] = recording_data['length']
                length_sec = recording_data['length'] // 1000
                minutes = length_sec // 60
                seconds = length_sec % 60
                metadata['duration'] = f"{minutes}:{seconds:02d}"
            if 'tags' in recording_data and recording_data['tags']:
                genres = [tag['name'] for tag in recording_data['tags'][:3]]
                if genres:
                    metadata['genres'] = genres
                    metadata['genre'] = ', '.join(genres)
            return metadata if metadata else None
        except Exception as e:
            self.logger.error(f"Ошибка извлечения метаданных: {e}")
            return None
