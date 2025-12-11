import logging
import logging.handlers
import os
from pathlib import Path


class Logger:
    _instances = {}
    
    def __init__(
            self,
            name: str,
            log_path: str = "logs"
    ):
        self.name = name
        self.logger = logging.getLogger(name)
        
        if not self.logger.handlers:
            self.logger.setLevel(logging.DEBUG)

            self.config = {
                'log_format': '%(asctime)s [%(levelname)s] [%(name)s] - %(message)s',
                'date_format': '%d-%m-%Y %H:%M:%S',
                'max_bytes': 10485760,  # 10MB
                'backup_count': 5,
                'file_level': 'INFO',
                'console_level': 'INFO'
            }

            # format everything like in the config
            formatter = logging.Formatter(
                fmt=self.config['log_format'],
                datefmt=self.config['date_format']
            )

            # add console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.config['console_level'])
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

            # Add file handler to keep track oc
            os.makedirs(log_path, exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                filename=Path(log_path) / f"{name}.log",
                maxBytes=self.config['max_bytes'],
                backupCount=self.config['backup_count']
            )
            file_handler.setLevel(self.config['file_level'])
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
"""
14 Dec 2025 - Basti
The logger used to have a weird function signature that made it odd to use normally.
"""
    def info(self, message: str, *args, **kwargs):
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, exc_info=True, **kwargs):
        self.logger.error(message, *args, exc_info=exc_info, **kwargs)

    def debug(self, message: str, *args, **kwargs):
        self.logger.debug(message, *args, **kwargs)

    def set_level(self, level: str):
        self.logger.setLevel(getattr(logging, level.upper()))