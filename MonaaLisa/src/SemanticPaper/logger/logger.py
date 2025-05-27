import logging
"""
25-May-2025 - Basti
Abstract:     Sets up logging to both file (overwrite on each run) and console.
Args:
- logfile: Name of the logfile (default value: latest_semanticpaper.log)
Returns: Returns a logger instance.
"""
def setup_logger(logfile='latest_semanticpaper.log'):
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