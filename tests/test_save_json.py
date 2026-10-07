
from pathlib import Path

import pipeline.ingestion.save_json as save_json_module


def test_save_json_creates_file(tmp_path, monkeypatch):
    """
    Test that save_json creates a JSON file
    containing the OpenWeather observation.
    """

    # Use pytest temporary directory
    monkeypatch.setattr(
        save_json_module,
        "RAW_DIR",
        tmp_path,
    )

    weather_data = {
        "coord": {
            "lon": 120.9842,
            "lat": 14.5995,
        },
        "weather": [
            {
                "description": "clear sky",
            }
        ],
        "main": {
            "temp": 30.5,
            "humidity": 70,
        },
        "dt": 1791283200,
        "name": "Manila",
    }

    output_file = save_json_module.save_json(
        data=weather_data,
        city="Manila",
        source="openweather",
    )

    assert output_file is not None
    assert output_file.exists()

    assert output_file == (
        tmp_path
        / "openweather"
        / "manila.json"
    )


def test_save_json_does_not_duplicate_observation(
    tmp_path,
    monkeypatch,
):
    """
    The same OpenWeather observation should
    not be saved twice.
    """

    monkeypatch.setattr(
        save_json_module,
        "RAW_DIR",
        tmp_path,
    )

    weather_data = {
        "name": "Manila",
        "dt": 1791283200,
        "main": {
            "temp": 30.5,
        },
    }

    first_file = save_json_module.save_json(
        data=weather_data,
        city="Manila",
        source="openweather",
    )

    second_file = save_json_module.save_json(
        data=weather_data,
        city="Manila",
        source="openweather",
    )

    assert first_file == second_file

    content = second_file.read_text(
        encoding="utf-8"
    )

    # The observation should only exist once.
    assert content.count('"dt": 1791283200') == 1

