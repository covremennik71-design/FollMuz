import os
import sys
import json
import asyncio
import logging

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
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            return settings.get('path_tracks', 'C:/Users/Smixr/Music')
    return 'C:/Users/Smixr/Music'

def load_tracking():
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_tracking(data):
    with open(TRACKING_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def sync_chat(bot, chat_id):
    tracks_path = get_tracks_path()
    tracking = load_tracking()
    chat_data = tracking.get(str(chat_id), {})

    disk_files = set()
    if os.path.exists(tracks_path):
        for f in os.listdir(tracks_path):
            if f.endswith('.mp3'):
                disk_files.add(f)

    sem = asyncio.Semaphore(BATCH_LIMIT)

    # Удаление: файлы в трекинге, но не на диске
    async def delete_file(msg_id, filename):
        async with sem:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=int(msg_id))
                logger.info(f"Deleted from chat: {filename}")
                chat_data.pop(msg_id, None)
                tracking[str(chat_id)] = chat_data
                save_tracking(tracking)
            except Exception as e:
                logger.warning(f"Failed to delete {filename}: {e}")

    delete_tasks = [
        delete_file(mid, fname)
        for mid, fname in list(chat_data.items())
        if fname not in disk_files
    ]
    if delete_tasks:
        await asyncio.gather(*delete_tasks)

    # Загрузка: файлы на диске, но не в трекинге
    tracked_filenames = set(chat_data.values())
    to_upload = sorted(f for f in disk_files if f not in tracked_filenames)

    async def upload_file(filename):
        async with sem:
            filepath = os.path.join(tracks_path, filename)
            try:
                with open(filepath, 'rb') as f:
                    msg = await bot.send_audio(chat_id=chat_id, audio=f, title=filename, performer='')
                chat_data[str(msg.message_id)] = filename
                tracking[str(chat_id)] = chat_data
                save_tracking(tracking)
                logger.info(f"Uploaded to chat: {filename}")
            except Exception as e:
                logger.warning(f"Failed to upload {filename}: {e}")

    if to_upload:
        await asyncio.gather(*[upload_file(f) for f in to_upload])

    tracking[str(chat_id)] = chat_data
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
