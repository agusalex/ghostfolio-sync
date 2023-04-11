import os

import colorlog

log_level = os.environ.get("LOG_LEVEL", "INFO")


def get_logger(name=__name__):
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s %(levelname)s:%(name)s: %(message)s'
        )
    )
    logger = colorlog.getLogger(name)
    logger.setLevel(log_level)
    logger.addHandler(handler)
    return logger
