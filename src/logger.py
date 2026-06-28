import logging
import os
from datetime import datetime
from functools import wraps

class Logger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup_logger()
        return cls._instance

    def _setup_logger(self):
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        log_filename = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y-%m-%d')}.log")

        self.logger = logging.getLogger("FollMuz")
        self.logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def debug(self, msg):
        self.logger.debug(msg)

    def info(self, msg):
        self.logger.info(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def error(self, msg):
        self.logger.error(msg)

    def exception(self, msg):
        self.logger.exception(msg)


def log_function(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = Logger()
        logger.debug(f"Вызов {func.__name__} с args={args}, kwargs={kwargs}")
        start = datetime.now()
        try:
            result = func(*args, **kwargs)
            end = datetime.now()
            logger.debug(f"{func.__name__} выполнена за {end - start}, результат: {result}")
            return result
        except Exception as e:
            logger.exception(f"Ошибка в {func.__name__}: {e}")
            raise
    return wrapper
