# src/routes/playlist_bp.py
from flask import Blueprint, request, jsonify
import os
from src.app_context import load_settings

playlist_bp = Blueprint('playlist_bp', __name__)

@playlist_bp.route('/playlists/list', methods=['GET'])
def list_playlists():
    settings = load_settings()
    path = settings['path_playlists']
    if not os.path.exists(path):
        os.makedirs(path)
    
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
                        'name': entry.name,
                        'type': 'folder',
                        'count': count,
                        'path': entry.name
                    })
                elif entry.is_file() and (entry.name.endswith('.m3u') or entry.name.endswith('.m3u8')):
                    playlists.append({
                        'name': entry.name,
                        'type': 'm3u',
                        'count': 0,
                        'path': entry.name
                    })
    except Exception as e:
        print(f"[PLAYLISTS ERROR] {e}")
    return jsonify({'playlists': playlists})
