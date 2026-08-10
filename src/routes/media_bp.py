# src/routes/media_bp.py
from flask import Blueprint, jsonify, send_from_directory
import os
from src.app_context import load_settings

media_bp = Blueprint('media_bp', __name__)

@media_bp.route('/files')
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

@media_bp.route('/play/<filename>')
def play_file(filename):
    settings = load_settings()
    return send_from_directory(settings['path_tracks'], filename)
