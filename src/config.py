# src/config.py
import json
import os
import re
import threading
from typing import Any, Dict, Optional

from src.logger import Logger

logger = Logger()


class Config:
    """
    Синглтон для управления настройками приложения.
    Потокобезопасный, с кэшированием и валидацией.
    """

    _instance: Optional["Config"] = None
    _lock = threading.Lock()

    def __new__(cls, config_path: str = "config/settings.json"):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, config_path: str = "config/settings.json"):
        # Инициализация только один раз
        if getattr(self, "_initialized", False):
            return

        with self._lock:
            if self._initialized:
                return

            self._initialized = True
            self.config_path = config_path
            self.default_settings = self.get_default_settings()
            self.settings = self.load_settings()
            self._cache: Dict[str, Any] = {}

    # ---------- Настройки по умолчанию ----------

    def get_default_settings(self) -> Dict[str, Any]:
        """Возвращает настройки по умолчанию."""
        cwd = os.getcwd()
        downloads_dir = os.path.join(cwd, "downloads")
        playlists_dir = os.path.join(downloads_dir, "playlists")

        return {
            # Основные настройки
            "download_path": downloads_dir,
            "last_download_path": downloads_dir,
            "last_playlist_path": playlists_dir,
            "single_download_path": downloads_dir,
            "playlist_download_path": playlists_dir,
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

            # Ускорение / API
            "enable_preload": True,
            "enable_cache": True,
            "youtube_api_key": "AIzaSyD-W93nU6oAP2Tm7jTdt0_R2foiMjPtyNw",
            "search_timeout": 3,
            "pharallel_search": True,
            "use_bypass": False,
        }

    # ---------- Загрузка / сохранение ----------

    def load_settings(self) -> Dict[str, Any]:
        """Загружает настройки из файла, объединяя с дефолтными."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded_settings = json.load(f)

                if not isinstance(loaded_settings, dict):
                    logger.warning("Файл настроек повреждён, используем настройки по умолчанию")
                    return self.default_settings.copy()

                settings = self.default_settings.copy()
                settings.update(loaded_settings)

                # Валидация некоторых полей
                settings = self._validate_settings(settings)

                logger.info("Настройки загружены из файла")
                return settings

            except Exception as e:
                logger.error(f"Ошибка загрузки настроек: {e}")
                return self.default_settings.copy()
        else:
            try:
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            except Exception:
                pass
            self.save_settings(self.default_settings)
            logger.info("Создан файл настроек по умолчанию")
            return self.default_settings.copy()

    def _validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Базовая валидация настроек."""
        # Числовые поля
        for key in ("window_width", "window_height"):
            val = settings.get(key)
            if isinstance(val, int) and val > 0:
                continue
            settings[key] = self.default_settings[key]

        for key in ("player_volume",):
            val = settings.get(key)
            if isinstance(val, (int, float)) and 0.0 <= val <= 1.0:
                continue
            settings[key] = self.default_settings[key]

        # Пути: проверяем, что строки
        path_keys = [
            "download_path",
            "last_download_path",
            "last_playlist_path",
            "single_download_path",
            "playlist_download_path",
        ]
        for key in path_keys:
            val = settings.get(key)
            if not isinstance(val, str):
                settings[key] = self.default_settings[key]

        return settings

    def save_settings(self, settings: Optional[Dict[str, Any]] = None) -> None:
        """Сохраняет настройки в файл."""
        if settings is None:
            settings = self.settings

        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
            logger.info("Настройки сохранены")
        except Exception as e:
            logger.error(f"Ошибка сохранения настроек: {e}")

    # ---------- Доступ к настройкам ----------

    def get(self, key: str, default: Any = None) -> Any:
        """Получить значение настройки с кэшированием."""
        if key in self._cache:
            return self._cache[key]

        value = self.settings.get(key, default)
        self._cache[key] = value
        return value

    def set(self, key: str, value: Any, save: bool = True) -> None:
        """
        Установить значение настройки.

        :param key: Ключ настройки.
        :param value: Новое значение.
        :param save: Сохранять ли сразу в файл.
        """
        self.settings[key] = value
        self._cache[key] = value
        if save:
            self.save_settings()

    # ---------- Методы для работы с путями ----------

    def get_download_path(self) -> str:
        """Получить текущий путь для скачивания (alias для single_download_path)."""
        return self.get_single_download_path()

    def set_download_path(self, path: str) -> None:
        """Сохранить путь для скачивания."""
        self.set_single_download_path(path)

    def get_single_download_path(self) -> str:
        """Получить папку для скачивания одиночных треков."""
        return self.get(
            "single_download_path",
            self.get("last_download_path", self.default_settings["last_download_path"]),
        )

    def set_single_download_path(self, path: str) -> None:
        """Сохранить папку для скачивания одиночных треков."""
        if path and os.path.isdir(path):
            self.set("single_download_path", path, save=False)
            self.set("last_download_path", path, save=False)
            self.set("download_path", path, save=True)  # для совместимости
        else:
            logger.warning(f"Некорректный путь для одиночных треков: {path}")

    def get_last_download_path(self) -> str:
        """Получить последнюю использованную папку (прямой доступ)."""
        return self.get("last_download_path", self.default_settings["last_download_path"])

    def set_last_download_path(self, path: str) -> None:
        """Сохранить последнюю использованную папку."""
        if path and os.path.isdir(path):
            self.set("last_download_path", path)
        else:
            logger.warning(f"Некорректный путь для last_download_path: {path}")

    def get_last_playlist_path(self) -> str:
        """Получить последнюю папку для плейлиста."""
        return self.get_playlist_download_path()

    def set_last_playlist_path(self, path: str) -> None:
        """Сохранить последнюю папку для плейлиста."""
        self.set_playlist_download_path(path)

    def get_playlist_download_path(self) -> str:
        """Получить папку для скачивания плейлистов."""
        return self.get(
            "playlist_download_path",
            self.get("last_playlist_path", self.default_settings["last_playlist_path"]),
        )

    def set_playlist_download_path(self, path: str) -> None:
        """Сохранить папку для скачивания плейлистов."""
        if path and os.path.isdir(path):
            self.set("playlist_download_path", path, save=False)
            self.set("last_playlist_path", path, save=True)
        else:
            logger.warning(f"Некорректный путь для плейлистов: {path}")

    # ---------- Методы для работы с окном ----------

    def get_window_geometry(self) -> str:
        """Получить последний размер и позицию окна в формате WxH+X+Y."""
        width = self.get("window_width", 900)
        height = self.get("window_height", 700)
        x = self.get("window_x")
        y = self.get("window_y")

        if x is not None and y is not None:
            return f"{width}x{height}+{x}+{y}"
        return f"{width}x{height}"

    def save_window_geometry(self, geometry: str) -> None:
        """
        Сохранить размер и позицию окна.

        :param geometry: Строка вида 'WxH+X+Y' или 'WxH'.
        """
        self.set("window_geometry", geometry, save=False)

        match = re.match(r"(d+)x(d+)([+-]d+)?([+-]d+)?", geometry)
        if match:
            width = int(match.group(1))
            height = int(match.group(2))
            self.set("window_width", width, save=False)
            self.set("window_height", height, save=False)

            if match.group(3) and match.group(4):
                x = int(match.group(3))
                y = int(match.group(4))
                self.set("window_x", x, save=False)
                self.set("window_y", y, save=False)

            self.save_settings()
        else:
            logger.warning(f"Некорректная геометрия окна: {geometry}")

    # ---------- Вкладки и прочее ----------

    def get_last_tab(self) -> int:
        """Получить последнюю использованную вкладку."""
        val = self.get("last_used_tab", 0)
        return int(val) if isinstance(val, int) else 0

    def set_last_tab(self, tab_index: int) -> None:
        """Сохранить последнюю использованную вкладку."""
        if isinstance(tab_index, int) and tab_index >= 0:
            self.set("last_used_tab", tab_index)
        else:
            logger.warning(f"Некорректный индекс вкладки: {tab_index}")

    # ---------- Токены (VK и т.п.) ----------

    def clean_token(self, token_input: str) -> str:
        """Извлекает токен из ссылки, если нужно."""
        if "access_token=" in token_input:
            match = re.search(r"access_token=([^&]+)", token_input)
            if match:
                return match.group(1)
        return token_input.strip()

    def validate_token(self, token: str) -> bool:
        """Проверяет, что токен похож на настоящий."""
        return len(token) > 10 and token.isprintable()

    # ---------- Сброс ----------

    def reset_to_defaults(self) -> None:
        """Сброс настроек до значений по умолчанию."""
        self.settings = self.default_settings.copy()
        self._cache.clear()
        self.save_settings(self.settings)
        logger.info("Настройки сброшены до значений по умолчанию")


# Глобальный экземпляр для удобства
config = Config()