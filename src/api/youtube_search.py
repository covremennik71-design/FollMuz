# src/api/youtube_search.py
import os
import yt_dlp
from ..utils import format_duration

def yt_search(query, limit=12, music_only=True):
    fetch_limit = limit * 3 if music_only else limit
    ydl_opts = {
        'extract_flat': True,
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'playlistend': fetch_limit,
        'default_search': 'ytsearch',
        'extractor_args': {'youtube': {'player_client': ['android']}},
    }
    os.environ['YTDLP_NO_COOKIES'] = '1'
    
    non_music_keywords = [
        'podcast', 'подкаст', 'interview', 'интервью', 'tutorial', 'урок', 
        'how to', 'как сделать', 'gameplay', 'lets play', 'прохождение', 
        'review', 'обзор', 'reaction', 'реакция', 'vlog', 'влог', 
        'stream', 'стрим', 'episode', 'эпизод', 'full movie', 'фильм', 'audiobook', 'аудиокнига'
    ]
    
    mix_keywords = ['mix', 'album', 'playlist', 'concert', 'full', 'микс', 'альбом', 'концерт', 'сборник']
    
    query_lower = query.lower()
    is_mix_query = any(kw in query_lower for kw in mix_keywords)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"ytsearch{fetch_limit}:{query}", download=False)
            tracks = []
            entries = []
            if 'entries' in result:
                entries = result['entries']
            elif isinstance(result, list):
                entries = result
                
            for entry in entries:
                if not entry:
                    continue
                video_id = entry.get('id') or entry.get('url', '').split('=')[-1]
                if not video_id:
                    continue
                title = entry.get('title') or 'Unknown Title'
                channel = entry.get('channel') or entry.get('uploader') or 'Unknown Artist'
                duration = entry.get('duration')
                thumbnail = entry.get('thumbnail') or f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                
                title_lower = title.lower()
                
                if music_only:
                    if duration:
                        if duration < 25:
                            continue
                        if duration > 900 and not is_mix_query:
                            if not any(kw in title_lower for kw in mix_keywords):
                                continue
                    
                    if any(nm in title_lower for nm in non_music_keywords):
                        if not any(mk in title_lower for mk in ['song', 'music', 'audio', 'remix', 'cover', 'песня', 'трек', 'клип']):
                            continue
                
                tracks.append({
                    'id': video_id,
                    'title': title,
                    'artist': channel,
                    'channel_name': channel,
                    'duration': format_duration(duration) if duration else "",
                    'duration_ms': (duration or 0) * 1000,
                    'duration_sec': duration or 0,
                    'thumbnail': thumbnail,
                    'url': f"https://www.youtube.com/watch?v={video_id}"
                })
                if len(tracks) >= limit:
                    break
            return tracks
    except Exception as e:
        print(f"[YOUTUBE SEARCH ERROR] {e}")
        return []
