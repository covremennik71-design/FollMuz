# src/api/youtube_client.py
import yt_dlp
import os
import re
from ..logger_config import LoggerMixin
from ..exceptions import SearchError, DownloadError
from ..utils import sanitize_filename, format_duration, format_size
from ..constants import TRACK_TYPES
from ..config import config

class YouTubeClient(LoggerMixin):
    """
    Клиент для поиска и скачивания аудио с YouTube.
    """
    
    def __init__(self):
        self.ydl_opts = self._get_base_opts()
        self.logger.info("YouTubeClient инициализирован")
    
    def _get_base_opts(self):
        """Базовые опции для yt-dlp."""
        import random
        quality = config.get("mp3_quality", "192")
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15',
        ]
        return {
            'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
            'format_sort': ['+size', '+br', '+res', 'hasaud'],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': quality,
            }],
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'retries': 5,
            'fragment_retries': 5,
            'wait_for_video': (5, 10),
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'android', 'web', 'default'],
                }
            },
            'http_headers': {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            },
        }
    
    def _is_relevant_result(self, title, artist, title_part, modification):
        """
        Проверяет, соответствует ли название видео запросу.
        """
        title_lower = title.lower()
        artist_lower = artist.lower()
        title_part_lower = title_part.lower()
        
        # Исполнитель должен присутствовать
        if artist_lower not in title_lower and artist_lower.split()[-1] not in title_lower:
            return False
        
        # Название должно присутствовать
        if title_part_lower not in title_lower:
            words = title_part_lower.split()
            if not any(word in title_lower for word in words):
                return False
        
        # Термины модификаций для фильтрации
        modification_terms = {
            'slowed': ['slowed', 'slowed + reverb', 'slow + reverb', 'slow reverb', 'slowedreverb', 'slow+reverb'],
            'speed up': ['speed up', 'sped up', 'spedup', 'speedup', 'nightcore', 'night core', 'sped ', ' sped'],
            'remix': ['remix', 'mashup', 'bootleg'],
            'instrumental': ['instrumental', 'karaoke', 'no vocals', 'no vocal'],
            'live': ['live', 'concert', 'on stage', 'live performance', ' (live)'],
            'acoustic': ['acoustic', 'unplugged', 'piano version'],
        }
        
        if modification and modification != 'original':
            track_types_dict = {t['id']: t for t in TRACK_TYPES}
            mod_info = track_types_dict.get(modification, {})
            search_term = mod_info.get('search_term', '')
            if search_term and search_term not in title_lower:
                return False
        else:
            # Для оригинала — отклоняем ЛЮБУЮ модификацию
            for mod_key, terms in modification_terms.items():
                for term in terms:
                    if term in title_lower:
                        return False
        
        return True
    
    def _build_queries(self, artist, title, modification):
        """Строит список поисковых запросов от наиболее точного к общему."""
        track_types_dict = {t['id']: t for t in TRACK_TYPES}
        mod_info = track_types_dict.get(modification, track_types_dict['original'])
        search_term = mod_info.get('search_term', '')
        
        queries = []
        
        if modification and modification != 'original' and search_term:
            queries.append(f"{artist} - {title} {search_term}")
            queries.append(f"{artist} {title} {search_term}")
        
        # Запросы для оригина — с приоритетом на официальные релизы
        queries.append(f"{artist} - {title}")
        queries.append(f"{artist} {title} official audio")
        queries.append(f"{artist} {title} official video")
        queries.append(f"{artist} - {title} official")
        queries.append(f"{artist} {title} audio")
        
        return queries
    
    def search_track(self, artist, title, modification='original'):
        """
        Ищет трек на YouTube с учётом модификации.
        
        Args:
            artist (str): Исполнитель.
            title (str): Название трека.
            modification (str): Ключ модификации из TRACK_TYPES.
        
        Returns:
            dict: Информация о найденном видео (url, title, duration, webpage_url).
        
        Raises:
            SearchError: Если трек не найден.
        """
        # Формируем список поисковых запросов
        queries = self._build_queries(artist, title, modification)
        
        ydl_opts = self._get_base_opts()
        ydl_opts['default_search'] = 'ytsearch'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for query in queries:
                self.logger.info(f"Пробую запрос: {query}")
                try:
                    info = ydl.extract_info(f"ytsearch5:{query}", download=False)
                    if info and isinstance(info, dict) and 'entries' in info:
                        for entry in info['entries']:
                            if not isinstance(entry, dict):
                                continue
                            if self._is_relevant_result(
                                entry.get('title', ''), artist, title, modification
                            ):
                                # Используем webpage_url как основной URL
                                video_url = entry.get('webpage_url') or entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id', '')}"
                                result = {
                                    'url': video_url,
                                    'title': entry.get('title'),
                                    'duration': entry.get('duration'),
                                    'webpage_url': video_url,
                                    'extractor': entry.get('extractor'),
                                }
                                self.logger.info(f"Найдено релевантное видео: {entry.get('title')}")
                                return result
                except Exception as e:
                    self.logger.warning(f"Ошибка при поиске по запросу {query}: {e}")
                    continue
        
        raise SearchError(f"Трек не найден для {artist} - {title} ({modification})")
    
    def download_track(self, info, output_path):
        """
        Скачивает аудио по информации о видео.
        
        Args:
            info (dict): Информация о видео (результат search_track).
            output_path (str): Путь для сохранения файла.
        
        Returns:
            str: Путь к скачанному файлу.
        
        Raises:
            DownloadError: Если скачивание не удалось.
        """
        video_id = info.get('id', '') or info.get('webpage_url', '').split('v=')[-1].split('&')[0]
        safe_title = sanitize_filename(info.get('title', 'audio'))
        
        import time
        import random
        
        ydl_opts = self._get_base_opts()
        ydl_opts['outtmpl'] = os.path.join(output_path, f'{safe_title}_{video_id}.%(ext)s')
        
        format_candidates = [
            'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
            'bestaudio/best',
            'bestaudio*',
            'best[ext=m4a]/best[ext=webm]/best',
            'best',
            'worstaudio/worst',
        ]
        
        last_error = None
        for format_name in format_candidates:
            ydl_opts['format'] = format_name
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    self.logger.info(f"Скачивание (формат: {format_name}): {info['webpage_url']}")
                    ydl.download([info['webpage_url']])
                    
                    # Ищем скачанный файл по уникальному имени
                    import glob
                    pattern = os.path.join(output_path, f'{safe_title}_{video_id}.*')
                    downloaded_files = glob.glob(pattern)
                    if downloaded_files:
                        # Если это не mp3, конвертируем
                        for f in downloaded_files:
                            if f.endswith('.mp3'):
                                return f
                        # Конвертация через ffmpeg если нужно
                        import subprocess
                        for f in downloaded_files:
                            mp3_path = os.path.splitext(f)[0] + '.mp3'
                            if os.path.exists(mp3_path):
                                return mp3_path
                            try:
                                subprocess.run([
                                    'ffmpeg', '-y', '-i', f,
                                    '-codec:a', 'libmp3lame',
                                    '-b:a', str(config.get("mp3_quality", "192")) + 'k',
                                    mp3_path
                                ], check=True, capture_output=True)
                                if os.path.exists(mp3_path):
                                    return mp3_path
                            except Exception:
                                continue
                        raise DownloadError("Не удалось конвертировать в mp3")
                    else:
                        raise DownloadError("Файл не найден после скачивания")
            except Exception as e:
                last_error = e
                self.logger.warning(f"Формат {format_name} не удался: {e}")
                time.sleep(random.uniform(1, 3))
                continue
        
        raise DownloadError(f"Не удалось скачать трек: {last_error}")