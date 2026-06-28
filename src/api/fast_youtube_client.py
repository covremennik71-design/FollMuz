# src/api/fast_youtube_client.py
import time
import logging
import os
import re
import sys
from typing import Optional, Dict

# Ensure src directory is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logger = logging.getLogger(__name__)

class FastYouTubeClient:
    def __init__(self, check_api_on_init=True):
        self.cache = {}
        self.cache_ttl = 300
        self.session = None
        self.api_quota_exceeded = False
        
        # Проверяем наличие YouTube API ключа из конфига
        from src.config import config
        self.api_key = config.get("youtube_api_key", "")
        self.use_youtube_api = bool(self.api_key and self.api_key.strip())
        
        if self.use_youtube_api and check_api_on_init:
            # Проверяем доступность API при инициализации
            if not self._check_api_quota():
                logger.warning("YouTube API quota exceeded or invalid, switching to youtube-search-python")
                self.use_youtube_api = False
                self.api_quota_exceeded = True
        
        if self.use_youtube_api:
            logger.info("YouTube API ключ найден, используется быстрый поиск")
        else:
            logger.info("YouTube API ключ не найден или исчерпан, используется youtube-search-python")

    def _check_api_quota(self) -> bool:
        """Проверяет доступность YouTube API (не исчерпана ли квота)."""
        if not self.api_key:
            return False
        
        try:
            params = {
                'part': 'snippet',
                'q': 'test',
                'type': 'video',
                'maxResults': 1,
                'key': self.api_key
            }
            
            response = self.get_session().get(
                'https://www.googleapis.com/youtube/v3/search',
                params=params,
                timeout=5
            )
            
            if response.status_code == 200:
                return True
            elif response.status_code == 403:
                error_data = response.json()
                error_reason = error_data.get('error', {}).get('errors', [{}])[0].get('reason', '')
                if error_reason == 'quotaExceeded':
                    logger.warning("YouTube API квота исчерпана")
                    return False
                elif error_reason == 'keyInvalid':
                    logger.warning("YouTube API ключ недействителен")
                    return False
            return False
        except Exception as e:
            logger.warning(f"Ошибка проверки YouTube API: {e}")
            return False

    def get_session(self):
        if self.session is None:
            import requests
            self.session = requests.Session()
        return self.session

    def _normalize(self, text: str) -> str:
        return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]+', ' ', (text or '').lower(), flags=re.UNICODE)).strip()

    def _score_result(self, video: Dict, artist: str, title: str, modification: str) -> int:
        artist_n = self._normalize(artist)
        title_n = self._normalize(title)
        modification_n = self._normalize(modification)
        video_title = self._normalize(video.get('title', ''))

        score = 0
        if artist_n and artist_n in video_title:
            score += 6
        if title_n and title_n in video_title:
            score += 8

        modification_terms = {
            'slowed': ['slowed', 'slow + reverb', 'slowed + reverb', 'slowreverb', 'slowedreverb'],
            'speed up': ['speed up', 'sped up', 'spedup', 'speedup', 'nightcore', 'night core'],
            'remix': ['remix', 'mashup', 'bootleg'],
            'instrumental': ['instrumental', 'karaoke', 'no vocals', 'no vocal'],
            'live': ['live', 'concert', 'on stage', 'live performance'],
            'acoustic': ['acoustic', 'unplugged', 'piano version'],
        }

        if modification_n:
            target_terms = modification_terms.get(modification_n, [modification_n])
            if any(term in video_title for term in target_terms):
                score += 10
            else:
                score -= 20
        else:
            for mod_key, terms in modification_terms.items():
                if any(term in video_title for term in terms):
                    score -= 30

        if 'official audio' in video_title or 'official video' in video_title:
            score += 5
        if 'official' in video_title:
            score += 2
        if 'lyrics' in video_title:
            score -= 1
        return score

    def _pick_best_result(self, results, artist: str, title: str, modification: str) -> Optional[Dict]:
        if not results:
            return None
        scored = sorted(
            results,
            key=lambda video: self._score_result(video, artist, title, modification),
            reverse=True,
        )
        best = scored[0]
        best_score = self._score_result(best, artist, title, modification)
        if best_score < 0:
            return None
        return best
    
    def _build_search_queries(self, artist: str, title: str, modification: str):
        """Строит список поисковых запросов."""
        from ..constants import TRACK_TYPES
        track_types_dict = {t['id']: t for t in TRACK_TYPES}
        mod_info = track_types_dict.get(modification, track_types_dict.get('original', {}))
        search_term = mod_info.get('search_term', '')
        
        queries = []
        
        if modification and modification != 'original' and search_term:
            queries.append(f"{artist} {title} {search_term}")
        
        queries.append(f"{artist} {title}")
        queries.append(f"{artist} {title} official audio")
        queries.append(f"{artist} {title} official video")
        queries.append(f"{artist} {title} audio")
        
        return queries
    
    def search_track_fast(self, artist: str, title: str, modification: str = "") -> Optional[Dict]:
        cache_key = f"{artist}_{title}_{modification}".lower()
        
        # Проверяем кэш
        if cache_key in self.cache:
            cached_time, cached_result = self.cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                logger.info(f"Использован кэш для {cache_key}")
                return cached_result
        
        # Выполняем поиск
        result = None
        if self.use_youtube_api:
            result = self._search_via_api(artist, title, modification)
        
        if not result:
            result = self._search_via_python_lib(artist, title, modification)
        
        if result:
            self.cache[cache_key] = (time.time(), result)
        
        return result
    
    def _search_via_api(self, artist: str, title: str, modification: str) -> Optional[Dict]:
        try:
            queries = self._build_search_queries(artist, title, modification)
            
            for search_query in queries:
                params = {
                    'part': 'snippet',
                    'q': search_query,
                    'type': 'video',
                    'videoCategoryId': '10',
                    'maxResults': 5,
                    'key': self.api_key
                }
                
                response = self.get_session().get(
                    'https://www.googleapis.com/youtube/v3/search',
                    params=params,
                    timeout=3
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('items'):
                        candidates = []
                        for item in data['items']:
                            video_id = item['id']['videoId']
                            candidates.append({
                                'id': video_id,
                                'title': item['snippet']['title'],
                                'url': f'https://www.youtube.com/watch?v={video_id}',
                                'duration': 'Unknown'
                            })
                        result = self._pick_best_result(candidates, artist, title, modification)
                        if result:
                            return result
            return None
        except Exception as e:
            logger.error(f"Ошибка API: {e}")
            return None
    
    def _search_via_python_lib(self, artist: str, title: str, modification: str) -> Optional[Dict]:
        queries = self._build_search_queries(artist, title, modification)

        for search_query in queries:
            # Первичный поиск через youtubesearchpython
            try:
                from youtubesearchpython import VideosSearch

                videos_search = VideosSearch(search_query, limit=5)
                results = videos_search.result()

                if results and results.get('result'):
                    candidates = []
                    for video in results['result'][:5]:
                        video_id = video['id']
                        candidates.append({
                            'id': video_id,
                            'title': video['title'],
                            'url': f"https://www.youtube.com/watch?v={video_id}",
                            'duration': video.get('duration', 'Unknown')
                        })
                    result = self._pick_best_result(candidates, artist, title, modification)
                    if result:
                        return result
            except ModuleNotFoundError:
                break
            except TypeError as e:
                if "proxies" in str(e):
                    pass
                else:
                    logger.warning(f"Ошибки youtubesearchpython: {e}")
            except Exception as e:
                if "proxies" not in str(e):
                    logger.warning(f"Ошибки youtubesearchpython: {e}")

        for search_query in queries:
            # Фоллбэк на youtube_search
            try:
                from youtube_search import YoutubeSearch

                results = YoutubeSearch(search_query, max_results=5).to_dict()
                if results:
                    candidates = []
                    for video in results[:5]:
                        candidates.append({
                            'id': video['id'],
                            'title': video['title'],
                            'url': f"https://youtube.com/watch?v={video['id']}",
                            'duration': video.get('duration', 'Unknown')
                        })
                    result = self._pick_best_result(candidates, artist, title, modification)
                    if result:
                        return result
            except ModuleNotFoundError:
                logger.warning("youtube_search не установлен")
            except Exception as e:
                logger.warning(f"Ошибки youtube_search: {e}")

        logger.warning("Не удалось выполнить поиск: ни одна библиотека не установлена или не вернула результат")
        return None

    def search_tracks_batch(self, tracks, max_results_per_track=5, progress_callback=None):
        """
        Пакетный поиск треков с обработкой по кругам.
        
        Args:
            tracks: список словарей {'artist': ..., 'title': ..., 'modification': ...}
            max_results_per_track: максимальное количество результатов на трек
            progress_callback: функция обратного вызова для прогресса (current, total, track_info)
        
        Returns:
            список результатов в том же порядке что и tracks
        """
        results = [None] * len(tracks)
        not_found_indices = list(range(len(tracks)))
        
        # Круг 1: Точный поиск
        logger.info(f"Круг 1: Точный поиск ({len(not_found_indices)} треков)")
        for i, idx in enumerate(not_found_indices[:]):
            track = tracks[idx]
            result = self.search_track_fast(
                track.get('artist', ''),
                track.get('title', ''),
                track.get('modification', '')
            )
            if result:
                results[idx] = result
                not_found_indices.remove(idx)
            
            if progress_callback:
                progress_callback(i + 1, len(tracks), track)
        
        # Круг 2: Поиск без модификации
        if not_found_indices:
            logger.info(f"Круг 2: Поиск без модификации ({len(not_found_indices)} треков)")
            for idx in not_found_indices[:]:
                track = tracks[idx]
                result = self.search_track_fast(
                    track.get('artist', ''),
                    track.get('title', ''),
                    ''  # Без модификации
                )
                if result:
                    results[idx] = result
                    not_found_indices.remove(idx)
        
        # Круг 3: Поиск только по названию
        if not_found_indices:
            logger.info(f"Круг 3: Поиск только по названию ({len(not_found_indices)} треков)")
            for idx in not_found_indices[:]:
                track = tracks[idx]
                result = self.search_track_fast(
                    '',  # Без артиста
                    f"{track.get('artist', '')} {track.get('title', '')}",
                    ''
                )
                if result:
                    results[idx] = result
                    not_found_indices.remove(idx)
        
        if not_found_indices:
            logger.warning(f"Не найдено {len(not_found_indices)} треков")
        
        return results
