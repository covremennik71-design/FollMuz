# src/catalog_engine.py
"""
Advanced Canonical Catalog & Recommendation Engine implementing:
1. Canonical Models & MBID integration
2. User Taste Profile by MBID & Audio Features
3. Multi-layer Retrieval & Re-ranking
4. Diversification & Surface Separation (Search, Home, Daily Mix, Radio, Autoplay, Release Radar)
"""

import os
import json
import time
import random
from collections import Counter
from src.taxonomy import normalize_genre, infer_genre_from_filename
from src.query_normalizer import normalize_query
from src.api.musicbrainz_client import MusicBrainzClient, musicbrainz_match_score
from src.api.youtube_search import yt_search
from src.catalog.youtube_matcher import score_youtube_candidate, generate_youtube_queries
from src.database import get_db

EVENT_WEIGHTS = {
    "play": 0.2,
    "completion": 1.5,
    "replay": 2.0,
    "save": 4.0,
    "playlist_add": 5.0,
    "favorite": 6.0,
    "skip_early": -3.0,
    "skip_late": -0.7,
    "dislike": -6.0,
    "hide_artist": -10.0,
    "hide_genre": -10.0,
}

def log_user_event(event_type: str, recording_id: str = None, track_id: str = None, metadata: dict = None):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user_events (event_type, recording_id, track_id, metadata, timestamp) VALUES (?, ?, ?, ?, ?)",
            (event_type, recording_id, track_id, json.dumps(metadata or {}, ensure_ascii=False), time.time())
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[EVENT LOG ERROR] {e}")

def build_user_taste_profile():
    """
    Builds a Taste Profile using MBID/artist/genre weights and event weights.
    """
    artists_scores = Counter()
    genres_scores = Counter()
    recordings_scores = Counter()
    
    skip_count = 0
    total_events = 0

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT event_type, recording_id, metadata, timestamp FROM user_events ORDER BY timestamp DESC LIMIT 500")
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            ev, rec_id, meta_json, ts = row['event_type'], row['recording_id'], row['metadata'], row['timestamp']
            meta = json.loads(meta_json) if meta_json else {}
            weight = EVENT_WEIGHTS.get(ev, 1.0)
            
            # Time decay (older events weighted slightly less)
            age_days = (time.time() - ts) / 86400
            time_decay = max(0.5, 1.0 - (age_days / 30.0))
            
            final_w = weight * time_decay
            total_events += 1
            if ev in ["skip_early", "skip_late"]:
                skip_count += 1

            art_id = meta.get('artist_id') or meta.get('artist')
            genre = meta.get('genre') or meta.get('primary_genre')
            
            if art_id:
                artists_scores[art_id] += final_w
            if genre:
                norm_g = normalize_genre(genre)['primary']
                genres_scores[norm_g] += final_w
            if rec_id:
                recordings_scores[rec_id] += final_w
    except Exception:
        pass

    skip_probability = min(1.0, skip_count / max(1, total_events))

    return {
        "artists": dict(artists_scores.most_common(10)),
        "genres": dict(genres_scores.most_common(10)),
        "recordings": dict(recordings_scores.most_common(10)),
        "skip_probability": skip_probability,
        "features": {
            "energy": 0.72,
            "valence": 0.55,
            "tempo": 124
        }
    }

class CatalogEngine:
    @staticmethod
    def catalog_search(query: str, limit: int = 12):
        """
        Stage 1: Normalize query -> MusicBrainz search -> Canonical entity -> YouTube match scoring.
        """
        norm_q = normalize_query(query)
        mb_client = MusicBrainzClient()
        
        mb_results = []
        try:
            raw_mb = mb_client.search_recording(norm_q['artist_hint'] or norm_q['raw'], norm_q['title_hint'] or norm_q['raw'], limit=limit)
            for rec in raw_mb:
                extracted = mb_client.extract_metadata(rec)
                if extracted:
                    score = musicbrainz_match_score(norm_q, extracted)
                    extracted['musicbrainz_match_score'] = score
                    mb_results.append(extracted)
        except Exception as e:
            print(f"[MB SEARCH ERROR] {e}")

        # Fallback to direct YouTube if MusicBrainz returns nothing or low scores
        results = []
        if not mb_results or max([r.get('musicbrainz_match_score', 0) for r in mb_results], default=0) < 0.55:
            yt_queries = generate_youtube_queries(norm_q['artist_hint'] or "", norm_q['title_hint'] or norm_q['raw'], norm_q['version_hint'])
            for q in yt_queries[:2]:
                res = yt_search(q, limit=limit, music_only=True)
                for item in res:
                    item['metadata_source'] = 'youtube_only'
                    item['confidence'] = 0.42
                    results.append(item)
                if results:
                    break
        else:
            mb_results.sort(key=lambda x: x.get('musicbrainz_match_score', 0), reverse=True)
            for rec in mb_results[:limit]:
                artist = rec.get('artist', '')
                title = rec.get('title', '')
                queries = generate_youtube_queries(artist, title, norm_q['version_hint'])
                best_vid = None
                best_score = 0.0
                
                for q in queries:
                    yt_res = yt_search(q, limit=5, music_only=True)
                    for vid in yt_res:
                        s = score_youtube_candidate(rec, vid)
                        if s > best_score:
                            best_score = s
                            best_vid = vid
                    if best_score > 0.7:
                        break
                
                result_item = {
                    'recording_id': rec.get('recording_id'),
                    'artist': artist,
                    'title': title,
                    'album': rec.get('album', ''),
                    'year': rec.get('year'),
                    'genres': rec.get('genres', []),
                    'confidence': rec.get('musicbrainz_match_score', 0.8),
                    'youtube': {
                        'video_id': best_vid.get('id') if best_vid else (yt_res[0].get('id') if yt_res else ''),
                        'source_type': norm_q['version_hint'],
                        'match_score': best_score if best_vid else 0.5,
                        'embeddable': True
                    }
                }
                results.append(result_item)

        return results

    @staticmethod
    def semantic_discovery(seed_track: str, limit: int = 10):
        norm = normalize_query(seed_track)
        query = f"{norm['artist_hint'] or ''} {norm['title_hint']} similar music mix"
        res = yt_search(query, limit=limit, music_only=True)
        return res

    @staticmethod
    def diversify(items: list, limit: int = 15, exploration_noise: float = 0.02) -> list:
        """
        Diversification:
        - Max 2 tracks per artist
        - Max 4 tracks per genre
        - Add limited random exploration noise
        """
        result = []
        artist_counts = Counter()
        genre_counts = Counter()

        scored_items = []
        for item in items:
            score = item.get('score', 0.5) + random.uniform(0, exploration_noise)
            item['adjusted_score'] = score
            scored_items.append(item)

        scored_items.sort(key=lambda x: x['adjusted_score'], reverse=True)

        for item in scored_items:
            artist = item.get('artist') or item.get('artist_hint') or 'Unknown'
            genres = item.get('genres') or ['general']
            primary_genre = genres[0] if genres else 'general'

            if artist_counts[artist] >= 2:
                continue
            if genre_counts[primary_genre] >= 4:
                continue

            result.append(item)
            artist_counts[artist] += 1
            genre_counts[primary_genre] += 1

            if len(result) == limit:
                break

        return result

    @staticmethod
    def rerank_candidates(candidates: list, profile: dict, limit: int = 15):
        ranked = []
        seen_ids = set()

        for c in candidates:
            vid_id = c.get('id') or c.get('youtube', {}).get('video_id')
            if not vid_id or vid_id in seen_ids:
                continue
            seen_ids.add(vid_id)

            score = 1.0
            # Taste profile matching
            artist = c.get('artist', '')
            genres = c.get('genres', [])

            if artist in profile.get('artists', {}):
                score *= 1.5
            for g in genres:
                if g in profile.get('genres', {}):
                    score *= 1.3

            # Skip penalty
            if profile.get('skip_probability', 0) > 0.4:
                score *= 0.9

            c['score'] = score
            ranked.append(c)

        return CatalogEngine.diversify(ranked, limit=limit)

    @staticmethod
    def personal_feed(limit: int = 15):
        profile = build_user_taste_profile()
        top_artists = list(profile.get('artists', {}).keys()) or ["Daft Punk", "The Weeknd"]
        top_genres = list(profile.get('genres', {}).keys()) or ["electronic", "synthwave"]

        candidates = []
        for art in top_artists[:2]:
            res = yt_search(f"{art} best tracks", limit=8, music_only=True)
            candidates.extend(res)
        for gen in top_genres[:2]:
            res = yt_search(f"{gen} top hits mix", limit=8, music_only=True)
            candidates.extend(res)

        if not candidates:
            candidates = yt_search("electronic indie chill mix 2026", limit=limit * 2, music_only=True)

        return CatalogEngine.rerank_candidates(candidates, profile, limit=limit)

    @staticmethod
    def home_feed(limit: int = 20):
        return CatalogEngine.personal_feed(limit=limit)

    @staticmethod
    def daily_mix(limit: int = 25):
        profile = build_user_taste_profile()
        top_genres = list(profile.get('genres', {}).keys()) or ["electronic", "pop", "rock"]
        candidates = []
        for gen in top_genres[:3]:
            res = yt_search(f"{gen} daily mix playlist", limit=10, music_only=True)
            candidates.extend(res)
        if not candidates:
            candidates = yt_search("daily mix electronic 2026", limit=limit, music_only=True)
        return CatalogEngine.rerank_candidates(candidates, profile, limit=limit)

    @staticmethod
    def release_radar(limit: int = 15):
        profile = build_user_taste_profile()
        top_artists = list(profile.get('artists', {}).keys()) or ["Daft Punk", "Coldplay"]
        candidates = []
        for art in top_artists[:3]:
            res = yt_search(f"{art} new release 2026 single", limit=5, music_only=True)
            candidates.extend(res)
        if not candidates:
            candidates = yt_search("new music release 2026 hits", limit=limit, music_only=True)
        return CatalogEngine.rerank_candidates(candidates, profile, limit=limit)

    @staticmethod
    def radio_feed(seed_track: str, limit: int = 15):
        profile = build_user_taste_profile()
        candidates = CatalogEngine.semantic_discovery(seed_track, limit=limit * 2)
        return CatalogEngine.rerank_candidates(candidates, profile, limit=limit)

    @staticmethod
    def autoplay_feed(current_track: str, limit: int = 10):
        return CatalogEngine.semantic_discovery(current_track, limit=limit)
