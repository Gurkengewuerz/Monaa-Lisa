import logging

def setup_logger(logfile='latest_semanticpaper.log'):
    """
    Sets up logging to both file (overwrite on each run) and console.
    Returns a logger instance.
    """
    logger = logging.getLogger("SemanticPaper")
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        logger.handlers.clear()

    file_handler = logging.FileHandler(logfile, mode='w', encoding='utf-8')
    file_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(file_formatter)
    logger.addHandler(console_handler)

    return logger