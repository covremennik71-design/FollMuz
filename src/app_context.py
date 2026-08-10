# src/app_context.py
import os
import sys
import json
import subprocess

SETTINGS_FILE = 'settings.json'
HASH_FOLDER = 'hash_cache'

CREATION_FLAGS = 0
if sys.platform == 'win32':
    CREATION_FLAGS = subprocess.CREATE_NO_WINDOW

os.makedirs(HASH_FOLDER, exist_ok=True)

DEFAULT_SETTINGS = {
    'path_tracks': 'C:/Users/Smixr/Music',
    'path_playlists': 'C:/Users/Smixr/Music/Playlists',
    'player_width': 450,
    'theme': 'dark',
    'crossfade_enabled': True,
    'crossfade_duration': 2,
    'favorite_artists': [],
    'excluded_artists': [],
    'favorite_genres': [],
    'excluded_genres': [],
    'tg_token': ''
}

_ffmpeg_path_cache = None

def find_ffmpeg():
    global _ffmpeg_path_cache
    if _ffmpeg_path_cache is not None:
        return _ffmpeg_path_cache or None
    
    import shutil
    ffmpeg = shutil.which('ffmpeg')
    if ffmpeg:
        _ffmpeg_path_cache = os.path.dirname(ffmpeg)
        return _ffmpeg_path_cache
        
    common_paths = [
        os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin'),
        r'C:\ProgramData\chocolatey\bin',
        r'C:\ffmpeg\bin',
        r'C:\ffmpeg',
    ]
    for p in common_paths:
        if os.path.exists(p):
            _ffmpeg_path_cache = p
            return p
            
    _ffmpeg_path_cache = "" 
    return None

_settings_cache = {'mtime': 0, 'data': None}

def load_settings():
    global _settings_cache
    try:
        mtime = os.path.getmtime(SETTINGS_FILE) if os.path.exists(SETTINGS_FILE) else 0
        if _settings_cache['data'] is not None and _settings_cache['mtime'] == mtime:
            return _settings_cache['data'].copy()
    except Exception:
        pass

    cfg = DEFAULT_SETTINGS.copy()
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                file_settings = json.load(f)
                cfg.update(file_settings)
        except Exception:
            pass
    for k in DEFAULT_SETTINGS:
        if k not in cfg:
            cfg[k] = DEFAULT_SETTINGS[k]
            
    try:
        _settings_cache['mtime'] = os.path.getmtime(SETTINGS_FILE) if os.path.exists(SETTINGS_FILE) else 0
        _settings_cache['data'] = cfg.copy()
    except Exception:
        pass
        
    return cfg

def write_settings(new_vals):
    global _settings_cache
    existing = load_settings()
    existing.update(new_vals)
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=4)
    try:
        _settings_cache['mtime'] = os.path.getmtime(SETTINGS_FILE) if os.path.exists(SETTINGS_FILE) else 0
        _settings_cache['data'] = existing.copy()
    except Exception:
        pass
