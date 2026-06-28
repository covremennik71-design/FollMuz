# src/config.py
import json
import os
import re
from src.logger import Logger

logger = Logger()

class Config:
    _instance = None
    
    def __new__(cls, config_path="config/settings.json"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_path="config/settings.json"):
        if self._initialized:
            return
            
        self._initialized = True
        self.config_path = config_path
        self.default_settings = self.get_default_settings()
        self.settings = self.load_settings()
        self._cache = {}

    def get_default_settings(self):
        """Возвращает настройки по умолчанию"""
        cwd = os.getcwd()
        return {
            # Основные настройки
            "download_path": os.path.join(cwd, "downloads"),
            "last_download_path": os.path.join(cwd, "downloads"),
            "last_playlist_path": os.path.join(cwd, "downloads", "playlists"),
            "single_download_path": os.path.join(cwd, "downloads"),
            "playlist_download_path": os.path.join(cwd, "downloads", "playlists"),
            "mp3_quality": "192",
            "add_tags": True,
            "download_cover": True,
            
            # Внешний вид
            "theme": "dark",
            "language": "ru",
            "minimize_to_tray": False,
            "window_width": 900,
            "window_height": 700,
            "window_x": None,
            "window_y": None,
            "window_geometry": "900x700",
            "player_volume": 0.8,
            
            # Дополнительно
            "auto_check_updates": True,
            "last_used_tab": 0,
            # Ускорение
            "enable_preload": True,
            "enable_cache": True,
            "youtube_api_key": "AIzaSyD-W93nU6oAP2Tm7jTdt0_R2foiMjPtyNw",
            "search_timeout": 3,
            "pharallel_search": True,
            "use_bypass": False,
        }


    def load_settings(self):
        """Загружает настройки из файла"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # Объединяем с настройками по умолчанию (добавляем новые ключи)
                    settings = self.default_settings.copy()
                    settings.update(loaded_settings)
                    logger.info("Настройки загружены из файла")
                    return settings
            except Exception as e:
                logger.error(f"Ошибка загрузки настроек: {e}")
                return self.default_settings.copy()
        else:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            self.save_settings(self.default_settings)
            logger.info("Создан файл настроек по умолчанию")
            return self.default_settings.copy()

    def save_settings(self, settings=None):
        """Сохраняет настройки в файл"""
        if settings is None:
            settings = self.settings
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
            logger.info("Настройки сохранены")
        except Exception as e:
            logger.error(f"Ошибка сохранения настроек: {e}")

    def get(self, key, default=None):
        """Получить значение настройки с кэшированием."""
        if key in self._cache:
            return self._cache[key]
        value = self.settings.get(key, default)
        self._cache[key] = value
        return value

    def set(self, key, value):
        """Установить значение настройки и сохранить."""
        self.settings[key] = value
        self._cache[key] = value
        self.save_settings()

    # Методы для работы с путями
    def get_download_path(self):
        """Получить текущий путь для скачивания (alias для last_download_path)"""
        return self.get_single_download_path()

    def set_download_path(self, path):
        """Сохранить путь для скачивания"""
        self.set_single_download_path(path)

    def get_single_download_path(self):
        """Получить папку для скачивания одиночных треков."""
        return self.get(
            "single_download_path",
            self.get("last_download_path", self.default_settings["last_download_path"])
        )

    def set_single_download_path(self, path):
        """Сохранить папку для скачивания одиночных треков."""
        if path and os.path.exists(path):
            self.set("single_download_path", path)
            self.set("last_download_path", path)
            self.set("download_path", path)  # для совместимости

    def get_last_download_path(self):
        """Получить последнюю использованную папку (прямой доступ)"""
        return self.get("last_download_path", self.default_settings["last_download_path"])

    def set_last_download_path(self, path):
        """Сохранить последнюю использованную папку"""
        if path and os.path.exists(path):
            self.set("last_download_path", path)

    def get_last_playlist_path(self):
        """Получить последнюю папку для плейлиста"""
        return self.get_playlist_download_path()

    def set_last_playlist_path(self, path):
        """Сохранить последнюю папку для плейлиста"""
        self.set_playlist_download_path(path)

    def get_playlist_download_path(self):
        """Получить папку для скачивания плейлистов."""
        return self.get(
            "playlist_download_path",
            self.get("last_playlist_path", self.default_settings["last_playlist_path"])
        )

    def set_playlist_download_path(self, path):
        """Сохранить папку для скачивания плейлистов."""
        if path and os.path.exists(path):
            self.set("playlist_download_path", path)
            self.set("last_playlist_path", path)

    # Методы для работы с окном
    def get_window_geometry(self):
        """Получить последний размер окна"""
        width = self.get("window_width", 900)
        height = self.get("window_height", 700)
        x = self.get("window_x")
        y = self.get("window_y")
        if x is not None and y is not None:
            return f"{width}x{height}+{x}+{y}"
        return f"{width}x{height}"

    def save_window_geometry(self, geometry):
        """Сохранить размер окна (строку вида WxH+X+Y)"""
        self.set("window_geometry", geometry)
        # Парсим для отдельных полей
        import re
        match = re.match(r'(\d+)x(\d+)([+-]\d+)?([+-]\d+)?', geometry)
        if match:
            width, height = int(match.group(1)), int(match.group(2))
            self.set("window_width", width)
            self.set("window_height", height)
            if match.group(3) and match.group(4):
                x = int(match.group(3))
                y = int(match.group(4))
                self.set("window_x", x)
                self.set("window_y", y)

    def get_last_tab(self):
        """Получить последнюю использованную вкладку"""
        return self.get("last_used_tab", 0)

    def set_last_tab(self, tab_index):
        """Сохранить последнюю использованную вкладку"""
        self.set("last_used_tab", tab_index)

    def clean_token(self, token_input):
        """Извлекает токен из ссылки, если нужно"""
        if 'access_token=' in token_input:
            match = re.search(r'access_token=([^&]+)', token_input)
            if match:
                return match.group(1)
        return token_input.strip()

    def validate_token(self, token):
        """Проверяет, что токен похож на настоящий"""
        return len(token) > 10 and token.isprintable()

    def reset_to_defaults(self):
        """Сброс настроек до значений по умолчанию"""
        self.settings = self.default_settings.copy()
        self.save_settings(self.settings)
        logger.info("Настройки сброшены до значений по умолчанию")


# Глобальный экземпляр для удобства
config = Config()
