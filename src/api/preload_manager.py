# src/api/preload_manager.py
"""
Менеджер предзагрузки для ускорения поиска
Предварительно загружает популярные треки в фоне
"""

import threading
import queue
import time
import logging
from typing import Dict, Optional
from src.config import config

logger = logging.getLogger(__name__)

class PreloadManager:
    """
    Фоновый менеджер для предзагрузки популярных треков
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.preload_queue = queue.Queue()
        self.cache = {}
        self.running = True
        self.worker_thread = None
        
        # Запускаем фоновый поток
        if config.get("enable_preload", True):
            self.start()
    
    def start(self):
        """Запуск фонового потока"""
        if self.worker_thread is None:
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
            logger.info("Менеджер предзагрузки запущен")
    
    def stop(self):
        """Остановка фонового потока"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=2)
    
    def preload(self, artist: str, title: str):
        """Добавление трека в очередь предзагрузки"""
        key = f"{artist}_{title}".lower()
        if key not in self.cache:
            self.preload_queue.put((artist, title))
    
    def _worker(self):
        """Фоновый рабочий процесс"""
        from api.fast_youtube_client import FastYouTubeClient
        client = FastYouTubeClient()
        
        while self.running:
            try:
                # Ждём задачу с таймаутом
                artist, title = self.preload_queue.get(timeout=1)
                key = f"{artist}_{title}".lower()
                
                if key not in self.cache:
                    logger.info(f"Предзагрузка: {artist} - {title}")
                    result = client.search_track_fast(artist, title)
                    if result:
                        self.cache[key] = {
                            'result': result,
                            'timestamp': time.time()
                        }
                
                self.preload_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Ошибка предзагрузки: {e}")
    
    def get_cached(self, artist: str, title: str) -> Optional[Dict]:
        """Получение из кэша"""
        key = f"{artist}_{title}".lower()
        cached = self.cache.get(key)
        
        if cached:
            age = time.time() - cached['timestamp']
            if age < 300:  # 5 минут
                return cached['result']
            else:
                del self.cache[key]
        
        return None

# Глобальный экземпляр
preload_manager = PreloadManager()