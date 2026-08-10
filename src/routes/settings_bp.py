# src/routes/settings_bp.py
from flask import Blueprint, request, jsonify, send_from_directory
import os
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from src.app_context import load_settings, write_settings
from src.taxonomy import MUSIC_TAXONOMY, normalize_genre, infer_genre_from_filename

settings_bp = Blueprint('settings_bp', __name__)

@settings_bp.route('/get_settings', methods=['GET'])
def get_settings_route():
    return jsonify(load_settings())

@settings_bp.route('/save_settings', methods=['POST'])
def save_settings_route():
    data = request.json or {}
    write_settings(data)
    return jsonify({'status': 'success'})

@settings_bp.route('/track_info/<filename>')
def track_info(filename):
    settings = load_settings()
    filepath = os.path.join(settings['path_tracks'], filename)
    if not os.path.exists(filepath):
        return jsonify({'status': 'error', 'message': 'Файл не найден'}), 404
    try:
        audio = MP3(filepath, ID3=ID3)
        duration = int(audio.info.length) if audio.info else 0
        title = filename
        artist = "Unknown Artist"
        album = "Unknown Album"
        genre = ""
        
        if audio.tags:
            title = str(audio.tags.get('TIT2', filename))
            artist = str(audio.tags.get('TPE1', 'Unknown Artist'))
            album = str(audio.tags.get('TALB', 'Unknown Album'))
            g_tag = str(audio.tags.get('TCON', ''))
            if g_tag and g_tag.lower() != 'unknown':
                genre = g_tag
            
        inf = infer_genre_from_filename(filename)
        
        return jsonify({
            'status': 'success',
            'filename': filename,
            'title': title,
            'artist': artist,
            'album': album,
            'genre': genre,
            'taxonomy': inf,
            'duration': duration
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@settings_bp.route('/cover/<filename>')
def get_cover(filename):
    settings = load_settings()
    filepath = os.path.join(settings['path_tracks'], filename)
    if not os.path.exists(filepath):
        return jsonify({'status': 'error', 'message': 'Файл не найден'}), 404
    try:
        audio = MP3(filepath, ID3=ID3)
        if audio.tags:
            for tag in audio.tags.values():
                if isinstance(tag, APIC):
                    cover_data = tag.data
                    mime = tag.mime or 'image/jpeg'
                    from flask import Response
                    return Response(cover_data, mimetype=mime)
    except Exception:
        pass
    return send_from_directory('static', 'default_cover.png')

@settings_bp.route('/taxonomy', methods=['GET'])
def get_taxonomy():
    return jsonify(MUSIC_TAXONOMY)

@settings_bp.route('/taxonomy_genres', methods=['GET'])
def get_taxonomy_genres():
    genres = []
    for family, subgenres in MUSIC_TAXONOMY.items():
        for sub in subgenres:
            genres.append(f"{family} > {sub}")
    return jsonify(genres)

@settings_bp.route('/normalize_genre', methods=['POST'])
def normalize_genre_route():
    data = request.json or {}
    genre = data.get('genre', '')
    return jsonify(normalize_genre(genre))

@settings_bp.route('/detect_genre', methods=['POST'])
def detect_genre_route():
    data = request.json or {}
    filename = data.get('filename', '')
    return jsonify(infer_genre_from_filename(filename))
