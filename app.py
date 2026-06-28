from flask import Flask, render_template, request, jsonify, send_from_directory, Response, send_file
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

app = Flask(__name__)
DOWNLOAD_FOLDER = 'downloads'
SETTINGS_FILE = 'settings.json'
HASH_FOLDER = 'hash_cache'

CREATION_FLAGS = 0
if sys.platform == 'win32':
    CREATION_FLAGS = subprocess.CREATE_NO_WINDOW

# Ensure hash folder exists
os.makedirs(HASH_FOLDER, exist_ok=True)

def find_ffmpeg():
    ffmpeg = shutil.which('ffmpeg')
    if ffmpeg:
        return os.path.dirname(ffmpeg)
    common_paths = [
        os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin'),
        r'C:\ProgramData\chocolatey\bin',
        r'C:\ffmpeg\bin',
        r'C:\ffmpeg',
    ]
    for path in common_paths:
        if os.path.exists(path):
            return path
    return None

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        'path_tracks': 'C:/Users/Smixr/Music',
        'path_playlists': 'C:/Users/Smixr/Music/Playlists',
        'player_width': 450
    }

def write_settings(settings):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_settings', methods=['GET'])
def get_settings():
    settings = load_settings()
    tg_token = ''
    tg_token_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tg_token.txt')
    if os.path.exists(tg_token_file):
        with open(tg_token_file, 'r', encoding='utf-8') as f:
            tg_token = f.read().strip()
    settings['tg_token'] = tg_token
    return jsonify(settings)

@app.route('/track_info/<filename>')
def get_track_info(filename):
    settings = load_settings()
    filepath = os.path.join(settings['path_tracks'], filename)
    info = {'title': filename, 'artist': 'Unknown'}
    try:
        audio = ID3(filepath)
        info['title'] = str(audio.get('TIT2', filename))
        info['artist'] = str(audio.get('TPE1', 'Unknown'))
    except:
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
                return Response(tag.data, mimetype='image/jpeg')
    except:
        pass
    return send_from_directory('static', 'default_cover.png')

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url', '').strip()
    artist = data.get('artist', '').strip()
    title = data.get('title', '').strip()
    to_hash = data.get('to_hash', False)
    
    settings = load_settings()
    path = HASH_FOLDER if to_hash else settings['path_tracks']
    if not os.path.exists(path):
        os.makedirs(path)
        
    download_target = url
    if not url:
        if artist and title:
            download_target = f"ytsearch1:{artist} - {title}"
        elif artist:
            download_target = f"ytsearch1:{artist}"
        elif title:
            download_target = f"ytsearch1:{title}"
        else:
            return jsonify({'status': 'error', 'message': 'Не указана ссылка или поисковый запрос'}), 400

    # Use explicit .mp3 extension to avoid double extension issues
    if artist and title:
        filename_template = f"{artist} - {title}.mp3"
    elif title:
        filename_template = f"{title}.mp3"
    else:
        filename_template = "%(title)s.%(ext)s"  # Keep %(ext)s for generic case
        
    output_path = os.path.join(path, filename_template)
    
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        return jsonify({'status': 'error', 'message': 'ffmpeg не найден. Установите ffmpeg'}), 500

    cmd = [sys.executable, '-m', 'yt_dlp', '-x', '--audio-format', 'mp3', '--ffmpeg-location', ffmpeg_path, '-o', output_path, download_target]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=CREATION_FLAGS)
        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip() or f'yt-dlp error {result.returncode}'
            return jsonify({'status': 'error', 'message': error_msg}), 500
        
        # Post-process: fix double extension if yt-dlp added .mp3 to .mp3
        if artist and title:
            expected_file = os.path.join(path, f"{artist} - {title}.mp3")
            double_ext_file = os.path.join(path, f"{artist} - {title}.mp3.mp3")
            if os.path.exists(double_ext_file) and not os.path.exists(expected_file):
                os.rename(double_ext_file, expected_file)
        elif title:
            expected_file = os.path.join(path, f"{title}.mp3")
            double_ext_file = os.path.join(path, f"{title}.mp3.mp3")
            if os.path.exists(double_ext_file) and not os.path.exists(expected_file):
                os.rename(double_ext_file, expected_file)
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def format_duration(seconds):
    if not seconds:
        return "--:--"
    try:
        seconds = int(seconds)
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}:{secs:02d}"
    except:
        return "--:--"

def yt_search(query, limit=12, music_only=True):
    if music_only and not query.startswith("ytsearch"):
        query = f"{query} music audio"
    ydl_opts = {
        'extract_flat': True,
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'playlistend': limit,
        'default_search': 'ytsearch',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            result = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
            tracks = []
            if 'entries' in result:
                for entry in result['entries']:
                    if not entry:
                        continue
                    video_id = entry.get('id')
                    title = (entry.get('title') or '').lower()
                    channel = (entry.get('channel') or entry.get('uploader') or '').lower()
                    is_music = any(kw in title for kw in ['music', 'audio', 'song', 'remix', 'cover', 'live', 'ft.', 'feat', 'official', 'mv', 'lyric']) or \
                               any(kw in channel for kw in ['music', 'vevo', 'official', 'topic', 'records'])
                    if music_only and not is_music:
                        continue
                    tracks.append({
                        'id': video_id,
                        'title': entry.get('title') or 'Unknown Title',
                        'artist': entry.get('channel') or entry.get('uploader') or 'Unknown Artist',
                        'url': entry.get('url') or f"https://www.youtube.com/watch?v={video_id}" if video_id else '',
                        'duration': format_duration(entry.get('duration')),
                        'thumbnail': entry.get('thumbnail') or (f"https://img.youtube.com/vi/{video_id}/0.jpg" if video_id else '/static/default_cover.png')
                    })
            return tracks
        except Exception as e:
            print("Search error:", e)
            return []

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
    
    results = yt_search(query, limit=limit, music_only=True)
    return jsonify({'status': 'success', 'tracks': results})

@app.route('/recommendations', methods=['GET'])
def get_recommendations():
    settings = load_settings()
    path = settings['path_tracks']
    if not os.path.exists(path):
        os.makedirs(path)
        
    mp3_files = [f for f in os.listdir(path) if f.endswith('.mp3')]
    artists = []
    titles = []
    
    for filename in mp3_files:
        filepath = os.path.join(path, filename)
        try:
            audio = ID3(filepath)
            artist = str(audio.get('TPE1', ''))
            title = str(audio.get('TIT2', ''))
            if artist and artist.lower() != 'unknown':
                artists.append(artist.strip())
            if title and title.lower() != 'unknown':
                titles.append(title.strip())
        except:
            name, _ = os.path.splitext(filename)
            if ' - ' in name:
                parts = name.split(' - ')
                if parts[0].strip():
                    artists.append(parts[0].strip())
                if len(parts) > 1 and parts[1].strip():
                    titles.append(parts[1].strip())
                    
    artist_counts = Counter(artists)
    top_artists = [item[0] for item in artist_counts.most_common(5)]
    
    all_tracks = []
    used_ids = set()
    
    queries = []
    if top_artists:
        fav = random.choice(top_artists)
        queries = [
            f"{fav} similar artists music",
            f"{fav} best songs",
            f"{fav} genre music mix",
            "music recommendations 2025 2026",
        ]
        if len(top_artists) > 1:
            queries.append(f"{random.choice(top_artists)} {random.choice(top_artists)} music")
    else:
        queries = [
            "synthwave darksynth cyberpunk music",
            "electronic music mix 2025",
            "indie music playlist",
            "chill music compilation",
        ]
    
    for q in queries:
        results = yt_search(q, limit=8)
        for t in results:
            vid_id = t.get('id', '')
            if vid_id and vid_id not in used_ids:
                used_ids.add(vid_id)
                all_tracks.append(t)
        if len(all_tracks) >= 40:
            break
    
    random.shuffle(all_tracks)
    all_tracks = all_tracks[:40]
    
    return jsonify({
        'status': 'success',
        'taste_profile': top_artists,
        'tracks': all_tracks
    })

@app.route('/files')
def list_files():
    settings = load_settings()
    path = settings['path_tracks']
    if not os.path.exists(path):
        os.makedirs(path)
    files = [f for f in os.listdir(path) if f.endswith('.mp3')]
    return jsonify({'files': files})

@app.route('/play/<filename>')
def play_file(filename):
    settings = load_settings()
    return send_from_directory(settings['path_tracks'], filename)

@app.route('/save_settings', methods=['POST'])
def save_settings_api():
    write_settings(request.json)
    return jsonify({'status': 'success'})

# ===== PLAYLISTS =====
@app.route('/playlists/list', methods=['GET'])
def list_playlists():
    settings = load_settings()
    path = settings['path_playlists']
    if not os.path.exists(path):
        os.makedirs(path)
    
    playlists = []
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        if os.path.isdir(item_path):
            # Folder
            files = [f for f in os.listdir(item_path) if f.endswith('.mp3')]
            playlists.append({
                'name': item,
                'type': 'folder',
                'count': len(files),
                'path': item
            })
        elif item.endswith('.m3u') or item.endswith('.m3u8'):
            # Count tracks in .m3u file
            count = 0
            try:
                with open(item_path, 'r', encoding='utf-8') as f:
                    lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]
                    count = len(lines)
            except:
                pass
            playlists.append({
                'name': os.path.splitext(item)[0],
                'type': 'playlist',
                'count': count,
                'path': item
            })
    
    return jsonify({'playlists': playlists})

@app.route('/playlists/create', methods=['POST'])
def create_playlist():
    data = request.json or {}
    name = data.get('name', '').strip()
    ptype = data.get('type', 'folder')
    
    if not name:
        return jsonify({'status': 'error', 'message': 'Имя не указано'}), 400
    
    settings = load_settings()
    path = settings['path_playlists']
    if not os.path.exists(path):
        os.makedirs(path)
    
    if ptype == 'folder':
        folder_path = os.path.join(path, name)
        if os.path.exists(folder_path):
            return jsonify({'status': 'error', 'message': 'Папка уже существует'}), 400
        os.makedirs(folder_path)
    else:
        playlist_path = os.path.join(path, f"{name}.m3u")
        if os.path.exists(playlist_path):
            return jsonify({'status': 'error', 'message': 'Плейлист уже существует'}), 400
        with open(playlist_path, 'w', encoding='utf-8') as f:
            f.write('#EXTM3U\n')
    
    return jsonify({'status': 'success'})

@app.route('/playlists/delete', methods=['POST'])
def delete_playlist():
    data = request.json or {}
    name = data.get('name', '').strip()
    ptype = data.get('type', 'folder')
    
    if not name:
        return jsonify({'status': 'error', 'message': 'Имя не указано'}), 400
    
    settings = load_settings()
    path = settings['path_playlists']
    
    if ptype == 'folder':
        folder_path = os.path.join(path, name)
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            shutil.rmtree(folder_path)
            return jsonify({'status': 'success'})
    else:
        playlist_path = os.path.join(path, f"{name}.m3u")
        if os.path.exists(playlist_path):
            os.remove(playlist_path)
            return jsonify({'status': 'success'})
    
    return jsonify({'status': 'error', 'message': 'Не найдено'}), 404

@app.route('/playlists/<name>/tracks', methods=['GET'])
def get_playlist_tracks(name):
    settings = load_settings()
    path = settings['path_playlists']
    
    folder_path = os.path.join(path, name)
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        files = [f for f in os.listdir(folder_path) if f.endswith('.mp3')]
        return jsonify({'tracks': files, 'type': 'folder'})
    
    playlist_path = os.path.join(path, f"{name}.m3u")
    if os.path.exists(playlist_path):
        with open(playlist_path, 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]
        return jsonify({'tracks': [os.path.basename(l) for l in lines], 'type': 'playlist'})
    
    return jsonify({'tracks': [], 'type': 'unknown'})

@app.route('/playlists/<name>/add_track', methods=['POST'])
def add_track_to_playlist(name):
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
    if os.path.exists(playlist_path):
        with open(playlist_path, 'a', encoding='utf-8') as f:
            f.write(os.path.join(settings['path_tracks'], filename) + '\n')
        return jsonify({'status': 'success'})
    
    return jsonify({'status': 'error', 'message': 'Плейлист не найден'}), 404

@app.route('/playlists/add_tracks', methods=['POST'])
def add_tracks_to_playlist():
    """Add multiple tracks to a playlist"""
    data = request.json or {}
    name = data.get('name', '').strip()
    tracks = data.get('tracks', [])
    
    if not name:
        return jsonify({'status': 'error', 'message': 'Имя плейлиста не указано'}), 400
    if not tracks:
        return jsonify({'status': 'error', 'message': 'Треки не указаны'}), 400
    
    settings = load_settings()
    path = settings['path_playlists']
    
    # Check if it's a folder
    folder_path = os.path.join(path, name)
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        added = 0
        for filename in tracks:
            src = os.path.join(settings['path_tracks'], filename)
            dst = os.path.join(folder_path, filename)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                added += 1
        return jsonify({'status': 'success', 'added': added})
    
    # It's a .m3u playlist
    playlist_path = os.path.join(path, f"{name}.m3u")
    if os.path.exists(playlist_path):
        added = 0
        with open(playlist_path, 'a', encoding='utf-8') as f:
            for filename in tracks:
                f.write(os.path.join(settings['path_tracks'], filename) + '\n')
                added += 1
        return jsonify({'status': 'success', 'added': added})
    
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
            except:
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

# ===== PREVIEW (30-second snippets) =====
@app.route('/preview/generate', methods=['POST'])
def generate_preview():
    """Generate a 30-second preview of a track and save to hash folder"""
    data = request.json or {}
    video_id = data.get('video_id', '').strip()
    url = data.get('url', '').strip()
    title = data.get('title', 'preview').strip()
    
    if not video_id and not url:
        return jsonify({'status': 'error', 'message': 'Не указан video_id или url'}), 400
    
    # Check if preview already exists
    preview_filename = f"preview_{video_id}.mp3" if video_id else f"preview_{hashlib.md5(url.encode()).hexdigest()[:12]}.mp3"
    preview_path = os.path.join(HASH_FOLDER, preview_filename)
    
    if os.path.exists(preview_path):
        return jsonify({'status': 'success', 'filename': preview_filename})
    
    # Download URL
    download_url = url if url else f"https://www.youtube.com/watch?v={video_id}"
    
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        return jsonify({'status': 'error', 'message': 'ffmpeg не найден'}), 500
    
    # Download first 30 seconds using yt-dlp with download-sections
    # Use explicit .mp3 extension
    output_template = os.path.join(HASH_FOLDER, f"preview_{video_id}.mp3" if video_id else f"preview_temp.mp3")
    
    cmd = [
        sys.executable, '-m', 'yt_dlp',
        '-x', '--audio-format', 'mp3',
        '--ffmpeg-location', ffmpeg_path,
        '--download-sections', '*0:00-0:30',  # Limit to first 30 seconds
        '-o', output_template,
        download_url
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=CREATION_FLAGS, timeout=60)
        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip() or f'yt-dlp error {result.returncode}'
            print(f"Preview generation error: {error_msg}")
            return jsonify({'status': 'error', 'message': f'Ошибка загрузки превью: {error_msg[:100]}'}), 500
        
        # Find the generated file
        if video_id:
            expected_file = os.path.join(HASH_FOLDER, f"preview_{video_id}.mp3")
        else:
            # Find any preview_temp.mp3
            for f in os.listdir(HASH_FOLDER):
                if f.startswith('preview_temp') and f.endswith('.mp3'):
                    expected_file = os.path.join(HASH_FOLDER, f)
                    break
            else:
                return jsonify({'status': 'error', 'message': 'Файл не создан'}), 500
        
        if os.path.exists(expected_file):
            # Rename to standard preview name if needed
            if video_id and not expected_file.endswith(f"preview_{video_id}.mp3"):
                new_path = os.path.join(HASH_FOLDER, f"preview_{video_id}.mp3")
                shutil.move(expected_file, new_path)
                expected_file = new_path
            
            # Fix double extension if yt-dlp added .mp3 to .mp3
            if expected_file.endswith('.mp3.mp3'):
                correct_path = expected_file[:-4]  # Remove last .mp3
                if not os.path.exists(correct_path):
                    os.rename(expected_file, correct_path)
                    expected_file = correct_path
            
            return jsonify({'status': 'success', 'filename': os.path.basename(expected_file)})
        else:
            return jsonify({'status': 'error', 'message': 'Файл не найден после загрузки'}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'status': 'error', 'message': 'Таймаут загрузки'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/preview/play/<filename>')
def play_preview(filename):
    """Play a preview file from hash folder"""
    return send_from_directory(HASH_FOLDER, filename)

# ===== BOT (removed toggle but keep endpoints for compatibility) =====
BOT_PROCESS = None

def get_bot_pid_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bot', 'bot.pid')

@app.route('/shutdown', methods=['POST'])
def shutdown():
    global BOT_PROCESS
    if BOT_PROCESS and BOT_PROCESS.poll() is None:
        if sys.platform == 'win32':
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(BOT_PROCESS.pid)],
                          capture_output=True, creationflags=CREATION_FLAGS)
    os._exit(0)

if __name__ == '__main__':
    app.run(port=5000)
