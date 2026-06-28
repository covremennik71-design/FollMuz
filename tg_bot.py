import os
import sys
import json
import time
import logging
import requests
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'tg_token.txt')
CHAT_FILE = os.path.join(BASE_DIR, 'tg_chat.txt')

API_BASE = 'https://api.telegram.org/bot'

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'path_tracks': str(Path.home() / 'Music')}

def read_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return None

def read_chat_id():
    if os.path.exists(CHAT_FILE):
        with open(CHAT_FILE, 'r', encoding='utf-8') as f:
            try: return int(f.read().strip())
            except: pass
    return None

def save_chat_id(cid):
    with open(CHAT_FILE, 'w', encoding='utf-8') as f:
        f.write(str(cid))

def api(method, token, files=None, data=None):
    url = f'{API_BASE}{token}/{method}'
    try:
        r = requests.post(url, files=files, data=data, timeout=30)
        return r.json()
    except Exception as e:
        log.error(f'API error: {e}')
        return {'ok': False}

def get_audio_messages(token, chat_id, limit=100):
    messages = {}
    offset = None
    while len(messages) < limit:
        params = {'timeout': 5, 'allowed_updates': ['message']}
        if offset: params['offset'] = offset
        try:
            r = requests.get(f'{API_BASE}{token}/getUpdates', params=params, timeout=10)
            data = r.json()
            if not data.get('ok'): break
            updates = data.get('result', [])
            if not updates: break
            for upd in updates:
                offset = upd['update_id'] + 1
                msg = upd.get('message')
                if msg and msg.get('chat', {}).get('id') == chat_id:
                    audio = msg.get('audio')
                    if audio:
                        fname = audio.get('file_name') or f"{audio['file_id']}.mp3"
                        messages[fname] = msg['message_id']
        except:
            break
    return messages

def get_mp3_files(tracks_dir):
    files = {}
    for root, dirs, fnames in os.walk(tracks_dir):
        for f in fnames:
            if f.lower().endswith('.mp3'):
                rel = os.path.relpath(os.path.join(root, f), tracks_dir)
                files[rel] = os.path.join(root, f)
    return files

def send_audio_file(token, chat_id, filepath, filename):
    with open(filepath, 'rb') as f:
        result = api('sendAudio', token,
            files={'audio': (filename, f, 'audio/mpeg')},
            data={'chat_id': chat_id, 'title': os.path.splitext(filename)[0]}
        )
        return result.get('ok', False)

def delete_message(token, chat_id, msg_id):
    result = api('deleteMessage', token,
        data={'chat_id': chat_id, 'message_id': msg_id}
    )
    return result.get('ok', False)

def sync_once(token, chat_id, tracks_dir):
    log.info('Starting sync...')
    disk_files = get_mp3_files(tracks_dir)
    log.info(f'Found {len(disk_files)} tracks on disk')
    chat_files = get_audio_messages(token, chat_id)
    log.info(f'Found {len(chat_files)} audio messages in chat')

    for fname, msg_id in chat_files.items():
        if fname not in disk_files:
            if delete_message(token, chat_id, msg_id):
                log.info(f'Deleted from chat: {fname}')
            else:
                log.error(f'Failed to delete: {fname}')

    for fname, fpath in disk_files.items():
        if fname not in chat_files:
            if send_audio_file(token, chat_id, fpath, fname):
                log.info(f'Uploaded to chat: {fname}')
            else:
                log.error(f'Failed to upload: {fname}')

    log.info('Sync complete')

def main():
    token = read_token()
    if not token:
        log.error('NO_TOKEN')
        sys.exit(1)
    chat_id = read_chat_id()
    if not chat_id:
        log.error('NO_CHAT')
        sys.exit(1)
    settings = load_settings()
    tracks_dir = settings.get('path_tracks', str(Path.home() / 'Music'))
    sync_once(token, chat_id, tracks_dir)

if __name__ == '__main__':
    main()
