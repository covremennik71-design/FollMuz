# src/routes/catalog_bp.py
from flask import Blueprint, request, jsonify
import datetime
from src.catalog_engine import CatalogEngine, log_user_event, build_user_taste_profile
from src.api.youtube_search import yt_search

catalog_bp = Blueprint('catalog_bp', __name__)

@catalog_bp.route('/search_catalog', methods=['POST'])
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

@catalog_bp.route('/recommendations', methods=['GET'])
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

        return jsonify({
            'status': 'success',
            'surface': surface,
            'generated_at': datetime.datetime.utcnow().isoformat() + 'Z',
            'items': items,
            'tracks': items
        })
    except Exception as e:
        print(f"[RECOMMENDATIONS ERROR] {e}")
        return jsonify({'status': 'success', 'surface': 'home', 'items': [], 'tracks': []})

@catalog_bp.route('/api/catalog/search', methods=['POST'])
def api_catalog_search():
    data = request.json or {}
    query = data.get('query', '').strip()
    limit = data.get('limit', 12)
    results = CatalogEngine.catalog_search(query, limit)
    return jsonify({'status': 'success', 'tracks': results})

@catalog_bp.route('/api/catalog/discovery', methods=['POST'])
def api_catalog_discovery():
    data = request.json or {}
    seed = data.get('seed', '').strip()
    limit = data.get('limit', 10)
    results = CatalogEngine.semantic_discovery(seed, limit)
    return jsonify({'status': 'success', 'tracks': results})

@catalog_bp.route('/api/catalog/feed', methods=['GET'])
def api_catalog_feed():
    limit = int(request.args.get('limit', 15))
    results = CatalogEngine.personal_feed(limit)
    profile = build_user_taste_profile()
    return jsonify({'status': 'success', 'feed': results, 'profile': profile})

@catalog_bp.route('/api/user/event', methods=['POST'])
def api_user_event():
    data = request.json or {}
    event_type = data.get('event_type')
    track_id = data.get('track_id')
    metadata = data.get('metadata', {})
    if not event_type or not track_id:
        return jsonify({'status': 'error', 'message': 'Missing parameters'}), 400
    log_user_event(event_type, recording_id=track_id, metadata=metadata)
    return jsonify({'status': 'success'})

@catalog_bp.route('/api/playback/start', methods=['POST'])
def api_playback_start():
    data = request.json or {}
    recording_id = data.get('recording_id')
    video_id = data.get('video_id')
    surface = data.get('surface', 'home')
    if video_id:
        log_user_event('play', recording_id=recording_id, track_id=video_id, metadata={'surface': surface})
    return jsonify({'status': 'success', 'playback': {'recording_id': recording_id, 'source': 'youtube', 'video_id': video_id, 'surface': surface}})
