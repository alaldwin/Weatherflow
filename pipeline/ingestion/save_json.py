import json
import datetime

from pathlib import Path

from common.logging import get_logger


logger = get_logger(__name__, "save_json.log")


def save_json(data: dict, city: str, source: str) -> Path:
    """
    Saves the given data as a JSON file in the appropriate directory.

    Args:
        data (dict): The data to save.
        city (str): The city for which to save data.
        source (str): The source of the data.

    Returns:
        Path: The path to the saved JSON file.
    """

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    safe_city = city.strip().lower().replace(" ", "_")

    root = Path(__file__).resolve().parents[2]
    output_dir = root / "data" / source
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{safe_city}_{today}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    logger.info(f"Saved data from {source} to {output_file}")

    return output_file