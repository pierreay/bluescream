"""Logging facilities."""

# Core modules.
import logging
import os

# External modules.
import colorlog

# Logger used accross all modules.
LOGGER = None
OS_LOGLEVEL = os.getenv("DE_OS_LOGLEVEL")
LOGGER_DEFAULT_LEVEL = "DEBUG" if OS_LOGLEVEL is None else OS_LOGLEVEL

def log_n_exit(e, str, code, traceback=False):
    """Log a critical error and exit.

    :param e: Exception object.
    :param str: Log message.
    :param code: Exit code.

    """
    assert LOGGER, "No initialized logger"
    if e:
        LOGGER.critical(e, exc_info=traceback)
    LOGGER.critical(str)
    exit(code)

def init(level):
    """Initialize the logging system.

    Initialize the stream type (stderr) and the logging format depending on the
    later in the global LOGGER variable, alert program start.

    """
    global LOGGER
    if LOGGER is None:
        handler = colorlog.StreamHandler()
        format = "%(log_color)s{}%(levelname)-5s - %(message)s".format("[%(asctime)s] [%(threadName)s] [%(module)s] " if level == "DEBUG" else "")
        formatter = colorlog.ColoredFormatter(format)
        LOGGER = colorlog.getLogger(__name__)
        handler.setFormatter(formatter)
        LOGGER.propagate = False # We want a custom handler and don't want its
                                 # messages also going to the root handler.
        LOGGER.setLevel(level)
        LOGGER.addHandler(handler)

init(LOGGER_DEFAULT_LEVEL)
