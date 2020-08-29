import json
import logging


def get_logger(filename):
    log = logging.getLogger(filename)
    log_level = logging.INFO
    log.setLevel(log_level)
    log_handler = logging.StreamHandler()
    log_formatter = logging.Formatter('%(levelname)s: %(asctime)s - %(name)s:%(lineno)d - %(message)s')
    log_handler.setFormatter(log_formatter)
    log.addHandler(log_handler)
    return log


def get_settings():
    with open("settings.json", "r") as f:
        return json.load(f)
