
from datetime import datetime, timezone

from pipeline.ingestion.state_manager import (
    is_new_data,
    update_state,
)


def test_new_observation_is_detected():
    """
    A newer observation should be considered new data.
    """

    location = "Manila"

    observation_time = datetime.now(timezone.utc).timestamp()

    result = is_new_data(
        source="openweather",
        location=location,
        observation_time=observation_time,
    )

    assert result is True


def test_state_can_be_updated():
    """
    Updating the state should not raise an exception.
    """

    location = "Manila"

    observation_time = datetime.now(timezone.utc).timestamp()

    update_state(
        source="openweather",
        location=location,
        observation_time=observation_time,
    )
