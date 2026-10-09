import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common.logging import get_logger


logger = get_logger(__name__, "save_json.log")

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def _safe_name(s: str) -> str:
    """Convert a city/source name into a safe file/directory name."""
    s = (s or "").strip().lower()
    s = s.replace(" ", "_")
    return re.sub(r"[^a-z0-9_-]", "_", s)


def _load_existing_records(output_file: Path) -> list[dict[str, Any]]:
    """Load raw JSON records if the file already exists."""
    if not output_file.exists():
        return []

    try:
        with output_file.open("r", encoding="utf-8") as file:
            content = json.load(file)
    except (json.JSONDecodeError, OSError):
        return []

    if isinstance(content, list):
        return [item for item in content if isinstance(item, dict)]
    if isinstance(content, dict):
        return [content]
    return []


def _prepare_weather_record(data: dict[str, Any], city: str, source: str) -> dict[str, Any]:
    """Normalize raw weather payloads before they are written to disk."""
    record = dict(data)
    record.setdefault("city", city)
    record.setdefault("source", source)
    record.setdefault("observation_time", _get_observation_time(data))
    return record


def _get_observation_time(data: dict) -> str | None:
    """
    Extract the observation timestamp from the API data.

    If the payload is intentionally minimal or missing time metadata, fall back to
    the current UTC timestamp so the raw JSON writer still behaves predictably.
    """

    if data.get("observation_time"):
        return str(data["observation_time"])

    if data.get("dt"):
        return datetime.fromtimestamp(
            data["dt"],
            tz=timezone.utc
        ).isoformat()

    current = data.get("current", {})
    if current.get("last_updated"):
        return str(current["last_updated"])

    return datetime.now(timezone.utc).isoformat()


def save_json(
    data: dict,
    city: str,
    source: str
) -> Path:

    if not isinstance(data, dict):
        raise TypeError("data must be a dictionary")

    if not city or not city.strip():
        raise ValueError("city cannot be empty")

    if not source or not source.strip():
        raise ValueError("source cannot be empty")

    safe_city = _safe_name(city)
    safe_source = _safe_name(source)
    output_dir = RAW_DIR / safe_source
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{safe_city}.json"

    record = _prepare_weather_record(data=data, city=city, source=source)
    observation_time = record["observation_time"]
    existing_data = _load_existing_records(output_file)
    existing_times = {_get_observation_time(record) for record in existing_data}

    if observation_time in existing_times:
        logger.info(f"Duplicate skipped: {source} - {city} - {observation_time}")
        return output_file

    existing_data.append(record)

    try:
        with output_file.open("w", encoding="utf-8") as file:
            json.dump(existing_data, file, ensure_ascii=False, indent=4)
    except OSError as exc:
        logger.error(f"Failed to write JSON file {output_file}: {exc}")
        raise

    if len(existing_data) == 1:
        logger.info(f"Initial load: {source} - {city} - {observation_time}")
    else:
        logger.info(f"Appended record: {source} - {city} - {observation_time}")

    return output_file
 