# src/logger_config.py
import logging
import os
from datetime import datetime
from .paths import Paths

def setup_logger(name='FollMuz', level=logging.DEBUG):
    """
    Настраивает логгер с выводом в файл и консоль.
    
    Args:
        name (str): Имя логгера.
        level (int): Уровень логирования.
    
    Returns:
        logging.Logger: Настроенный логгер.
    """
    # Создаём логгер
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Убираем старые обработчики, если они есть
    if logger.handlers:
        logger.handlers.clear()
    
    # Форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Обработчик для файла
    log_filename = os.path.join(Paths.LOGS_DIR, f'app_{datetime.now().strftime("%Y-%m-%d")}.log')
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

class LoggerMixin:
    """Mixin для добавления логгера в класс."""
    
    @property
    def logger(self):
        if not hasattr(self, '_logger'):
            self._logger = setup_logger(self.__class__.__name__)
        return self._logger