import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from common.logging import get_logger

logger = get_logger(__name__, "state_manager.log")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_FILE = PROJECT_ROOT / "data" / "state" / "extraction_state.json"


def parse_time(value: Any) -> Optional[datetime]:
    """Convert a supported timestamp into a timezone-aware UTC datetime."""
    if value is None:
        return None


    # datetime object, ensure it's timezone-aware and in UTC
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)


    # Unix timestamp (int or float) or string representation of it
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (ValueError, OverflowError, OSError):
            return None


    # String representation of ISO-8601 or Unix timestamp
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None


        # Convert 2026-10-06T07:00:00Z → 2026-10-06T07:00:00+00:00
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"


        # Try parsing as ISO-8601
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            try:
                return datetime.fromtimestamp(float(value), tz=timezone.utc)
            except (ValueError, OverflowError, OSError):
                return None

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    return None


def default_state() -> dict[str, dict[str, Optional[str]]]:
    """Return the default state structure for the extraction state file."""
    return {
        "openweather": {"last_observation_time": None},
        "geocoding": {"last_observation_time": None},
    }


def load_state() -> dict[str, dict[str, Optional[str]]]:
    """Load extraction state from JSON. If the file is missing, return the default state."""
    if not STATE_FILE.exists():
        logger.info(f"State file {STATE_FILE} does not exist. Returning default state.")
        return default_state()

    try:
        with STATE_FILE.open("r", encoding="utf-8") as file:
            state = json.load(file)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(f"Failed to load state file {STATE_FILE}: {exc}. Returning default state.")
        return default_state()


    # Ensure source keys exist and are dictionaries
    if not isinstance(state, dict):
        return default_state()

    if not isinstance(state.get("openweather"), dict):
        state["openweather"] = {"last_observation_time": None}

    if not isinstance(state.get("geocoding"), dict):
        state["geocoding"] = {"last_observation_time": None}

    return state


def save_state(state: dict[str, dict[str, Optional[str]]]) -> bool:
    """Atomically save the extraction state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = STATE_FILE.with_suffix(".tmp")

    try:
        with temporary_file.open("w", encoding="utf-8") as file:
            json.dump(state, file, indent=2, ensure_ascii=False)
        temporary_file.replace(STATE_FILE)
        logger.info(f"Successfully saved state to {STATE_FILE}")
        return True
    except (OSError, TypeError, ValueError) as exc:
        logger.error(f"Failed to save state file {STATE_FILE}: {exc}")
        if temporary_file.exists():
            try:
                temporary_file.unlink()
            except OSError:
                pass
        return False


def get_location_state(source: str, location: str) -> dict[str, Any]:
    """Return the state for a specific source and location."""
    state = load_state()
    source_state = state.get(source, {})
    if not isinstance(source_state, dict):
        return {}
    location_state = source_state.get(location, {})
    if not isinstance(location_state, dict):
        return {}
    return location_state


def is_new_data(source: str, location: str, observation_time: Any) -> bool:
    """Determine whether this observation is newer than the last processed one."""
    observation_dt = parse_time(observation_time)
    if observation_dt is None:
        logger.warning("Invalid observation timestamp for %s / %s: %r", source, location, observation_time)
        return False

    state = load_state()
    source_state = state.get(source, {})
    if not isinstance(source_state, dict):
        source_state = {}

    location_state = source_state.get(location, {})
    if not isinstance(location_state, dict):
        logger.info("No previous state for %s / %s. Treating as new data.", source, location)
        return True

    last_time_raw = location_state.get("last_observation_time")
    last_dt = parse_time(last_time_raw)
    if last_dt is None:
        logger.info("No previous observation time for %s / %s; treating data as new.", source, location)
        return True

    if observation_dt > last_dt:
        logger.info("New observation for %s / %s: %s > %s", source, location, observation_dt, last_dt)
        return True

    return False


def update_state(source: str, location: str, observation_time: Any) -> bool:
    """Persist the latest timestamp for the provided source/location pair."""
    observation_dt = parse_time(observation_time)
    if observation_dt is None:
        logger.warning("Cannot update state because observation time is invalid: %r", observation_time)
        return False

    state = load_state()
    if source not in state:
        state[source] = {}
    if location not in state[source]:
        state[source][location] = {"last_observation_time": None}

    state[source][location]["last_observation_time"] = observation_dt.isoformat()
    return save_state(state)
