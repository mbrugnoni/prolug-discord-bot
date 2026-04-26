import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging(log_dir='logs', log_file='prolug-bot.log',
                  max_bytes=5*1024*1024, backup_count=5):
    """Configure root logger with file rotation and stdout output."""
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # File handler - captures everything, full timestamps
    file_handler = RotatingFileHandler(
        log_path, maxBytes=max_bytes, backupCount=backup_count
    )
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_fmt)

    # Stream handler - INFO and above, shorter format (journalctl adds timestamps)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_fmt = logging.Formatter('[%(levelname)s] %(name)s: %(message)s')
    stream_handler.setFormatter(stream_fmt)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)

    # Quiet down noisy third-party loggers
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
