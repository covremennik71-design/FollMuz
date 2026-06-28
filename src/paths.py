# src/paths.py
import os
import sys

def get_base_path():
    """Get base path - works in dev and frozen exe."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_PATH = get_base_path()

class Paths:
    ROOT_DIR = BASE_PATH
    SRC_DIR = os.path.join(BASE_PATH, 'src')
    DOWNLOADS_DIR = os.path.join(BASE_PATH, 'downloads')
    CONFIG_DIR = os.path.join(BASE_PATH, 'config')
    LOGS_DIR = os.path.join(BASE_PATH, 'logs')
    CONFIG_FILE = os.path.join(CONFIG_DIR, 'settings.json')
    
    @classmethod
    def ensure_dirs(cls):
        for d in [cls.DOWNLOADS_DIR, cls.CONFIG_DIR, cls.LOGS_DIR]:
            os.makedirs(d, exist_ok=True)
    
    @classmethod
    def get_download_path(cls, subdir=None):
        if subdir:
            path = os.path.join(cls.DOWNLOADS_DIR, subdir)
            os.makedirs(path, exist_ok=True)
            return path
        return cls.DOWNLOADS_DIR
    
    @classmethod
    def get_config_path(cls):
        return cls.CONFIG_FILE
    
    @classmethod
    def get_log_path(cls, filename=None):
        if filename:
            return os.path.join(cls.LOGS_DIR, filename)
        return cls.LOGS_DIR
