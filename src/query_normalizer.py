# src/query_normalizer.py
import re

VERSION_KEYWORDS = {
    "live": ["live", "concert", "tour"],
    "remix": ["remix", "mix", "club mix", "extended mix"],
    "acoustic": ["acoustic", "unplugged", "piano version"],
    "instrumental": ["instrumental", "karaoke version"],
    "cover": ["cover", "tribute"],
    "karaoke": ["karaoke", "instrumental karaoke"],
    "sped_up": ["sped up", "nightcore", "fast"],
    "slowed": ["slowed", "reverb", "slowed + reverb", "slow"],
    "edit": ["edit", "radio edit", "single edit"],
    "demo": ["demo", "rough mix", "prototype"],
    "compilation": ["compilation", "full album", "megamix"]
}

def normalize_text(text: str) -> str:
    if not text:
        return ""
    t = text.lower()
    t = t.replace('&', ' and ')
    t = re.sub(r'[\(\)\[\]\{\}\_\-\/\,\.\!\?]', ' ', t)
    # Remove noise words from main comparison but keep context if needed
    noise_words = ['official', 'music', 'video', 'lyrics', 'audio', 'hq', 'hd', 'visualizer']
    words = t.split()
    filtered = [w for w in words if w not in noise_words]
    return " ".join(filtered).strip()

def detect_version_keywords(query: str) -> str:
    q_lower = query.lower()
    for v_type, keywords in VERSION_KEYWORDS.items():
        for kw in keywords:
            if kw in q_lower:
                return v_type
    if "official video" in q_lower or "music video" in q_lower:
        return "official_video"
    if "official audio" in q_lower:
        return "official_audio"
    return "studio"

def normalize_query(query: str) -> dict:
    cleaned_raw = query.strip()
    version_hint = detect_version_keywords(cleaned_raw)
    
    # Try splitting artist and title if ' - ' or ' by ' exists
    artist_hint = None
    title_hint = cleaned_raw
    album_hint = None
    year_hint = None
    
    if ' - ' in cleaned_raw:
        parts = cleaned_raw.split(' - ', 1)
        artist_hint = parts[0].strip()
        title_hint = parts[1].strip()
    elif ' by ' in cleaned_raw.lower():
        parts = re.split(r'\s+by\s+', cleaned_raw, flags=re.IGNORECASE)
        title_hint = parts[0].strip()
        artist_hint = parts[1].strip()

    # Extract year if 4 digits 19xx or 20xx in query
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', cleaned_raw)
    if year_match:
        year_hint = int(year_match.group(1))

    return {
        "raw": cleaned_raw,
        "normalized": normalize_text(cleaned_raw),
        "artist_hint": artist_hint,
        "title_hint": normalize_text(title_hint) if title_hint else normalize_text(cleaned_raw),
        "album_hint": album_hint,
        "year_hint": year_hint,
        "version_hint": version_hint,
    }
