# src/catalog/youtube_matcher.py
import re
from difflib import SequenceMatcher

UNWANTED_MARKERS = [
    "live", "concert", "cover", "karaoke", "instrumental", "nightcore",
    "slowed", "sped up", "8d", "remix", "fan made", "reaction", "mix", "playlist", "compilation"
]

OFFICIAL_CHANNELS = ["vevo", "official", "topic", "records", "music"]

def normalize_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'[\(\)\[\]\{\}\_\-\/\,\.\!\?]', ' ', text.lower()).strip()

def artist_in_title(artist: str, title: str) -> bool:
    if not artist or not title:
        return False
    a_norm = normalize_text(artist)
    t_norm = normalize_text(title)
    return any(word in t_norm for word in a_norm.split() if len(word) > 2)

def title_contains_track(track: str, title: str) -> bool:
    if not track or not title:
        return False
    tr_norm = normalize_text(track)
    t_norm = normalize_text(title)
    return tr_norm in t_norm or SequenceMatcher(None, tr_norm, t_norm).ratio() > 0.7

def duration_matches(rec_ms: int, vid_ms: int) -> bool:
    if not rec_ms or not vid_ms:
        return True  # fallback if duration unknown
    return abs(rec_ms - vid_ms) < 7000  # within 7 seconds

def is_official_channel(channel_name: str) -> bool:
    if not channel_name:
        return False
    c = channel_name.lower()
    return any(term in c for term in OFFICIAL_CHANNELS)

def is_topic_channel(channel_name: str) -> bool:
    if not channel_name:
        return False
    return "topic" in channel_name.lower()

def has_unwanted_marker(title: str, version_type: str) -> bool:
    t = title.lower()
    for marker in UNWANTED_MARKERS:
        if marker in t:
            # If the requested version matches the marker, it's NOT unwanted
            if version_type and version_type in marker:
                continue
            return True
    return False

def is_compilation(title: str) -> bool:
    t = title.lower()
    return "compilation" in t or "full album" in t or "megamix" in t

def is_karaoke(title: str) -> bool:
    t = title.lower()
    return "karaoke" in t or "instrumental version" in t

def score_youtube_candidate(recording: dict, video: dict) -> float:
    score = 0.0
    penalties = 0.0

    v_title = video.get('title', '')
    artist = recording.get('artist', '')
    track = recording.get('title', '')
    version_type = recording.get('version_type', 'studio')
    rec_length = recording.get('length_ms')
    vid_length = video.get('duration_ms') or (video.get('duration_sec', 0) * 1000)
    channel = video.get('channel_name') or video.get('uploader', '')

    if artist_in_title(artist, v_title):
        score += 0.35

    if title_contains_track(track, v_title):
        score += 0.35

    if duration_matches(rec_length, vid_length):
        score += 0.15

    if is_official_channel(channel):
        score += 0.10

    if is_topic_channel(channel):
        score += 0.08

    if has_unwanted_marker(v_title, version_type):
        penalties += 0.30

    if is_compilation(v_title):
        penalties += 0.25

    if is_karaoke(v_title):
        penalties += 0.40

    return max(0.0, min(1.0, score - penalties))

def generate_youtube_queries(artist: str, title: str, version_type: str = "studio") -> list:
    queries = [
        f'"{artist}" "{title}" official audio',
        f'"{artist}" "{title}" official video',
        f'"{artist}" "{title}" Topic',
        f'"{artist}" "{title}" audio',
        f'"{artist}" "{title}"',
    ]
    if version_type == "live":
        queries.insert(0, f'"{artist}" "{title}" live')
    elif version_type == "remix":
        queries.insert(0, f'"{artist}" "{title}" remix')
    elif version_type == "acoustic":
        queries.insert(0, f'"{artist}" "{title}" acoustic')
    elif version_type == "instrumental":
        queries.insert(0, f'"{artist}" "{title}" instrumental')
    return queries
