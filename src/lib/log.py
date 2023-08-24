"""Logging facilities."""

# Core modules.
import logging

# External modules.
import colorlog

# Logger used accross all modules.
LOGGER = None

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

def init(file, level):
    """Initialize the logging system.

    Initialize the stream type (stderr/file) and the logging format depending
    on the later in the global LOGGER variable, alert program start.

    :param file: File name used to log the messages.
    :param level: Logging level [logging.INFO, logging.DEBUG]
    :raises: Exception raised by logging.FileHandler().

    """
    global LOGGER
    try:
        if file:
            handler = logging.FileHandler(file)
            formatter = logging.Formatter("[%(asctime)s] [%(threadName)s] - %(levelname)-5s - %(module)-10s - %(message)s")
            LOGGER = logging.getLogger(__name__)
        else:
            handler = colorlog.StreamHandler()
            format = "%(log_color)s{}%(levelname)-5s - %(module)-10s - %(message)s".format("[%(asctime)s] [%(threadName)s] " if level == "DEBUG" else "")
            formatter = colorlog.ColoredFormatter(format)
            LOGGER = colorlog.getLogger(__name__)
        handler.setFormatter(formatter)
    except Exception as e:
        print("ERROR: Can't initialize the logging file/stream.")
        raise e
    else:
        LOGGER.propagate = False # We want a custom handler and don't want its
                                 # messages also going to the root handler.
        LOGGER.setLevel(level)
        LOGGER.addHandler(handler)
        LOGGER.debug("Start logging")

def close():
    """End the logging system.

    Alert the program end.

    """
    LOGGER.debug("End logging")
