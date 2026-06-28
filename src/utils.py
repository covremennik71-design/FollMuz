# src/utils.py
"""Вспомогательные утилиты для приложения."""
import os
import re
import datetime
import customtkinter as ctk
from src.styles import AppFonts

def safe_abs(value, default=0):
    """Безопасное вычисление абсолютного значения."""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return default

def safe_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def sanitize_filename(filename):
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    filename = filename.strip()
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200] + ext
    return filename

def create_ctk_font(style="body", weight=None, family=None):
    params = AppFonts.get_font(style, weight, family)
    return ctk.CTkFont(**params)

def ensure_dir_exists(path):
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def get_latest_file(directory, extension=None):
    if not os.path.exists(directory):
        return None
    files = os.listdir(directory)
    if extension:
        files = [f for f in files if f.endswith(extension)]
    if not files:
        return None
    full_paths = [os.path.join(directory, f) for f in files]
    latest = max(full_paths, key=os.path.getmtime)
    return latest

def format_duration(seconds):
    if not seconds:
        return "0:00"
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes}:{secs:02d}"

def format_size(bytes_size):
    size = safe_float(bytes_size, 0)
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.1f} GB"

def parse_query(query):
    if ' - ' in query:
        artist, title = query.split(' - ', 1)
        return artist.strip(), title.strip()
    return "Unknown", query.strip()

def extract_video_id(url):
    patterns = [
        r'(?:youtube\.com\/watch\?v=)([^&]+)',
        r'(?:youtu\.be\/)([^?]+)',
        r'(?:youtube\.com\/embed\/)([^?]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_timestamp():
    return datetime.datetime.now().strftime("%H:%M:%S")

def clean_filename_for_download(artist, title, extension=".mp3"):
    filename = f"{artist} - {title}{extension}"
    return sanitize_filename(filename)

def safe_remove_file(filepath):
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except:
        pass

# ===== Новые функции для нормализации и генерации вариантов поиска =====

def normalize_query(text):
    """
    Нормализует текст для поиска: удаляет спецсимволы, приводит к нижнему регистру.
    
    Args:
        text: Исходный текст
    
    Returns:
        str: Нормализованный текст
    """
    if not text:
        return text
    
    # Удаляем эмодзи (все диапазоны)
    text = re.sub(r'[\u2600-\u26FF\u2700-\u27BF\u2190-\u21FF\u2500-\u25FF\u2600-\u26FF]', '', text)
    text = re.sub(r'[\U0001F300-\U0001F9FF]', '', text)
    text = re.sub(r'[\U0001FA00-\U0001FAFF]', '', text)
    text = re.sub(r'[\U00002702-\U000027B0]', '', text)
    
    # Удаляем символы валют
    text = re.sub(r'[$\u20A0-\u20CF]', '', text)
    
    # Удаляем спецсимволы поиска: # @ ^ ? ! ~ ` \ | / . , ; : = + *
    text = re.sub(r'[#@^?!~`\\|/,;:=+*<>]', ' ', text)
    
    # Удаляем кавычки
    text = re.sub(r'[""„"\']', '', text)
    
    # Обрабатываем скобки с feat: [feat. xxx] -> feat xxx
    text = re.sub(r'[\(\[\{][^\)\]\}]*?(feat|featuring|ft)[.\s]*([^\)\]\}]*?)[\)\]\}]', r' \1 \2 ', text, flags=re.IGNORECASE)
    
    # Удаляем остальные скобки
    text = re.sub(r'[\(\)\[\]\{\}]', ' ', text)
    
    # Удаляем повторяющиеся дефисы и точки
    text = re.sub(r'[-_.\s]{2,}', ' ', text)
    
    # Удаляем невидимые символы
    text = re.sub(r'[\u200B-\u200F\u2028-\u202F\uFEFF]', '', text)
    
    # Убираем лишние пробелы
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text.lower()


def generate_search_variations(artist, title):
    """
    Генерирует различные варианты написания для поиска.
    
    Args:
        artist: Исполнитель
        title: Название трека
    
    Returns:
        list: Список вариантов для поиска
    """
    variations = []
    
    # Оригинальные строки
    variations.append(f"{artist} {title}")
    
    # Нормализованные (без спецсимволов)
    norm_artist = normalize_query(artist)
    norm_title = normalize_query(title)
    variations.append(f"{norm_artist} {norm_title}")
    
    # Без исполнителя (только название)
    variations.append(title)
    variations.append(norm_title)
    
    # Разные комбинации
    variations.append(f"{artist} {norm_title}")
    variations.append(f"{norm_artist} {title}")
    
    # Удаляем символы валют и спецсимволы (дополнительная очистка)
    clean_artist = re.sub(r'[$€£¥]', '', artist).strip()
    clean_title = re.sub(r'[$€£¥]', '', title).strip()
    
    if clean_artist != artist:
        variations.append(f"{clean_artist} {title}")
        variations.append(f"{clean_artist} {norm_title}")
    
    if clean_title != title:
        variations.append(f"{artist} {clean_title}")
        variations.append(f"{norm_artist} {clean_title}")
    
    # Разбиваем на слова для частичного поиска
    artist_words = norm_artist.split()
    title_words = norm_title.split()
    
    # Комбинации первых слов
    if artist_words and title_words:
        variations.append(f"{artist_words[0]} {title}")
        variations.append(f"{artist} {title_words[0]}")
        variations.append(f"{artist_words[0]} {title_words[0]}")
    
    # Убираем дубликаты и пустые строки
    variations = [v for v in variations if v.strip()]
    return list(dict.fromkeys(variations))