
import logging
from pathlib import Path

# Resolve the backend directory.
BACKEND_ROOT = Path(__file__).resolve().parents[2]

# Store backend logs in backend/logs/.
LOG_DIR = BACKEND_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Shared logging format.
LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

LOG_LEVEL = logging.INFO


def get_logger(name: str, filename: str) -> logging.Logger:
    """Create a logger that writes to both a file and the console."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(LOG_LEVEL)
    logger.propagate = False

    formatter = logging.Formatter(LOG_FORMAT)

    # File logging.
    file_handler = logging.FileHandler(
        LOG_DIR / filename,
        encoding="utf-8",
    )
    file_handler.setLevel(LOG_LEVEL)
    file_handler.setFormatter(formatter)

    # Console logging.
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def config_logging() -> None:
    """Configure the root logger for the FastAPI application."""
    root_logger = logging.getLogger()

    if root_logger.handlers:
        return

    root_logger.setLevel(LOG_LEVEL)
    formatter = logging.Formatter(LOG_FORMAT)

    file_handler = logging.FileHandler(
        LOG_DIR / "backend.log",
        encoding="utf-8",
    )
    file_handler.setLevel(LOG_LEVEL)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    console_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)