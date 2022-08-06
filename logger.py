import logging
import constants
import sys
import traceback
import os

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename=constants.LOG_FILE, encoding="utf-8", mode="a")
handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
logger.addHandler(handler)
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
logger.addHandler(stdout_handler)

# Log uncaught exceptions.
def log_exceptions(type, value, tb):
    loggera = logging.getLogger('discord')
    loggera.error("Uncaught exception:")
    for line in traceback.TracebackException(type, value, tb).format():
        loggera.error(line.rstrip())
    # Call the standard excepthook.
    sys.__excepthook__(type, value, tb)

sys.excepthook = log_exceptions


class logger(logging.Logger):
    def __init__(self):
        super.__init__(self)