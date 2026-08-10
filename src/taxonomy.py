# src/taxonomy.py
"""
Music Taxonomy, Normalization and Classification System.
Architected for scalability, search, recommendations, and tag normalization.
"""

MUSIC_TAXONOMY = {
    "Electronic": {
        "House": ["Deep House", "Tech House", "Progressive House", "Slap House", "Melodic House", "Microhouse"],
        "Techno": ["Acid Techno", "Melodic Techno", "Hard Techno", "Industrial Techno"],
        "Synthwave": ["Darksynth", "Retrowave", "Chillwave"],
        "Drum & Bass": ["Neurofunk", "Liquid DnB", "Jump Up"],
        "Trance": ["Psytrance", "Progressive Trance", "Vocal Trance"]
    },
    "Rock & Metal": {
        "Rock": ["Alternative Rock", "Indie Rock", "Hard Rock", "Garage Rock", "Post-Rock", "Classic Rock"],
        "Metal": ["Heavy Metal", "Deathcore", "Metalcore", "Melodic Death Metal", "Djent", "Thrash Metal"],
        "Punk": ["Pop Punk", "Post-Punk", "Hardcore Punk"]
    },
    "Hip-Hop & Rap": {
        "Trap": ["Southern Trap", "Melodic Trap", "Drill", "Rage", "Drift Phonk", "Phonk"],
        "Boom Bap": ["Conscious Hip-Hop", "Lo-Fi Hip-Hop", "Jazz Rap"],
        "Hip-Hop": ["Alternative Hip-Hop", "Gangsta Rap"]
    },
    "Pop & Dance": {
        "Synth-Pop": ["Dance-Pop", "Indie Pop", "Electropop"],
        "Disco": ["Nu-Disco", "Italo-Disco"],
        "Pop": ["Mainstream Pop", "Teen Pop"]
    },
    "R&B & Soul": {
        "R&B": ["Contemporary R&B", "Neo-Soul", "Alternative R&B"],
        "Soul": ["Motown", "Modern Soul"]
    },
    "Jazz & Blues": {
        "Jazz": ["Modal Jazz", "Bebop", "Smooth Jazz", "Free Jazz"],
        "Blues": ["Delta Blues", "Electric Blues"]
    },
    "Classical & Ambient": {
        "Classical": ["Chamber Music", "Orchestral", "Baroque", "Opera"],
        "Ambient": ["Neoclassical", "Dark Ambient", "Drone"]
    },
    "Folk & Acoustic": {
        "Folk": ["Contemporary Folk", "Indie Folk", "Singer-Songwriter"],
        "Acoustic": ["Unplugged"]
    },
    "Latin & Reggae": {
        "Reggae": ["Roots Reggae", "Dub", "Dancehall"],
        "Latin": ["Reggaeton", "Salsa", "Bachata", "Latin Pop"]
    }
}

# Alias dictionary mapping variants/synonyms to (Family, Canonical Genre, Subgenre)
GENRE_ALIASES = {
    "deep house": ("Electronic", "House", "Deep House"),
    "deephouse": ("Electronic", "House", "Deep House"),
    "tech house": ("Electronic", "House", "Tech House"),
    "techno": ("Electronic", "Techno", "Melodic Techno"),
    "dnb": ("Electronic", "Drum & Bass", "Liquid DnB"),
    "drum and bass": ("Electronic", "Drum & Bass", "Liquid DnB"),
    "drum & bass": ("Electronic", "Drum & Bass", "Liquid DnB"),
    "synthwave": ("Electronic", "Synthwave", "Retrowave"),
    "phonk": ("Hip-Hop & Rap", "Trap", "Phonk"),
    "drift phonk": ("Hip-Hop & Rap", "Trap", "Drift Phonk"),
    "trap": ("Hip-Hop & Rap", "Trap", "Southern Trap"),
    "drill": ("Hip-Hop & Rap", "Trap", "Drill"),
    "hip hop": ("Hip-Hop & Rap", "Hip-Hop", "Alternative Hip-Hop"),
    "hiphop": ("Hip-Hop & Rap", "Hip-Hop", "Alternative Hip-Hop"),
    "rap": ("Hip-Hop & Rap", "Hip-Hop", "Alternative Hip-Hop"),
    "lofi": ("Hip-Hop & Rap", "Boom Bap", "Lo-Fi Hip-Hop"),
    "lo-fi": ("Hip-Hop & Rap", "Boom Bap", "Lo-Fi Hip-Hop"),
    "rock": ("Rock & Metal", "Rock", "Alternative Rock"),
    "indie rock": ("Rock & Metal", "Rock", "Indie Rock"),
    "metal": ("Rock & Metal", "Metal", "Heavy Metal"),
    "metalcore": ("Rock & Metal", "Metal", "Metalcore"),
    "pop": ("Pop & Dance", "Pop", "Mainstream Pop"),
    "synthpop": ("Pop & Dance", "Synth-Pop", "Dance-Pop"),
    "synth-pop": ("Pop & Dance", "Synth-Pop", "Dance-Pop"),
    "disco": ("Pop & Dance", "Disco", "Nu-Disco"),
    "rnb": ("R&B & Soul", "R&B", "Contemporary R&B"),
    "r&b": ("R&B & Soul", "R&B", "Contemporary R&B"),
    "soul": ("R&B & Soul", "Soul", "Modern Soul"),
    "jazz": ("Jazz & Blues", "Jazz", "Modal Jazz"),
    "blues": ("Jazz & Blues", "Blues", "Electric Blues"),
    "classical": ("Classical & Ambient", "Classical", "Orchestral"),
    "ambient": ("Classical & Ambient", "Ambient", "Neoclassical"),
    "folk": ("Folk & Acoustic", "Folk", "Indie Folk"),
    "reggae": ("Latin & Reggae", "Reggae", "Roots Reggae"),
    "reggaeton": ("Latin & Reggae", "Latin", "Reggaeton")
}

def normalize_genre(raw_genre: str) -> dict:
    """
    Normalizes a raw genre string into Family, Canonical Genre, Subgenre, and confidence score.
    """
    if not raw_genre:
        return {
            "family": "Unknown",
            "primary": "Unknown",
            "subgenre": "Unknown",
            "confidence": 0.0
        }
    
    cleaned = raw_genre.lower().strip()
    
    # 1. Direct alias lookup
    if cleaned in GENRE_ALIASES:
        fam, prim, sub = GENRE_ALIASES[cleaned]
        return {
            "family": fam,
            "primary": prim,
            "subgenre": sub,
            "confidence": 0.95
        }
    
    # 2. Fuzzy / Substring matching through taxonomy
    for family, genres in MUSIC_TAXONOMY.items():
        for primary, subgenres in genres.items():
            if cleaned in primary.lower() or primary.lower() in cleaned:
                return {
                    "family": family,
                    "primary": primary,
                    "subgenre": subgenres[0] if subgenres else "General",
                    "confidence": 0.80
                }
            for sub in subgenres:
                if cleaned in sub.lower() or sub.lower() in cleaned:
                    return {
                        "family": family,
                        "primary": primary,
                        "subgenre": sub,
                        "confidence": 0.90
                    }
    
    # 3. Fallback
    return {
        "family": "Other",
        "primary": raw_genre.title(),
        "subgenre": "General",
        "confidence": 0.40
    }

def infer_genre_from_filename(filename: str) -> dict:
    """
    Infers genre from filename using keyword analysis.
    If no specific keyword matches, returns None.
    """
    if not filename:
        return None
    
    fn_lower = filename.lower()
    
    if "phonk" in fn_lower:
        return normalize_genre("Phonk")
    if "house" in fn_lower:
        return normalize_genre("House")
    if "techno" in fn_lower:
        return normalize_genre("Techno")
    if "lofi" in fn_lower or "lo-fi" in fn_lower:
        return normalize_genre("Lo-Fi")
    if "rock" in fn_lower or "metal" in fn_lower:
        return normalize_genre("Rock")
    if "rap" in fn_lower or "trap" in fn_lower or "drill" in fn_lower or "hip hop" in fn_lower:
        return normalize_genre("Hip-Hop")
    if "synthwave" in fn_lower or "retrowave" in fn_lower:
        return normalize_genre("Synthwave")
    if "ambient" in fn_lower or "chill" in fn_lower:
        return normalize_genre("Ambient")
    if "jazz" in fn_lower:
        return normalize_genre("Jazz")
    if "classical" in fn_lower or "piano" in fn_lower:
        return normalize_genre("Classical")
    if "reggae" in fn_lower:
        return normalize_genre("Reggae")
    if "remix" in fn_lower:
        return normalize_genre("Dance-Pop")
        
    return None
