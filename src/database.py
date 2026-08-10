# src/database.py
import sqlite3
import json
import os
import uuid
import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'follmuz_catalog.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS artists (
        id TEXT PRIMARY KEY,
        musicbrainz_artist_id TEXT UNIQUE,
        name TEXT NOT NULL,
        sort_name TEXT,
        country TEXT,
        artist_type TEXT,
        disambiguation TEXT,
        aliases TEXT DEFAULT '[]',
        genres TEXT DEFAULT '[]',
        metadata_confidence REAL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS releases (
        id TEXT PRIMARY KEY,
        musicbrainz_release_id TEXT UNIQUE,
        title TEXT NOT NULL,
        artist_id TEXT,
        release_group_id TEXT,
        release_date TEXT,
        country TEXT,
        release_type TEXT,
        cover_art_url TEXT,
        metadata_confidence REAL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (artist_id) REFERENCES artists(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS recordings (
        id TEXT PRIMARY KEY,
        musicbrainz_recording_id TEXT UNIQUE,
        title TEXT NOT NULL,
        normalized_title TEXT NOT NULL,
        artist_id TEXT,
        release_id TEXT,
        isrc TEXT,
        length_ms INTEGER,
        version TEXT,
        version_type TEXT DEFAULT 'studio',
        genres TEXT DEFAULT '[]',
        audio_features TEXT DEFAULT '{}',
        metadata_confidence REAL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (artist_id) REFERENCES artists(id),
        FOREIGN KEY (release_id) REFERENCES releases(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS track_sources (
        id TEXT PRIMARY KEY,
        recording_id TEXT,
        source TEXT NOT NULL,
        source_track_id TEXT NOT NULL,
        source_url TEXT,
        source_type TEXT,
        title_from_source TEXT,
        channel_name TEXT,
        duration_ms INTEGER,
        published_at TEXT,
        match_score REAL DEFAULT 0,
        match_method TEXT,
        is_verified INTEGER DEFAULT 0,
        is_available INTEGER DEFAULT 1,
        last_checked_at TEXT,
        UNIQUE(recording_id, source, source_track_id),
        FOREIGN KEY (recording_id) REFERENCES recordings(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS api_cache (
        cache_key TEXT PRIMARY KEY,
        data TEXT NOT NULL,
        expires_at REAL NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        recording_id TEXT,
        track_id TEXT,
        metadata TEXT,
        timestamp REAL NOT NULL
    )
    ''')

    conn.commit()
    conn.close()

init_db()
