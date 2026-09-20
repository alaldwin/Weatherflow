import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common.logging import get_logger


logger = get_logger(__name__, "save_json.log")


def _safe_name(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace(" ", "_")
    return re.sub(r"[^a-z0-9_-]", "_", s)


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

    root = Path(__file__).resolve().parents[2]

    safe_city = _safe_name(city)
    safe_source = _safe_name(source)

    output_dir = (
        root
        / "data"
        / "raw"
        / safe_source
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        output_dir
        / f"{safe_city}.json"
    )

    observation_time = _get_observation_time(data)

    # --------------------------------------------------
    # FIRST LOAD
    # --------------------------------------------------

    if not output_file.exists():

        records = [data]

        with output_file.open(
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                records,
                file,
                ensure_ascii=False,
                indent=4
            )

        logger.info(
            f"Initial load: "
            f"{source} - {city}"
        )

        return output_file

    # --------------------------------------------------
    # EXISTING DATA
    # --------------------------------------------------

    with output_file.open(
        "r",
        encoding="utf-8"
    ) as file:

        existing_data = json.load(file)

    if not isinstance(existing_data, list):
        existing_data = [existing_data]

    # --------------------------------------------------
    # DUPLICATE CHECK
    # --------------------------------------------------

    existing_times = {
        _get_observation_time(record)
        for record in existing_data
    }

    if observation_time in existing_times:

        logger.info(
            f"Duplicate skipped: "
            f"{source} - {city} - "
            f"{observation_time}"
        )

        return output_file

    # --------------------------------------------------
    # INCREMENTAL LOAD
    # --------------------------------------------------

    existing_data.append(data)

    with output_file.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            existing_data,
            file,
            ensure_ascii=False,
            indent=4
        )

    logger.info(
        f"Incremental load: "
        f"{source} - {city} - "
        f"{observation_time}"
    )

    return output_file