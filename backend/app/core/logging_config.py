import json
import logging
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = BACKEND_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_LEVEL = logging.INFO

MAX_LOG_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5

STRUCTURED_FIELDS = (
    "request_id",
    "method",
    "path",
    "status_code",
    "duration_ms",
)


class StructuredFormatter(logging.Formatter):
    """Format logs as readable text in the terminal."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=UTC,
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for field in STRUCTURED_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                log_entry[field] = value

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class ConsoleFormatter(logging.Formatter):
    """Format logs as readable text in the terminal."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(
            record.created,
            tz=UTC,
        ).isoformat(timespec="seconds")

        message = (
            f"{timestamp} | "
            f"{record.levelname:<8} | "
            f"{record.name} | "
            f"{record.getMessage()}"
        )

        for field in STRUCTURED_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                message += f" | {field}={value}"

        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)

        return message


def _create_handler(
    filename: str | None = None,
) -> logging.Handler:
    """Create a readable console or structured file handler."""

    if filename is None:
        handler = logging.StreamHandler()
        handler.setFormatter(ConsoleFormatter())
    else:
        handler = RotatingFileHandler(
            LOG_DIR / filename,
            maxBytes=MAX_LOG_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setFormatter(StructuredFormatter())

    handler.setLevel(LOG_LEVEL)
    return handler


def get_logger(name: str, filename: str) -> logging.Logger:
    """Create a logger that writes structured logs to file and console."""

    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(LOG_LEVEL)
    logger.propagate = False

    logger.addHandler(_create_handler(filename))
    logger.addHandler(_create_handler())

    return logger


def config_logging() -> None:
    """Configure application logging at INFO level."""

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if not root_logger.handlers:
        root_logger.addHandler(_create_handler("backend.log"))
        root_logger.addHandler(_create_handler())

    # Configure Uvicorn's loggers to use INFO level.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
