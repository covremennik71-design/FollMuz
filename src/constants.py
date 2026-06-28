# src/constants.py
"""Константы, используемые в приложении."""

# Типы треков
# src/constants.py
TRACK_TYPES = [
    {
        "id": "original", 
        "name_ru": "Оригинал", 
        "name_en": "Original", 
        "search_term": ""  # пустая строка для оригинального названия
    },
    {
        "id": "slowed", 
        "name_ru": "Slowed", 
        "name_en": "Slowed", 
        "search_term": "slowed"
    },
    {
        "id": "sped_up", 
        "name_ru": "Sped Up", 
        "name_en": "Sped Up", 
        "search_term": "sped up"
    },
    {
        "id": "remix", 
        "name_ru": "Ремикс", 
        "name_en": "Remix", 
        "search_term": "remix"
    },
    {
        "id": "instrumental", 
        "name_ru": "Инструментал", 
        "name_en": "Instrumental", 
        "search_term": "instrumental"
    },
    {
        "id": "live", 
        "name_ru": "Live", 
        "name_en": "Live", 
        "search_term": "live"
    },
    {
        "id": "acoustic", 
        "name_ru": "Акустика", 
        "name_en": "Acoustic", 
        "search_term": "acoustic"
    },
]

# Качество аудио
AUDIO_QUALITIES = ["128", "192", "256", "320"]

# Каналы аудио
AUDIO_CHANNELS = [
    {"id": "stereo", "name_ru": "Стерео", "name_en": "Stereo", "ffmpeg_param": "2"},
    {"id": "mono", "name_ru": "Моно", "name_en": "Mono", "ffmpeg_param": "1"},
]

# URL API
MUSICBRAINZ_URL = "https://musicbrainz.org/ws/2"
USER_AGENT = "FollMuz/1.0 (https://github.com/username/follmuz)"

# Версии API
VK_API_VERSION = "5.131"
YOUTUBE_API_VERSION = "v3"