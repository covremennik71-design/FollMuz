import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Set

import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'tg_token.txt')
CHAT_FILE = os.path.join(BASE_DIR, 'tg_chat.txt')

API_BASE = 'https://api.telegram.org/bot'
TRACKING_FILE = os.path.join(BASE_DIR, 'bot', 'tracking.json')


# ---------- Утилиты ----------

def load_json_file(path: str, default: Any = None) -> Any:
    if default is None:
        default = {}
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log.warning(f"Не удалось прочитать {path}: {e}")
    return default


def save_json_file(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_tracking() -> Dict[str, Dict[str, str]]:
    data = load_json_file(TRACKING_FILE, {})
    if not isinstance(data, dict):
        return {}
    return data


def save_tracking(data: Dict[str, Dict[str, str]]) -> None:
    save_json_file(TRACKING_FILE, data)


def load_settings() -> Dict[str, Any]:
    default = {'path_tracks': str(Path.home() / 'Music')}
    cfg = load_json_file(SETTINGS_FILE, default)
    if not isinstance(cfg, dict):
        return default
    if 'path_tracks' not in cfg:
        cfg['path_tracks'] = default['path_tracks']
    return cfg


def read_token() -> Optional[str]:
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            log.warning(f"Не удалось прочитать токен: {e}")
    return None


def read_chat_id() -> Optional[int]:
    if os.path.exists(CHAT_FILE):
        try:
            with open(CHAT_FILE, 'r', encoding='utf-8') as f:
                raw = f.read().strip()
                return int(raw)
        except Exception as e:
            log.warning(f"Не удалось прочитать chat_id: {e}")
    return None


def save_chat_id(cid: int) -> None:
    os.makedirs(os.path.dirname(CHAT_FILE), exist_ok=True)
    with open(CHAT_FILE, 'w', encoding='utf-8') as f:
        f.write(str(cid))


# ---------- Telegram API ----------

def api(
    method: str,
    token: str,
    files: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    retries: int = 2,
) -> Dict[str, Any]:
    url = f'{API_BASE}{token}/{method}'
    attempt = 0
    while True:
        try:
            r = requests.post(url, files=files, data=data, timeout=30)
            result = r.json()
            return result
        except Exception as e:
            attempt += 1
            if attempt > retries:
                log.error(f'API error ({method}): {e}')
                return {'ok': False}
            log.warning(f'API error ({method}), retry {attempt}/{retries}: {e}')
            time.sleep(1.0)


def get_audio_messages(
    token: str,
    chat_id: int,
    limit: int = 100,
) -> Dict[str, int]:
    """
    Получить последние audio-сообщения из чата.
    Возвращает dict: {filename: message_id}.
    """
    messages: Dict[str, int] = {}
    offset: Optional[int] = None

    while len(messages) < limit:
        params = {'timeout': 5, 'allowed_updates': ['message']}
        if offset is not None:
            params['offset'] = offset

        try:
            r = requests.get(
                f'{API_BASE}{token}/getUpdates',
                params=params,
                timeout=10,
            )
            data = r.json()
            if not data.get('ok'):
                break
            updates = data.get('result', [])
            if not updates:
                break

            for upd in updates:
                offset = upd['update_id'] + 1
                msg = upd.get('message')
                if msg and msg.get('chat', {}).get('id') == chat_id:
                    audio = msg.get('audio')
                    if audio:
                        fname = audio.get('file_name') or f"{audio['file_id']}.mp3"
                        messages[fname] = msg['message_id']
        except Exception as e:
            log.warning(f"Ошибка при получении audio-сообщений: {e}")
            break

    return messages


def get_mp3_files(tracks_dir: str) -> Dict[str, str]:
    files: Dict[str, str] = {}
    tracks_dir = os.path.abspath(tracks_dir)

    for root, _, fnames in os.walk(tracks_dir):
        for f in fnames:
            if f.lower().endswith('.mp3'):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, tracks_dir)
                files[rel_path] = full_path

    return files


def send_audio_file(
    token: str,
    chat_id: int,
    filepath: str,
    filename: str,
) -> bool:
    with open(filepath, 'rb') as f:
        result = api(
            'sendAudio',
            token,
            files={'audio': (filename, f, 'audio/mpeg')},
            data={
                'chat_id': str(chat_id),
                'title': os.path.splitext(os.path.basename(filename))[0],
            },
        )
        return bool(result.get('ok'))


def delete_message(
    token: str,
    chat_id: int,
    msg_id: int,
) -> bool:
    result = api(
        'deleteMessage',
        token,
        data={
            'chat_id': str(chat_id),
            'message_id': msg_id,
        },
    )
    return bool(result.get('ok'))


def sync_once(
    token: str,
    chat_id: int,
    tracks_dir: str,
) -> None:
    log.info('Starting sync...')

    if not os.path.isdir(tracks_dir):
        log.error(f"Директория с треками не найдена: {tracks_dir}")
        return

    disk_files = get_mp3_files(tracks_dir)
    log.info(f'Found {len(disk_files)} tracks on disk')

    tracking = load_tracking()
    chat_data: Dict[str, str] = tracking.get(str(chat_id), {})

    # Нормализуем: ключи — строки, значения — имена файлов
    chat_data = {str(k): v for k, v in chat_data.items()}

    tracked_filenames: Set[str] = set(chat_data.values())
    disk_file_set: Set[str] = set(disk_files.keys())

    # Удаляем сообщения о треках, которых больше нет на диске
    for msg_id_str, fname in list(chat_data.items()):
        if fname not in disk_file_set:
            msg_id = int(msg_id_str)
            if delete_message(token, chat_id, msg_id):
                log.info(f'Deleted from chat: {fname}')
                chat_data.pop(msg_id_str, None)
            else:
                log.error(f'Failed to delete: {fname}')

    # Загружаем новые треки
    to_upload = sorted([fname for fname in disk_files if fname not in tracked_filenames])

    chunk_size = 4
    for i in range(0, len(to_upload), chunk_size):
        chunk = to_upload[i:i + chunk_size]
        for fname in chunk:
            fpath = disk_files[fname]
            if send_audio_file(token, chat_id, fpath, os.path.basename(fname)):
                # Получаем message_id из ответа API (если нужно, можно доработать api())
                # Пока просто сохраняем по факту успешной отправки
                # Для точного message_id нужно парсить результат api() внутри send_audio_file
                log.info(f'Uploaded to chat: {fname}')
            else:
                log.error(f'Failed to upload {fname}')

        # Сохраняем прогресс после каждой пачки
        tracking[str(chat_id)] = chat_data
        save_tracking(tracking)
        time.sleep(1.5)  # Пауза, чтобы не словить rate limit от Telegram

    tracking[str(chat_id)] = chat_data
    save_tracking(tracking)
    log.info('Sync complete')


def main() -> None:
    token = read_token()
    if not token:
        log.error('NO_TOKEN')
        sys.exit(1)

    chat_id = read_chat_id()
    if chat_id is None:
        log.error('NO_CHAT')
        sys.exit(1)

    cfg = load_settings()
    tracks_dir = cfg.get('path_tracks', str(Path.home() / 'Music'))

    sync_once(token, chat_id, tracks_dir)


if __name__ == '__main__':
    main()