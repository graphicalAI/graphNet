import logging
from logging import Logger
from datetime import datetime
import sys
from pathlib import Path
import json

from Src.Utils import singleton



@singleton
class Logger_factory:
    '''
    Класс для логирования, синглтон.

    Attributes:
        config: dict - конфигурация для создания логгеров.
    '''
    BASE_PATH = Path(sys._MEIPASS if hasattr(sys, '_MEIPASS') else '.')

    config: dict
    _loggers = {}


    # @classmethod
    @staticmethod
    def open_config(path: Path, exist_ok=True):
        path = Logger_factory.BASE_PATH / path
        config = {}
        if path.exists():
            config = json.load(path.open())
        elif not exist_ok:
            raise FileExistsError(f"Обязательный конфигурационный файл отсутствует: {path}")

        return config


    def __init__(self, config: dict[str, str|int]) -> "Logger_factory":
        '''
        Класс для логирования, синглтон.

        Args:
            config: dict - конфигурация для создания логгеров.
        '''
        if 'filename' in config:
            config['filename'] = config['filename'].format(curdata=datetime.now().strftime(config['datefmt']))
            Path(config['filename']).parent.mkdir(parents=True, exist_ok=True)

        self.config = config
        logging.basicConfig(**self.config)


    def __call__(self, logger_name: str, config: dict = {}) -> logging.Logger:
        '''
        Фабричный метод. При использовании будет вызываться логгер для модуля.

        Args:
            logger_name: str - название логгера для модуля.
            config: dict - конфигурация нового логгера.

        Returns:
            Logger - экземпляр логировщика
        '''
        if logger_name not in Logger_factory._loggers:
            logger = logging.Logger(logger_name)
            Logger_factory._loggers[logger_name] = logger

        logger = Logger_factory._loggers[logger_name]

        if not config: return logger

        config = self.config | config

        logger.propagate = False
        handler = None
        if 'filename' in config and config['filename'] == 'stream':
            handler = logging.StreamHandler(sys.stdout)
        elif 'filename' in config:
            handler = logging.FileHandler(config['filename'].format(curdata=f"{logger_name}_{datetime.now().strftime(config['datefmt'])}"))

        if 'format' in config and handler:
            handler.setFormatter(logging.Formatter(config['format'].format(group=logger_name)))

        if handler: logger.addHandler(handler)

        if 'level' in config:
            logger.setLevel(config['level'])

        return logger
