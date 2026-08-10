import os
import sys
import json
import asyncio
import logging
import hashlib
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = "8911888438:AAGv6b-GCqBcOaODvDFHcN8NapnlO3m0dF0"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')
TRACKING_FILE = os.path.join(os.path.dirname(__file__), 'tracking.json')
PID_FILE = os.path.join(os.path.dirname(__file__), 'bot.pid')
BATCH_LIMIT = 4

def get_tracks_path():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                return settings.get('path_tracks', 'C:/Users/Smixr/Music')
        except Exception:
            pass
    return 'C:/Users/Smixr/Music'

def load_tracking():
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_tracking(data):
    with open(TRACKING_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def normalize_name(filename):
    name = os.path.splitext(filename)[0].lower()
    return re.sub(r'[^a-zа-я0-9]', '', name)

def get_file_hash(filepath):
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    except Exception:
        return None

async def sync_chat(bot, chat_id):
    tracks_path = get_tracks_path()
    tracking = load_tracking()
    
    raw_chat_data = tracking.get(str(chat_id), {})
    if isinstance(raw_chat_data, dict) and "messages" in raw_chat_data:
        chat_messages = raw_chat_data["messages"]
        sent_filenames = set(raw_chat_data.get("sent_filenames", []))
        sent_hashes = set(raw_chat_data.get("sent_hashes", []))
    else:
        # Миграция со старого формата словаря
        chat_messages = {k: v for k, v in raw_chat_data.items() if str(k).isdigit()}
        old_history = raw_chat_data.get("sent_history", []) if isinstance(raw_chat_data, dict) else []
        sent_filenames = {normalize_name(v) for v in list(chat_messages.values()) + list(old_history)}
        sent_hashes = set()

    disk_files_info = []
    if os.path.exists(tracks_path):
        for f in os.listdir(tracks_path):
            if f.endswith('.mp3'):
                filepath = os.path.join(tracks_path, f)
                f_hash = get_file_hash(filepath)
                f_norm = normalize_name(f)
                disk_files_info.append({
                    "filename": f,
                    "norm": f_norm,
                    "hash": f_hash
                })

    sem = asyncio.Semaphore(BATCH_LIMIT)

    async def delete_file(msg_id, filename):
        async with sem:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=int(msg_id))
                logger.info(f"Deleted from chat: {filename}")
                chat_messages.pop(msg_id, None)
            except Exception as e:
                logger.warning(f"Failed to delete {filename}: {e}")

    disk_filenames = {info["filename"] for info in disk_files_info}
    delete_tasks = [
        delete_file(mid, fname)
        for mid, fname in list(chat_messages.items())
        if fname not in disk_filenames
    ]
    if delete_tasks:
        await asyncio.gather(*delete_tasks)
        tracking[str(chat_id)] = {
            "messages": chat_messages,
            "sent_filenames": list(sent_filenames),
            "sent_hashes": list(sent_hashes)
        }
        save_tracking(tracking)

    # Загружаем только новые треки
    to_upload = []
    for info in disk_files_info:
        fname = info["filename"]
        norm = info["norm"]
        fhash = info["hash"]
        
        already_sent = (
            fname in chat_messages.values() or
            norm in sent_filenames or
            (fhash and fhash in sent_hashes)
        )
        if not already_sent:
            to_upload.append(info)

    async def upload_file(info):
        filename = info["filename"]
        norm = info["norm"]
        fhash = info["hash"]
        async with sem:
            filepath = os.path.join(tracks_path, filename)
            try:
                with open(filepath, 'rb') as f:
                    msg = await bot.send_audio(chat_id=chat_id, audio=f, title=filename, performer='')
                chat_messages[str(msg.message_id)] = filename
                sent_filenames.add(norm)
                if fhash:
                    sent_hashes.add(fhash)
                logger.info(f"Uploaded new to chat: {filename}")
            except Exception as e:
                logger.warning(f"Failed to upload {filename}: {e}")

    if to_upload:
        chunk_size = 4
        for i in range(0, len(to_upload), chunk_size):
            chunk = to_upload[i:i + chunk_size]
            await asyncio.gather(*[upload_file(info) for info in chunk])
            tracking[str(chat_id)] = {
                "messages": chat_messages,
                "sent_filenames": list(sent_filenames),
                "sent_hashes": list(sent_hashes)
            }
            save_tracking(tracking)
            await asyncio.sleep(1.5)

    tracking[str(chat_id)] = {
        "messages": chat_messages,
        "sent_filenames": list(sent_filenames),
        "sent_hashes": list(sent_hashes)
    }
    save_tracking(tracking)

async def main():
    from telegram import Bot

    bot = Bot(token=TOKEN)
    logger.info("Bot started, waiting for /start command...")

    offset = 0
    while True:
        try:
            updates = await bot.get_updates(offset=offset, timeout=30, allowed_updates=['message'])
            for update in updates:
                offset = update.update_id + 1
                if update.message and update.message.text == '/start':
                    chat_id = update.message.chat_id
                    await bot.send_message(chat_id, "Синхронизация началась...")
                    await sync_chat(bot, chat_id)
                    await bot.send_message(chat_id, "Синхронизация завершена!")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Polling error: {e}")
            await asyncio.sleep(5)

if __name__ == '__main__':
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
