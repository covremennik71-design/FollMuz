# src/exceptions.py
"""
Собственные исключения для FollMuz.
"""

class FollMuzError(Exception):
    """Базовое исключение для всех ошибок приложения."""
    pass

class ConfigError(FollMuzError):
    """Ошибка загрузки или сохранения конфигурации."""
    pass

class NetworkError(FollMuzError):
    """Сетевая ошибка при запросах к API."""
    pass

class SearchError(FollMuzError):
    """Ошибка при поиске трека."""
    pass

class DownloadError(FollMuzError):
    """Ошибка при скачивании файла."""
    pass

class MetadataError(FollMuzError):
    """Ошибка при добавлении метаданных."""
    pass

class ValidationError(FollMuzError):
    """Ошибка валидации входных данных."""
    pass