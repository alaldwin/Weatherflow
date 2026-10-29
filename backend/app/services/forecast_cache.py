import hashlib
import json
import logging
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_DIR = Path(
    os.getenv("WEATHERFLOW_FORECAST_CACHE_DIR", "/app/data/forecast_cache")
)


def _cache_path(lat: float, lon: float) -> Path:
    key = f"{lat:.2f},{lon:.2f}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.json"


def save_forecast(lat: float, lon: float, forecast: dict) -> dict:
    """Save a successful forecast to persistent local storage."""
    cached = {
        **forecast,
        "cache": {
            "cached": False,
            "retrieved_at": datetime.now(UTC).isoformat(),
        },
    }

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix="forecast-",
        suffix=".tmp",
        dir=CACHE_DIR,
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(cached, file, ensure_ascii=False)

        os.replace(temp_name, _cache_path(lat, lon))
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)

    return cached


def load_forecast(lat: float, lon: float) -> dict | None:
    """Load the last saved forecast, if one exists."""
    path = _cache_path(lat, lon)

    try:
        with path.open("r", encoding="utf-8") as file:
            cached = json.load(file)
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError):
        logger.exception("Unable to read cached forecast")
        return None

    metadata = cached.get("cache", {})

    return {
        **cached,
        "cache": {
            "cached": True,
            "retrieved_at": metadata.get("retrieved_at"),
        },
    }