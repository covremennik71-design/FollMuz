# src/follmuz_downloader.py
import re
import yt_dlp
import os
import logging

logger = logging.getLogger(__name__)

class FollMuzDownloader:
    """
    Универсальный модуль для скачивания музыки.
    Поддерживает: Spotify, Yandex Music, MTS Music -> поиск на YouTube -> скачивание.
    """
    
    def __init__(self, output_dir="downloads"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
    def _extract_info_via_ytdlp(self, url):
        """Извлекает метаданные трека (максимально надёжный метод с ретраями)."""
        # 1. Для Spotify пробуем OEmbed с повторными попытками и увеличенным таймаутом
        if 'spotify.com' in url:
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            try:
                session = requests.Session()
                # Настраиваем автоматические повторы при ошибках соединения/таймаутах
                retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
                session.mount('https://', HTTPAdapter(max_retries=retries))
                
                oembed_url = f"https://open.spotify.com/oembed?url={url}"
                # Увеличиваем таймаут до 20 секунд
                response = session.get(oembed_url, timeout=20, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })
                
                if response.status_code == 200:
                    data = response.json()
                    full_title = data.get('title', '')
                    if ' - ' in full_title:
                        artist, title = full_title.split(' - ', 1)
                        return {
                            'title': title.strip(),
                            'artist': artist.strip(),
                            'album': data.get('album', ''),
                        }
            except Exception as e:
                logger.warning(f"OEmbed для Spotify не сработал после попыток: {e}")

        # 2. Общий метод через yt-dlp (основной фоллбэк)
        try:
            import subprocess
            import json
            ytdlp_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".venv", "Scripts", "yt-dlp.exe")
            
            args = [
                ytdlp_path, 
                "-j", 
                "--no-check-certificate", 
                "--no-warnings",
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                url
            ]
            
            # Увеличиваем таймаут для системного вызова
            result = subprocess.run(args, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                title = data.get('track') or data.get('title') or data.get('webpage_url_basename') or "Unknown"
                artist = data.get('artist') or data.get('uploader') or "Unknown"
                album = data.get('album', '')
                
                return {
                    'title': title,
                    'artist': artist,
                    'album': album,
                }
            else:
                err_msg = result.stderr.lower()
                if "captcha" in err_msg or "robot" in err_msg or "403" in err_msg:
                    return {"error": "captcha"}
                logger.error(f"yt-dlp error (code {result.returncode}): {result.stderr}")
        except Exception as e:
            logger.error(f"Ошибка при использовании yt-dlp: {e}")
            
        return None



    def _get_variation_suffix(self, title):
        """Определяет вариацию трека для добавления в название файла."""
        title_lower = title.lower()
        patterns = {
            ' (Sped Up)': ['sped up', 'speed up', 'nightcore', 'fast version'],
            ' (Slowed)': ['slowed', 'slow version', 'slowed + reverb', 'slowed down'],
            ' (Reverb)': ['reverb', 'echo', 'cathedral'],
            ' (Bass Boosted)': ['bass boosted', 'bass boost', 'heavy bass']
        }
        
        for suffix, keywords in patterns.items():
            if any(kw in title_lower for kw in keywords):
                return suffix
        return ''
    
    def search_and_download(self, artist, title, save_path=None, modification="", progress_callback=None):
        """Ищет и скачивает трек."""
        if not save_path:
            save_path = self.output_dir
            
        search_query = f"{artist} - {title}"
        if modification:
            search_query += f" {modification.strip(' ()')}"
            
        suffix = self._get_variation_suffix(title)
        outtmpl = os.path.join(save_path, f"{artist} - {title}{suffix}.%(ext)s")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': outtmpl,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'default_search': 'ytsearch1',
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if progress_callback:
                    progress_callback(10, "Поиск на YouTube...")
                
                info = ydl.extract_info(f"ytsearch1:{search_query}", download=True)
                
                if progress_callback:
                    progress_callback(100, "Завершено")
                
                return True, info['entries'][0]['requested_downloads'][0]['filepath']
        except Exception as e:
            logger.error(f"Ошибка скачивания: {e}")
            return False, str(e)

    def download_by_url(self, url, save_path=None):
        """Универсальный метод для ссылок Spotify, Yandex Music, MTS Music."""
        info = self._extract_info_via_ytdlp(url)
        if not info:
            return False, "Не удалось извлечь информацию по ссылке"
        
        variation = self._get_variation_suffix(info['title'])
        return self.search_and_download(info['artist'], info['title'], save_path, modification=variation)

    
    def _get_variation_suffix(self, title):
        """Определяет вариацию трека для добавления в название файла."""
        title_lower = title.lower()
        patterns = {
            ' (Sped Up)': ['sped up', 'speed up', 'nightcore', 'fast version'],
            ' (Slowed)': ['slowed', 'slow version', 'slowed + reverb', 'slowed down'],
            ' (Reverb)': ['reverb', 'echo', 'cathedral'],
            ' (Bass Boosted)': ['bass boosted', 'bass boost', 'heavy bass']
        }
        
        for suffix, keywords in patterns.items():
            if any(kw in title_lower for kw in keywords):
                return suffix
        return ''
    
    def search_and_download(self, artist, title, save_path=None, modification="", progress_callback=None):
        """Ищет и скачивает трек."""
        if not save_path:
            save_path = self.output_dir
            
        search_query = f"{artist} - {title}"
        if modification:
            # Если это вариация, добавляем её к поисковому запросу для лучшего результата
            search_query += f" {modification.strip(' ()')}"
            
        # Добавляем вариацию к имени файла
        suffix = self._get_variation_suffix(title)
        outtmpl = os.path.join(save_path, f"{artist} - {title}{suffix}.%(ext)s")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': outtmpl,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'default_search': 'ytsearch1',
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if progress_callback:
                    progress_callback(10, "Поиск на YouTube...")
                
                info = ydl.extract_info(f"ytsearch1:{search_query}", download=True)
                
                if progress_callback:
                    progress_callback(100, "Завершено")
                
                return True, info['entries'][0]['requested_downloads'][0]['filepath']
        except Exception as e:
            logger.error(f"Ошибка скачивания: {e}")
            return False, str(e)

    def download_spotify_track(self, spotify_url, save_path=None):
        """Главный метод для Spotify URL."""
        info = self._extract_info_via_ytdlp(spotify_url)
        if not info:
            return False, "Не удалось получить информацию из Spotify"
        
        # Получаем вариацию, если она есть
        variation = self._get_variation_suffix(info['title'])
        
        return self.search_and_download(info['artist'], info['title'], save_path, modification=variation)
