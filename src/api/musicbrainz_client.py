# src/api/musicbrainz_client.py
import requests
import time
from ..logger_config import LoggerMixin
from ..constants import MUSICBRAINZ_URL, USER_AGENT
from ..exceptions import NetworkError, MetadataError

class MusicBrainzClient(LoggerMixin):
    """
    Клиент для работы с MusicBrainz API.
    """
    
    def __init__(self):
        self.base_url = MUSICBRAINZ_URL
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'application/json'
        })
        self.logger.info("MusicBrainzClient инициализирован")

    def _make_request(self, endpoint, params=None, retry=3):
        """
        Выполняет запрос к MusicBrainz API с повторными попытками.
        """
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(retry):
            try:
                response = self.session.get(url, params=params, timeout=10)
                time.sleep(1)  # MusicBrainz требует задержки
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 503:
                    self.logger.warning(f"MusicBrainz временно недоступен, попытка {attempt+1}/{retry}")
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
        """
        Поиск записи в MusicBrainz по исполнителю и названию.
        """
        try:
            artist_clean = artist.replace('"', '').strip()
            title_clean = title.replace('"', '').strip()
            query = f'artist:"{artist_clean}" AND recording:"{title_clean}"'
            
            params = {
                'query': query,
                'fmt': 'json',
                'limit': limit
            }
            
            self.logger.info(f"Поиск в MusicBrainz: {artist_clean} - {title_clean}")
            result = self._make_request('recording', params)
            
            if result and 'recordings' in result and result['recordings']:
                self.logger.info(f"Найдено {len(result['recordings'])} записей")
                return result['recordings'][0]
            else:
                self.logger.info("Запись не найдена в MusicBrainz")
                return None
        except Exception as e:
            self.logger.error(f"Ошибка при поиске: {e}")
            raise MetadataError(f"Ошибка поиска в MusicBrainz: {e}")

    def get_recording_details(self, recording_id, includes=None):
        """
        Получение детальной информации о записи.
        """
        if includes is None:
            includes = ['artists', 'releases', 'tags']
        
        params = {
            'fmt': 'json',
            'inc': ' '.join(includes)
        }
        
        result = self._make_request(f'recording/{recording_id}', params)
        return result

    def extract_metadata(self, recording_data):
        """
        Извлекает метаданные из ответа MusicBrainz.
        """
        try:
            metadata = {}
            
            if 'title' in recording_data:
                metadata['title'] = recording_data['title']
            
            if 'artist-credit' in recording_data and recording_data['artist-credit']:
                artist_credit = recording_data['artist-credit'][0]
                if 'artist' in artist_credit:
                    metadata['artist'] = artist_credit['artist'].get('name', '')
                    if 'joinphrase' in artist_credit:
                        metadata['artist'] += artist_credit['joinphrase']
            
            if 'releases' in recording_data and recording_data['releases']:
                release = recording_data['releases'][0]
                metadata['album'] = release.get('title', '')
                if 'date' in release:
                    metadata['date'] = release['date'][:4]
                if 'country' in release:
                    metadata['country'] = release['country']
            
            if 'length' in recording_data and recording_data['length']:
                length_sec = recording_data['length'] // 1000
                minutes = length_sec // 60
                seconds = length_sec % 60
                metadata['duration'] = f"{minutes}:{seconds:02d}"
            
            if 'tags' in recording_data and recording_data['tags']:
                genres = [tag['name'] for tag in recording_data['tags'][:3]]
                if genres:
                    metadata['genre'] = ', '.join(genres)
            
            return metadata if metadata else None
        except Exception as e:
            self.logger.error(f"Ошибка извлечения метаданных: {e}")
            return None