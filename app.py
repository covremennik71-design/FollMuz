from flask import Flask, render_template, request, jsonify, send_from_directory, Response
import subprocess
import os
import sys
import json
import shutil
import time
import hashlib
import threading
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, APIC
import yt_dlp
import random
from collections import Counter
import urllib.request
import urllib.parse
from src.taxonomy import MUSIC_TAXONOMY, normalize_genre, infer_genre_from_filename
from src.catalog_engine import CatalogEngine, log_user_event, build_user_taste_profile

# Инициализация Flask приложения
app = Flask(__name__)

from src.routes.catalog_bp import catalog_bp
from src.routes.settings_bp import settings_bp
from src.routes.media_bp import media_bp
from src.routes.playlist_bp import playlist_bp
from src.routes.bot_bp import bot_bp

app.register_blueprint(catalog_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(media_bp)
app.register_blueprint(playlist_bp)
app.register_blueprint(bot_bp)
SETTINGS_FILE = 'settings.json'
HASH_FOLDER = 'hash_cache'

# Флаги чтобы консоль не вылезала при вызовах под Windows
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
    # Кэшируем путь к ffmpeg, чтобы каждый раз не опрашивать диск
    global _ffmpeg_path_cache
    if _ffmpeg_path_cache is not None:
        return _ffmpeg_path_cache or None
    
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

@app.errorhandler(Exception)
def handle_exception(e):
    print(f"[ERROR] {e}")
    return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_settings', methods=['GET'])
def get_settings():
    settings = load_settings()
    return jsonify(settings)

@app.route('/save_settings', methods=['POST'])
def save_settings_api():
    try:
        data = request.json or {}
        write_settings(data)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/track_info/<filename>')
def get_track_info(filename):
    settings = load_settings()
    filepath = os.path.join(settings['path_tracks'], filename)
    
    title = os.path.splitext(filename)[0]
    artist = 'Unknown'
    if ' - ' in title:
        parts = title.split(' - ', 1)
        artist = parts[0].strip()
        title = parts[1].strip()

    info = {
        'title': title, 
        'artist': artist, 
        'genre': '', 
        'normalized_genre': infer_genre_from_filename(filename)
    }
    try:
        audio = ID3(filepath)
        if 'TIT2' in audio:
            info['title'] = str(audio['TIT2'])
        if 'TPE1' in audio:
            info['artist'] = str(audio['TPE1'])
            
        tcon = audio.get('TCON')
        raw_genre = ''
        if tcon and tcon.text:
            raw_genre = str(tcon.text[0])
        elif 'genre' in audio:
            raw_genre = str(audio['genre'])
        
        if raw_genre and raw_genre.lower() != 'unknown':
            info['genre'] = raw_genre
            info['normalized_genre'] = normalize_genre(raw_genre)
    except Exception:
        pass
    return jsonify(info)

@app.route('/cover/<filename>')
def get_cover(filename):
    settings = load_settings()
    filepath = os.path.join(settings['path_tracks'], filename)
    try:
        audio = ID3(filepath)
        for tag in audio.values():
            if tag.FrameID == 'APIC':
                res = Response(tag.data, mimetype='image/jpeg')
                res.headers['Cache-Control'] = 'public, max-age=86400'
                return res
    except Exception:
        pass
    res = send_from_directory('static', 'default_cover.png')
    res.headers['Cache-Control'] = 'public, max-age=86400'
    return res

def fix_double_extension(path, artist, title):
    # Хак: иногда yt-dlp умудряется сохранить файл как .mp3.mp3
    name = f"{artist} - {title}" if artist and title else (title if title else None)
    if name:
        exp = os.path.join(path, f"{name}.mp3")
        dbl = os.path.join(path, f"{name}.mp3.mp3")
        if os.path.exists(dbl) and not os.path.exists(exp):
            os.rename(dbl, exp)

def run_ytdlp_download(download_target, output_path, timeout=600):
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        return False, 'ffmpeg не найден'
    cmd = [
        sys.executable, '-m', 'yt_dlp',
    ]
    if shutil.which('deno'):
        cmd.extend(['--js-runtimes', 'deno'])
    cmd.extend([
        '--no-update',
        '--remote-components', 'ejs:github',
        '--extractor-args', 'youtube:player_client=android',
        '--format', 'bestaudio/best', '-x', '--audio-format', 'mp3',
        '--ffmpeg-location', ffmpeg_path, '-o', output_path, download_target
    ])
    env = os.environ.copy()
    env['YTDLP_NO_COOKIES'] = '1'
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, creationflags=CREATION_FLAGS, timeout=timeout, env=env)
        if res.returncode != 0:
            return False, res.stderr.strip() or res.stdout.strip() or f'error {res.returncode}'
        return True, None
    except subprocess.TimeoutExpired:
        return False, 'Таймаут'
    except Exception as e:
        return False, str(e)

@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.json or {}
        url = data.get('url', '').strip()
        artist = data.get('artist', '').strip()
        title = data.get('title', '').strip()
        to_hash = data.get('to_hash', False)
        destination = data.get('destination', 'library')
        
        path = HASH_FOLDER if to_hash else load_settings()['path_tracks']
        os.makedirs(path, exist_ok=True)
            
        download_target = url or (f"ytsearch1:{artist} - {title}" if artist and title else f"ytsearch1:{artist or title}")
        if not download_target or download_target == 'ytsearch1:':
            return jsonify({'status': 'error', 'message': 'Не указана ссылка или поисковый запрос'}), 400

        filename_template = f"{artist} - {title}.mp3" if artist and title else (f"{title}.mp3" if title else "%(title)s.%(ext)s")
        output_path = os.path.join(path, filename_template)
        
        success, err = run_ytdlp_download(download_target, output_path, 600)
        if not success:
            return jsonify({'status': 'error', 'message': err[:500]}), 500
        
        fix_double_extension(path, artist, title)
        actual_filename = f"{artist} - {title}.mp3" if artist and title else (f"{title}.mp3" if title else filename_template)
        
        if destination != 'library' and destination:
            try:
                add_track_to_playlist_internal(destination, actual_filename)
            except Exception as e:
                print(f"[WARNING] {e}")
        
        return jsonify({'status': 'success', 'filename': actual_filename})
    except Exception as e:
        print(f"[DOWNLOAD ERROR] {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/download_list', methods=['POST'])
def download_list():
    try:
        data = request.json or {}
        tracks = data.get('tracks', [])
        destination = data.get('destination', 'library')
        if not tracks:
            return jsonify({'status': 'error', 'message': 'Список треков пуст'}), 400
        
        path = load_settings()['path_tracks']
        os.makedirs(path, exist_ok=True)
        results = []
        
        for track_str in tracks:
            track_str = track_str.strip()
            if not track_str: continue
            
            artist, title = (track_str.split(' - ', 1) if ' - ' in track_str else ('', track_str))
            artist, title = artist.strip(), title.strip()
            
            download_target = f"ytsearch1:{artist} - {title}" if artist else f"ytsearch1:{title}"
            filename_template = f"{artist} - {title}.mp3" if artist else f"{title}.mp3"
            output_path = os.path.join(path, filename_template)
            
            success, err = run_ytdlp_download(download_target, output_path, 180)
            if not success:
                results.append({'track': track_str, 'status': 'error', 'message': err[:200]})
                continue
            
            fix_double_extension(path, artist, title)
            if destination != 'library' and destination:
                try: add_track_to_playlist_internal(destination, filename_template)
                except Exception: pass
            results.append({'track': track_str, 'status': 'success', 'filename': filename_template})
            
        return jsonify({'status': 'success', 'results': results})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def add_track_to_playlist_internal(playlist_name, track_filename):
    # Внутренний хелпер для добавления трека в плейлист без лишних запросов
    settings = load_settings()
    path = settings['path_playlists']
    
    folder_path = os.path.join(path, playlist_name)
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        src = os.path.join(settings['path_tracks'], track_filename)
        dst = os.path.join(folder_path, track_filename)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
        return
    
    playlist_path = os.path.join(path, f"{playlist_name}.m3u")
    if os.path.exists(playlist_path):
        with open(playlist_path, 'a', encoding='utf-8') as f:
            f.write(os.path.join(settings['path_tracks'], track_filename) + '\n')

def format_duration(seconds):
    if not seconds:
        return "--:--"
    try:
        seconds = int(seconds)
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}:{secs:02d}"
    except Exception:
        return "--:--"

from src.api.youtube_search import yt_search

@app.route('/delete_track', methods=['POST'])
def delete_track():
    data = request.json or {}
    filename = data.get('filename')
    if not filename:
        return jsonify({'status': 'error', 'message': 'Имя файла не указано'}), 400
    
    settings = load_settings()
    filepath = os.path.join(settings['path_tracks'], filename)
    if os.path.exists(filepath):
        for attempt in range(5):
            try:
                os.remove(filepath)
                return jsonify({'status': 'success'})
            except Exception as e:
                if attempt < 4:
                    time.sleep(0.5)
                else:
                    return jsonify({'status': 'error', 'message': str(e)}), 500
    return jsonify({'status': 'error', 'message': 'Файл не найден'}), 404

@app.route('/search_catalog', methods=['POST'])
def search_catalog():
    data = request.json or {}
    query = data.get('query', '').strip()
    limit = data.get('limit', 12)
    if not query:
        return jsonify({'status': 'error', 'message': 'Пустой запрос'}), 400
    
    results = CatalogEngine.catalog_search(query, limit)
    return jsonify({
        'status': 'success',
        'query': query,
        'results': results,
        'tracks': results
    })

@app.route('/recommendations', methods=['GET'])
def get_recommendations():
    try:
        surface = request.args.get('surface', 'home')
        limit = int(request.args.get('limit', 20))
        seed = request.args.get('seed', '')
        
        if surface == 'daily_mix':
            items = CatalogEngine.daily_mix(limit=limit)
        elif surface == 'release_radar':
            items = CatalogEngine.release_radar(limit=limit)
        elif surface == 'radio':
            items = CatalogEngine.radio_feed(seed_track=seed or "electronic hit", limit=limit)
        elif surface == 'autoplay':
            items = CatalogEngine.autoplay_feed(current_track=seed or "track", limit=limit)
        else:
            items = CatalogEngine.home_feed(limit=limit)

        import datetime
        return jsonify({
            'status': 'success',
            'surface': surface,
            'generated_at': datetime.datetime.utcnow().isoformat() + 'Z',
            'items': items,
            'tracks': items  # backward compatibility for frontend
        })
    except Exception as e:
        print(f"[RECOMMENDATIONS ERROR] {e}")
        return jsonify({'status': 'success', 'surface': 'home', 'items': [], 'tracks': []})

@app.route('/files')
def list_files():
    settings = load_settings()
    path = settings['path_tracks']
    if not os.path.exists(path):
        os.makedirs(path)
    try:
        with os.scandir(path) as it:
            files = [entry.name for entry in it if entry.is_file() and entry.name.endswith('.mp3')]
    except Exception:
        files = [f for f in os.listdir(path) if f.endswith('.mp3')]
    return jsonify({'files': files})

@app.route('/play/<filename>')
def play_file(filename):
    settings = load_settings()
    return send_from_directory(settings['path_tracks'], filename)

# ===== ПЛЕЙЛИСТЫ =====
def clean_playlist_name(name):
    if not name:
        return ""
    name = str(name).strip()
    while name.lower().endswith(('.m3u', '.m3u8')):
        name = os.path.splitext(name)[0]
    return name.strip()

def cleanup_broken_playlists(path):
    if not os.path.exists(path):
        return
    try:
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file() and (".m3u." in entry.name.lower() or entry.name.lower().endswith(('.m3u.m3u', '.m3u8.m3u8', '.m3u.m3u8', '.m3u8.m3u'))):
                    clean_name = clean_playlist_name(os.path.splitext(entry.name)[0])
                    if clean_name:
                        new_path = os.path.join(path, f"{clean_name}.m3u")
                        if not os.path.exists(new_path):
                            os.rename(entry.path, new_path)
                        else:
                            os.remove(entry.path)
    except Exception as e:
        print(f"[CLEANUP ERROR] {e}")

@app.route('/playlists/list', methods=['GET'])
def list_playlists():
    settings = load_settings()
    path = settings['path_playlists']
    if not os.path.exists(path):
        os.makedirs(path)
    
    cleanup_broken_playlists(path)
    
    playlists = []
    try:
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_dir():
                    count = 0
                    try:
                        with os.scandir(entry.path) as sub_it:
                            count = sum(1 for sub in sub_it if sub.is_file() and sub.name.endswith('.mp3'))
                    except Exception:
                        pass
                    playlists.append({
                        'name': clean_playlist_name(entry.name),
                        'type': 'folder',
                        'count': count,
                        'path': entry.name
                    })
                elif entry.is_file() and (entry.name.endswith('.m3u') or entry.name.endswith('.m3u8')):
                    count = 0
                    try:
                        with open(entry.path, 'r', encoding='utf-8', errors='ignore') as f:
                            count = sum(1 for line in f if line.strip() and not line.startswith('#'))
                    except Exception:
                        pass
                    playlists.append({
                        'name': clean_playlist_name(os.path.splitext(entry.name)[0]),
                        'type': 'playlist',
                        'count': count,
                        'path': entry.name
                    })
    except Exception as e:
        print(f"[PLAYLISTS ERROR] {e}")
    
    return jsonify({'playlists': playlists})

@app.route('/playlists/create', methods=['POST'])
def create_playlist():
    data = request.json or {}
    name = clean_playlist_name(data.get('name', ''))
    ptype = data.get('type', 'playlist')
    
    if not name:
        return jsonify({'status': 'error', 'message': 'Имя не указано'}), 400
    
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    name = clean_playlist_name(name)
    
    settings = load_settings()
    path = settings['path_playlists']
    if not os.path.exists(path):
        os.makedirs(path)
    
    try:
        if ptype == 'folder':
            folder_path = os.path.join(path, name)
            if os.path.exists(folder_path):
                return jsonify({'status': 'success', 'name': name})
            os.makedirs(folder_path, exist_ok=True)
        else:
            playlist_path = os.path.join(path, f"{name}.m3u")
            if os.path.exists(playlist_path):
                return jsonify({'status': 'success', 'name': name})
            with open(playlist_path, 'w', encoding='utf-8') as f:
                f.write('#EXTM3U\n')
        
        return jsonify({'status': 'success', 'name': name})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/playlists/delete', methods=['POST'])
def delete_playlist():
    data = request.json or {}
    name = clean_playlist_name(data.get('name', ''))
    
    if not name:
        return jsonify({'status': 'error', 'message': 'Имя не указано'}), 400
    
    settings = load_settings()
    path = settings['path_playlists']
    
    try:
        deleted = False
        folder_path = os.path.join(path, name)
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            shutil.rmtree(folder_path)
            deleted = True
            
        for ext in ['', '.m3u', '.m3u8']:
            p = os.path.join(path, name + ext)
            if os.path.exists(p):
                os.remove(p)
                deleted = True
                
        if os.path.exists(path):
            with os.scandir(path) as it:
                for entry in it:
                    base_name = clean_playlist_name(os.path.splitext(entry.name)[0])
                    if entry.name.lower() == name.lower() or base_name.lower() == name.lower():
                        if entry.is_dir():
                            shutil.rmtree(entry.path, ignore_errors=True)
                        else:
                            try:
                                os.remove(entry.path)
                            except Exception:
                                pass
                        deleted = True
                        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/playlists/<name>/tracks', methods=['GET'])
def get_playlist_tracks(name):
    name = clean_playlist_name(name)
    settings = load_settings()
    path = settings['path_playlists']
    
    try:
        folder_path = os.path.join(path, name)
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            files = [f for f in os.listdir(folder_path) if f.endswith('.mp3')]
            return jsonify({'tracks': files, 'type': 'folder'})
        
        playlist_path = os.path.join(path, f"{name}.m3u")
        if os.path.exists(playlist_path):
            with open(playlist_path, 'r', encoding='utf-8') as f:
                lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]
            return jsonify({'tracks': [os.path.basename(l) for l in lines], 'type': 'playlist'})
        
        playlist_path_8 = os.path.join(path, f"{name}.m3u8")
        if os.path.exists(playlist_path_8):
            with open(playlist_path_8, 'r', encoding='utf-8') as f:
                lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]
            return jsonify({'tracks': [os.path.basename(l) for l in lines], 'type': 'playlist'})
    except Exception as e:
        print(f"[PLAYLIST TRACKS ERROR] {e}")
        return jsonify({'tracks': [], 'type': 'unknown'})
    
    return jsonify({'tracks': [], 'type': 'unknown'})

@app.route('/playlists/<name>/add_track', methods=['POST'])
def add_track_to_playlist(name):
    name = clean_playlist_name(name)
    data = request.json or {}
    filename = data.get('filename', '').strip()
    
    if not filename:
        return jsonify({'status': 'error', 'message': 'Файл не указан'}), 400
    
    settings = load_settings()
    path = settings['path_playlists']
    
    folder_path = os.path.join(path, name)
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        src = os.path.join(settings['path_tracks'], filename)
        dst = os.path.join(folder_path, filename)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error', 'message': 'Файл не найден'}), 404
    
    playlist_path = os.path.join(path, f"{name}.m3u")
    os.makedirs(path, exist_ok=True)
    with open(playlist_path, 'a', encoding='utf-8') as f:
        if os.path.getsize(playlist_path) == 0:
            f.write('#EXTM3U\n')
        f.write(os.path.join(settings['path_tracks'], filename) + '\n')
    return jsonify({'status': 'success'})

@app.route('/playlists/add_tracks', methods=['POST'])
def add_tracks_to_playlist():
    data = request.json or {}
    name = clean_playlist_name(data.get('name', ''))
    tracks = data.get('tracks', [])
    
    if not name:
        return jsonify({'status': 'error', 'message': 'Имя плейлиста не указано'}), 400
    if not tracks:
        return jsonify({'status': 'error', 'message': 'Треки не указаны'}), 400
    
    settings = load_settings()
    path = settings['path_playlists']
    os.makedirs(path, exist_ok=True)
    
    try:
        folder_path = os.path.join(path, name)
        playlist_path = os.path.join(path, f"{name}.m3u")
        playlist_path_8 = os.path.join(path, f"{name}.m3u8")
        
        added = 0
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            for filename in tracks:
                src = os.path.join(settings['path_tracks'], filename)
                dst = os.path.join(folder_path, filename)
                if os.path.exists(src) and not os.path.exists(dst):
                    shutil.copy2(src, dst)
                    added += 1
        else:
            target_m3u = playlist_path
            if not os.path.exists(playlist_path) and os.path.exists(playlist_path_8):
                target_m3u = playlist_path_8
                
            with open(target_m3u, 'a', encoding='utf-8') as f:
                if os.path.getsize(target_m3u) == 0:
                    f.write('#EXTM3U\n')
                for filename in tracks:
                    full_path = os.path.join(settings['path_tracks'], filename)
                    f.write(full_path + '\n')
                    added += 1
                    
        return jsonify({'status': 'success', 'added': added})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/playlists/<name>/remove_track', methods=['POST'])
def remove_track_from_playlist(name):
    name = clean_playlist_name(name)
    data = request.json or {}
    filename = data.get('filename', '').strip()
    
    if not filename:
        return jsonify({'status': 'error', 'message': 'Файл не указан'}), 400
    
    settings = load_settings()
    path = settings['path_playlists']
    
    playlist_path = os.path.join(path, f"{name}.m3u")
    if os.path.exists(playlist_path):
        try:
            with open(playlist_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            new_lines = []
            removed = False
            for line in lines:
                line_stripped = line.strip()
                if not line_stripped or line_stripped.startswith('#'):
                    new_lines.append(line)
                    continue
                
                line_basename = os.path.basename(line_stripped)
                if line_basename == filename or filename in line_stripped:
                    removed = True
                    continue
                new_lines.append(line)
            
            if removed:
                with open(playlist_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                return jsonify({'status': 'success'})
            else:
                return jsonify({'status': 'error', 'message': 'Трек не найден в плейлисте'}), 404
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    folder_path = os.path.join(path, name)
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        track_path = os.path.join(folder_path, filename)
        if os.path.exists(track_path):
            try:
                os.remove(track_path)
                return jsonify({'status': 'success'})
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        return jsonify({'status': 'error', 'message': 'Трек не найден в папке'}), 404
    
    return jsonify({'status': 'error', 'message': 'Плейлист не найден'}), 404

# ===== HASH CACHE =====
@app.route('/hash/files', methods=['GET'])
def list_hash_files():
    if not os.path.exists(HASH_FOLDER):
        return jsonify({'files': []})
    files = [f for f in os.listdir(HASH_FOLDER) if f.endswith('.mp3')]
    return jsonify({'files': files})

@app.route('/hash/clear', methods=['POST'])
def clear_hash():
    if os.path.exists(HASH_FOLDER):
        for f in os.listdir(HASH_FOLDER):
            fp = os.path.join(HASH_FOLDER, f)
            try:
                if os.path.isfile(fp):
                    os.remove(fp)
            except Exception:
                pass
    return jsonify({'status': 'success'})

@app.route('/hash/play/<filename>')
def play_hash_file(filename):
    return send_from_directory(HASH_FOLDER, filename)

@app.route('/hash/move_to_library', methods=['POST'])
def move_hash_to_library():
    data = request.json or {}
    filename = data.get('filename', '').strip()
    if not filename:
        return jsonify({'status': 'error', 'message': 'Файл не указан'}), 400
    
    settings = load_settings()
    src = os.path.join(HASH_FOLDER, filename)
    dst = os.path.join(settings['path_tracks'], filename)
    
    if os.path.exists(src):
        shutil.move(src, dst)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Файл не найден'}), 404

# ===== PREVIEW =====
@app.route('/preview/generate', methods=['POST'])
def generate_preview():
    data = request.json or {}
    video_id = data.get('video_id', '').strip()
    url = data.get('url', '').strip()
    title = data.get('title', 'preview').strip()
    
    if not video_id and not url:
        return jsonify({'status': 'error', 'message': 'Не указан video_id или url'}), 400
    
    preview_filename = f"preview_{video_id}.mp3" if video_id else f"preview_{hashlib.md5(url.encode()).hexdigest()[:12]}.mp3"
    preview_path = os.path.join(HASH_FOLDER, preview_filename)
    
    if os.path.exists(preview_path):
        return jsonify({'status': 'success', 'filename': preview_filename})
    
    download_url = url if url else f"https://www.youtube.com/watch?v={video_id}"
    
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        return jsonify({'status': 'error', 'message': 'ffmpeg не найден'}), 500
    
    output_template = os.path.join(HASH_FOLDER, f"preview_{video_id}.mp3" if video_id else f"preview_temp.mp3")
    
    cmd = [
        sys.executable, '-m', 'yt_dlp',
    ]
    if shutil.which('deno'):
        cmd.extend(['--js-runtimes', 'deno'])
    cmd.extend([
        '--no-update',
        '--remote-components', 'ejs:github',
        '--extractor-args', 'youtube:player_client=android',
        '--format', 'bestaudio/best',
        '-x', '--audio-format', 'mp3',
        '--ffmpeg-location', ffmpeg_path,
        '--download-sections', '*0:00-0:30',
        '-o', output_template,
        download_url
    ])
    
    env = os.environ.copy()
    env['YTDLP_NO_COOKIES'] = '1'
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=CREATION_FLAGS, timeout=60, env=env)
        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip() or f'yt-dlp error {result.returncode}'
            print(f"[PREVIEW ERROR] {error_msg}")
            return jsonify({'status': 'error', 'message': f'Ошибка загрузки превью: {error_msg[:100]}'})
        
        if video_id:
            expected_file = os.path.join(HASH_FOLDER, f"preview_{video_id}.mp3")
        else:
            for f in os.listdir(HASH_FOLDER):
                if f.startswith('preview_temp') and f.endswith('.mp3'):
                    expected_file = os.path.join(HASH_FOLDER, f)
                    break
            else:
                return jsonify({'status': 'error', 'message': 'Файл не создан'})
        
        if os.path.exists(expected_file):
            if video_id and not expected_file.endswith(f"preview_{video_id}.mp3"):
                new_path = os.path.join(HASH_FOLDER, f"preview_{video_id}.mp3")
                shutil.move(expected_file, new_path)
                expected_file = new_path
            
            if expected_file.endswith('.mp3.mp3'):
                correct_path = expected_file[:-4]
                if not os.path.exists(correct_path):
                    os.rename(expected_file, correct_path)
                    expected_file = correct_path
            
            return jsonify({'status': 'success', 'filename': os.path.basename(expected_file)})
        else:
            return jsonify({'status': 'error', 'message': 'Файл не найден после загрузки'})
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Таймаут загрузки'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/preview/play/<filename>')
def play_preview(filename):
    return send_from_directory(HASH_FOLDER, filename)

# ===== ТАКСОНОМИЯ И ЖАНРЫ =====
@app.route('/taxonomy', methods=['GET'])
def get_taxonomy():
    return jsonify({'status': 'success', 'taxonomy': MUSIC_TAXONOMY})

@app.route('/taxonomy_genres', methods=['GET'])
def get_taxonomy_genres():
    genres = set()
    for family, cat_dict in MUSIC_TAXONOMY.items():
        genres.add(family)
        for primary, subs in cat_dict.items():
            genres.add(primary)
            for sub in subs:
                genres.add(sub)
    return jsonify({'status': 'success', 'genres': sorted(list(genres))})

@app.route('/normalize_genre', methods=['POST'])
def api_normalize_genre():
    data = request.json or {}
    raw_genre = data.get('genre', '')
    normalized = normalize_genre(raw_genre)
    return jsonify({'status': 'success', 'normalized': normalized})

# ===== ОПРЕДЕЛЕНИЕ ЖАНРА =====
@app.route('/detect_genre', methods=['POST'])
def detect_genre():
    data = request.json or {}
    artist = data.get('artist', '').strip()
    title = data.get('title', '').strip()
    
    if not artist and not title:
        return jsonify({'status': 'error', 'message': 'Не указан артист или название'}), 400
    
    try:
        query = f"{artist} {title}".strip()
        url = f"https://musicbrainz.org/ws/2/recording/?query={urllib.parse.quote(query)}&fmt=json&limit=5"
        req = urllib.request.Request(url, headers={'User-Agent': 'FollMuz/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
            
        if 'recordings' in result and len(result['recordings']) > 0:
            recording = result['recordings'][0]
            if 'releases' in recording and len(recording['releases']) > 0:
                release = recording['releases'][0]
                if 'media' in release:
                    for media in release['media']:
                        if 'tracks' in media:
                            for track in media['tracks']:
                                if 'title' in track:
                                    return jsonify({'status': 'success', 'genre': 'Unknown'})
            
            if 'artist-credit' in recording:
                for credit in recording['artist-credit']:
                    if 'artist' in credit:
                        artist_id = credit['artist'].get('id')
                        if artist_id:
                            artist_url = f"https://musicbrainz.org/ws/2/artist/{artist_id}?inc=genres&fmt=json"
                            req = urllib.request.Request(artist_url, headers={'User-Agent': 'FollMuz/1.0'})
                            with urllib.request.urlopen(req, timeout=5) as response:
                                artist_data = json.loads(response.read().decode('utf-8'))
                                if 'genres' in artist_data and len(artist_data['genres']) > 0:
                                    genre = artist_data['genres'][0].get('name', 'Unknown')
                                    return jsonify({'status': 'success', 'genre': genre})
    except Exception as e:
        print(f"[GENRE DETECT ERROR] {e}")
    
    return jsonify({'status': 'success', 'genre': 'Unknown'})

# ===== ПОИСК АРТИСТОВ =====
@app.route('/search_artists', methods=['GET'])
def search_artists_api():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'status': 'success', 'artists': []})
    
    try:
        url = f"https://musicbrainz.org/ws/2/artist/?query={urllib.parse.quote(query)}&fmt=json&limit=10"
        req = urllib.request.Request(url, headers={'User-Agent': 'FollMuz/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        artists = []
        if 'artists' in result:
            for artist in result['artists']:
                name = artist.get('name', '')
                if name:
                    artists.append(name)
        
        return jsonify({'status': 'success', 'artists': artists})
    except Exception as e:
        print(f"[ARTIST SEARCH ERROR] {e}")
        return jsonify({'status': 'success', 'artists': []})

@app.route('/search_artists_online', methods=['GET'])
def search_artists_online():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'status': 'success', 'artists': []})
    results = set()
    try:
        url = f"https://musicbrainz.org/ws/2/artist/?query={urllib.parse.quote(query)}&fmt=json&limit=15"
        req = urllib.request.Request(url, headers={'User-Agent': 'FollMuz/2.0'})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            for art in data.get('artists', []):
                name = art.get('name')
                if name:
                    results.add(name)
    except Exception:
        pass
    try:
        yt_res = yt_search(f"{query} music artist", limit=10, music_only=True)
        for t in yt_res:
            art = t.get('artist')
            if art and art.lower() != 'unknown':
                results.add(art)
    except Exception:
        pass
    return jsonify({'status': 'success', 'artists': sorted(list(results))[:20]})

@app.route('/search_genres_online', methods=['GET'])
def search_genres_online():
    query = request.args.get('q', '').lower().strip()
    matched = set()
    for family, categories in MUSIC_TAXONOMY.items():
        if not query or query in family.lower():
            matched.add(family)
        for primary, subgenres in categories.items():
            if not query or query in primary.lower():
                matched.add(primary)
            for sub in subgenres:
                if not query or query in sub.lower() or query in family.lower() or query in primary.lower():
                    matched.add(sub)
    return jsonify({'status': 'success', 'genres': sorted(list(matched))[:25]})

@app.route('/update_favorites', methods=['POST'])
def update_favorites():
    data = request.json or {}
    settings = load_settings()
    if 'favorite_artists' in data:
        settings['favorite_artists'] = data['favorite_artists']
    if 'favorite_genres' in data:
        settings['favorite_genres'] = data['favorite_genres']
    write_settings(settings)
    return jsonify({'status': 'success', 'settings': settings})

# ===== TELEGRAM BOT CONTROL =====
BOT_PROCESS = None

@app.route('/bot_status', methods=['GET'])
def bot_status():
    global BOT_PROCESS
    if BOT_PROCESS and BOT_PROCESS.poll() is None:
        return jsonify({'status': 'running'})
    return jsonify({'status': 'stopped'})

@app.route('/bot_start', methods=['POST'])
def bot_start():
    global BOT_PROCESS
    try:
        bot_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bot', 'bot.py')
        if not os.path.exists(bot_script):
            return jsonify({'status': 'error', 'message': 'bot.py не найден'}), 404
        
        BOT_PROCESS = subprocess.Popen(
            [sys.executable, bot_script],
            creationflags=CREATION_FLAGS
        )
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/bot_stop', methods=['POST'])
def bot_stop():
    global BOT_PROCESS
    if BOT_PROCESS and BOT_PROCESS.poll() is None:
        if sys.platform == 'win32':
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(BOT_PROCESS.pid)],
                          capture_output=True, creationflags=CREATION_FLAGS)
        BOT_PROCESS = None
    return jsonify({'status': 'success'})

@app.route('/shutdown', methods=['POST'])
def shutdown():
    global BOT_PROCESS
    if BOT_PROCESS and BOT_PROCESS.poll() is None:
        if sys.platform == 'win32':
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(BOT_PROCESS.pid)],
                          capture_output=True, creationflags=CREATION_FLAGS)
    os._exit(0)

# ===== CATALOG ENGINE & BEHAVIORAL SIGNALS =====
@app.route('/api/catalog/search', methods=['POST'])
def api_catalog_search():
    data = request.json or {}
    query = data.get('query', '').strip()
    limit = data.get('limit', 12)
    results = CatalogEngine.catalog_search(query, limit)
    return jsonify({'status': 'success', 'tracks': results})

@app.route('/api/catalog/discovery', methods=['POST'])
def api_catalog_discovery():
    data = request.json or {}
    seed = data.get('seed', '').strip()
    limit = data.get('limit', 10)
    results = CatalogEngine.semantic_discovery(seed, limit)
    return jsonify({'status': 'success', 'tracks': results})

@app.route('/api/catalog/feed', methods=['GET'])
def api_catalog_feed():
    limit = int(request.args.get('limit', 15))
    results = CatalogEngine.personal_feed(limit)
    profile = build_user_taste_profile()
    return jsonify({'status': 'success', 'feed': results, 'profile': profile})

@app.route('/api/user/event', methods=['POST'])
def api_user_event():
    data = request.json or {}
    event_type = data.get('event_type')
    track_id = data.get('track_id')
    metadata = data.get('metadata', {})
    if not event_type or not track_id:
        return jsonify({'status': 'error', 'message': 'Missing parameters'}), 400
    log_user_event(event_type, recording_id=track_id, metadata=metadata)
    return jsonify({'status': 'success'})

@app.route('/api/playback/start', methods=['POST'])
def api_playback_start():
    data = request.json or {}
    recording_id = data.get('recording_id')
    video_id = data.get('video_id')
    surface = data.get('surface', 'home')
    if video_id:
        log_user_event('play', recording_id=recording_id, track_id=video_id, metadata={'surface': surface})
    return jsonify({'status': 'success', 'playback': {'recording_id': recording_id, 'source': 'youtube', 'video_id': video_id, 'surface': surface}})

if __name__ == '__main__':
    app.run(port=5000, threaded=True)
