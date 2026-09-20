import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from common.logging import get_logger

logger = get_logger(__name__, "incremetal_load.log")


STATE_FILE = Path("data/state/extraction_state.json")


def parse_time(value: Any) -> Optional[datetime]:
    """Parse common timestamp formats into a timezone-aware UTC datetime.

    Accepts datetime, ISO-8601 strings (with or without Z), and unix epoch (int/float).
    Returns None if value is falsy.
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            return None

    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # Accept trailing Z for UTC
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(s).astimezone(timezone.utc)
        except Exception:
            # fallback: try parsing as float epoch string
            try:
                return datetime.fromtimestamp(float(s), tz=timezone.utc)
            except Exception:
                return None

    return None


def load_state() -> Dict[str, Dict[str, Optional[str]]]:
    if not STATE_FILE.exists():
        return {
            "openweather": {"last_observation_time": None},
            "weatherapi": {"last_observation_time": None},
        }

    with STATE_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_state(state: Dict[str, Dict[str, Optional[str]]]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with STATE_FILE.open("w", encoding="utf-8") as file:
        json.dump(state, file, indent=2)


def is_new_data(source: str, observation_time: Any) -> bool:
    """Return True if `observation_time` is newer than the last saved state for source.

    `observation_time` can be datetime, ISO string, or epoch.
    """
    state = load_state()

    if source not in state:
        # unknown source — treat as new
        return True

    last_time_raw = state[source].get("last_observation_time")
    last_dt = parse_time(last_time_raw)
    obs_dt = parse_time(observation_time)

    if obs_dt is None:
        # if we can't parse the incoming time, treat as not new
        return False

    if last_dt is None:
        return True

    return obs_dt > last_dt


def update_state(source: str, observation_time: Any) -> None:
    """Update the state's last_observation_time for `source` with `observation_time`.

    The stored value is an ISO-8601 UTC string.
    """
    state = load_state()
    if source not in state:
        state[source] = {"last_observation_time": None}

    obs_dt = parse_time(observation_time)
    if obs_dt is None:
        # if cannot parse, do not update
        return

    state[source]["last_observation_time"] = obs_dt.replace(tzinfo=timezone.utc).isoformat()
    save_state(state)
