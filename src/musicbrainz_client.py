import requests
import time
from src.logger import Logger

logger = Logger()

class MusicBrainzClient:
    def __init__(self, user_agent="FollMuz/1.0 (gghsvar@gmail.com)"):
        self.base_url = "https://musicbrainz.org/ws/2"
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'application/json'
        })
        logger.info("MusicBrainzClient инициализирован")

    def _make_request(self, endpoint, params=None, retry=3):
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(retry):
            try:
                response = self.session.get(url, params=params, timeout=10)
                
                time.sleep(1)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 503:
                    logger.warning(f"MusicBrainz временно недоступен, попытка {attempt + 1}/{retry}")
                    time.sleep(2 * (attempt + 1))
                else:
                    logger.error(f"Ошибка MusicBrainz API: {response.status_code}")
                    return None
                    
            except Exception as e:
                logger.error(f"Ошибка запроса к MusicBrainz: {e}")
                if attempt < retry - 1:
                    time.sleep(2 * (attempt + 1))
                else:
                    return None
        return None

    def search_recording(self, artist, title, limit=5):
        try:
            artist_clean = artist.replace('"', '').strip()
            title_clean = title.replace('"', '').strip()
            
            query = f'artist:"{artist_clean}" AND recording:"{title_clean}"'
            
            params = {
                'query': query,
                'fmt': 'json',
                'limit': limit
            }
            
            logger.info(f"Поиск в MusicBrainz: {artist_clean} - {title_clean}")
            result = self._make_request('recording', params)
            
            if result and 'recordings' in result and result['recordings']:
                logger.info(f"Найдено {len(result['recordings'])} записей")
                return result['recordings'][0]
            else:
                logger.info(f"Запись не найдена в MusicBrainz")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при поиске в MusicBrainz: {e}")
            return None

    def get_recording_details(self, recording_id, includes=None):
        try:
            if includes is None:
                includes = ['artists', 'releases', 'tags']
            
            params = {
                'fmt': 'json',
                'inc': ' '.join(includes)
            }
            
            result = self._make_request(f'recording/{recording_id}', params)
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при получении деталей записи: {e}")
            return None

    def extract_metadata(self, recording_data):
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
                genres = []
                for tag in recording_data['tags'][:3]:
                    if 'name' in tag:
                        genres.append(tag['name'])
                if genres:
                    metadata['genre'] = ', '.join(genres)
            
            return metadata if metadata else None
            
        except Exception as e:
            logger.error(f"Ошибка при извлечении метаданных: {e}")
            return None

    def search_artist(self, artist_name):
        try:
            query = f'artist:"{artist_name}"'
            params = {
                'query': query,
                'fmt': 'json',
                'limit': 5
            }
            
            result = self._make_request('artist', params)
            
            if result and 'artists' in result and result['artists']:
                return result['artists'][0]
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при поиске исполнителя: {e}")
            return None

    def get_artist_recordings(self, artist_id, limit=25):
        try:
            params = {
                'artist': artist_id,
                'fmt': 'json',
                'limit': limit
            }
            
            result = self._make_request('recording', params)
            
            if result and 'recordings' in result:
                return result['recordings']
            return []
            
        except Exception as e:
            logger.error(f"Ошибка при получении записей исполнителя: {e}")
            return []
