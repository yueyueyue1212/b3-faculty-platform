"""Console and rotating-file logging shared by development and portable runs."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import LOG_DIR

LOG_FILE = LOG_DIR / "b3.log"
_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging() -> Path:
    """Configure one console handler and one rotating UTF-8 file handler."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    formatter = logging.Formatter(_FORMAT)
    has_console = any(
        isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, logging.FileHandler)
        for handler in root.handlers
    )
    if not has_console:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        root.addHandler(console)

    log_path = str(LOG_FILE.resolve())
    has_file = any(
        getattr(handler, "_b3_log_path", None) == log_path for handler in root.handlers
    )
    if not has_file:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler._b3_log_path = log_path
        root.addHandler(file_handler)

    return LOG_FILE
