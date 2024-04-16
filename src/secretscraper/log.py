"""Log"""

import logging
import os
from logging.config import dictConfig

from secretscraper.config import settings

os.makedirs(settings.LOGPATH, exist_ok=True)


def verbose_formatter(verbose: int) -> str:
    """formatter factory"""
    if verbose is True:
        return "verbose"
    return "simple"


def update_log_level(debug: bool, level: str) -> str:
    """update log level"""
    if debug is True:
        level_num = logging.DEBUG
    else:
        level_num = logging.getLevelName(level)
    settings.set("LOGLEVEL", logging.getLevelName(level_num))
    return settings.LOGLEVEL


def init_log() -> None:
    """Init log config."""
    log_level = update_log_level(settings.DEBUG, str(settings.LOGLEVEL).upper())

    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "%(asctime)s %(levelname)s %(name)s %(process)d %(thread)d %(message)s",
            },
            "simple": {
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            },
        },
        "handlers": {
            "console": {
                "formatter": verbose_formatter(settings.VERBOSE),
                "level": log_level,
                "class": "logging.StreamHandler",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": verbose_formatter(settings.VERBOSE),
                "filename": os.path.join(settings.LOGPATH, "all.log"),
                "maxBytes": 1024 * 1024 * 1024 * 200,  # 200M
                "backupCount": "5",
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "": {"level": log_level, "handlers": ["console"]},
        },
    }

    dictConfig(log_config)
