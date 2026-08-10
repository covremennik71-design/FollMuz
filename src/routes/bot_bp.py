# src/routes/bot_bp.py
from flask import Blueprint, jsonify
import subprocess
import sys
import os
from src.app_context import CREATION_FLAGS

bot_bp = Blueprint('bot_bp', __name__)
BOT_PROCESS = None

@bot_bp.route('/bot_status', methods=['GET'])
def bot_status():
    global BOT_PROCESS
    running = False
    if BOT_PROCESS and BOT_PROCESS.poll() is None:
        running = True
    return jsonify({'status': 'success', 'running': running})

@bot_bp.route('/bot_start', methods=['POST'])
def bot_start():
    global BOT_PROCESS
    if BOT_PROCESS and BOT_PROCESS.poll() is None:
        return jsonify({'status': 'success', 'message': 'Бот уже запущен'})
    try:
        bot_script = os.path.join('bot', 'bot.py')
        if os.path.exists(bot_script):
            BOT_PROCESS = subprocess.Popen([sys.executable, bot_script], creationflags=CREATION_FLAGS)
            return jsonify({'status': 'success', 'message': 'Бот запущен'})
        else:
            return jsonify({'status': 'error', 'message': 'bot.py не найден'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bot_bp.route('/bot_stop', methods=['POST'])
def bot_stop():
    global BOT_PROCESS
    if BOT_PROCESS and BOT_PROCESS.poll() is None:
        if sys.platform == 'win32':
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(BOT_PROCESS.pid)],
                          capture_output=True, creationflags=CREATION_FLAGS)
        else:
            BOT_PROCESS.terminate()
        BOT_PROCESS = None
        return jsonify({'status': 'success', 'message': 'Бот остановлен'})
    return jsonify({'status': 'success', 'message': 'Бот не запущен'})

@bot_bp.route('/shutdown', methods=['POST'])
def shutdown():
    global BOT_PROCESS
    if BOT_PROCESS and BOT_PROCESS.poll() is None:
        if sys.platform == 'win32':
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(BOT_PROCESS.pid)],
                          capture_output=True, creationflags=CREATION_FLAGS)
    os._exit(0)
