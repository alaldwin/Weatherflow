from datetime import datetime, timezone

import polars as pl
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

import pipeline.main as pipeline_main
from pipeline.loaded.load_postresql import (
    LOCATIONS_TABLE,
    REQUIRED_ENV_VARS,
    WEATHER_TABLE,
    build_database_url,
    check_database_connection,
    ensure_database_ready,
    get_database_name,
    get_maintenance_database,
    load_all_parquet_to_postgresql,
    load_data_to_postgresql,
    load_postgresql,
)
from pipeline.loaded.save_parquet import save_parquet
from pipeline.transformation.weather_transform import WeatherTransform


@pytest.fixture()
def sqlite_engine():
    """In-memory SQLite engine that exercises the same SQLAlchemy load path."""

    engine = create_engine("sqlite://", poolclass=StaticPool)
    try:
        yield engine
    finally:
        engine.dispose()


def _openweather_payload() -> dict:
    return {
        "coord": {"lon": 120.9842, "lat": 14.5995},
        "weather": [{"id": 500, "main": "Rain", "description": "light rain"}],
        "main": {"temp": 32.21, "pressure": 1011, "humidity": 69},
        "wind": {"speed": 3.09, "deg": 150},
        "name": "Manila",
    }


def _count_rows(engine, table_name: str) -> int:
    with engine.connect() as connection:
        return connection.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar_one()


def test_build_database_url_requires_every_variable(monkeypatch):
    for var in REQUIRED_ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    monkeypatch.setenv("POSTGRES_USER", "weatherflow")

    with pytest.raises(ValueError) as excinfo:
        build_database_url()

    assert "POSTGRES_DB" in str(excinfo.value)


def test_build_database_url_escapes_special_characters(monkeypatch):
    monkeypatch.setenv("POSTGRES_USER", "weatherflow")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p@ss/word")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DB", "weatherflow")

    url = build_database_url()

    assert url == (
        "postgresql+psycopg2://weatherflow:p%40ss%2Fword@localhost:5432/weatherflow"
    )


def test_transformed_data_loads_into_a_table(sqlite_engine):
    transformed = WeatherTransform(_openweather_payload(), "openweather").transform()

    loaded = load_postgresql(transformed, "openweather_manila", engine=sqlite_engine)

    assert loaded == 1

    with sqlite_engine.connect() as connection:
        columns = {column["name"] for column in inspect(connection).get_columns("openweather_manila")}
        row = connection.execute(
            text('SELECT city, temperature, humidity FROM "openweather_manila"')
        ).one()

    assert {
        "city",
        "latitude",
        "longitude",
        "temperature",
        "humidity",
        "pressure",
        "weather_description",
        "wind_speed",
    } <= columns
    assert row.city == "Manila"
    assert row.temperature == pytest.approx(32.21)
    assert row.humidity == 69


def test_save_parquet_from_raw_weather_payload(tmp_path):
    payload = {
        "name": "Manila",
        "coord": {"lon": 120.9842, "lat": 14.5995},
        "main": {"temp": 32.21, "pressure": 1011, "humidity": 69},
        "wind": {"speed": 3.09, "deg": 150},
        "weather": [{"id": 500, "main": "Rain", "description": "light rain"}],
        "dt": 1700000000,
    }

    original_dir = save_parquet.__globals__["parquet_dir"]
    save_parquet.__globals__["parquet_dir"] = tmp_path

    try:
        output_file = save_parquet(payload, "Manila", "openweather")
    finally:
        save_parquet.__globals__["parquet_dir"] = original_dir

    assert output_file is not None
    assert output_file.exists()
    df = pl.read_parquet(output_file)
    assert df["city"].to_list() == ["Manila"]
    assert df["temperature"].to_list() == [32.21]


def test_pipeline_main_saves_parquet_and_loads_to_postgresql(monkeypatch, tmp_path):
    pipeline_main.CITIES = {"Manila": {"latitude": 14.5995, "longitude": 120.9842}}
    payload = {
        "coord": {"lon": 120.9842, "lat": 14.5995},
        "weather": [{"id": 500, "main": "Rain", "description": "light rain"}],
        "main": {"temp": 32.21, "pressure": 1011, "humidity": 69},
        "wind": {"speed": 3.09, "deg": 150},
        "name": "Manila",
        "dt": 1700000000,
    }
    calls = []

    monkeypatch.setattr(pipeline_main, "extract_openweather_data", lambda *args, **kwargs: payload)
    monkeypatch.setattr(pipeline_main, "extract_geocoding_data", lambda *args, **kwargs: {"name": "Manila", "lat": 14.5995, "lon": 120.9842})
    monkeypatch.setattr(pipeline_main, "is_new_data", lambda **kwargs: True)
    monkeypatch.setattr(pipeline_main, "save_json", lambda **kwargs: tmp_path / "manila.json")
    monkeypatch.setattr(pipeline_main, "update_state", lambda **kwargs: calls.append("state"))
    monkeypatch.setattr(pipeline_main, "save_parquet", lambda df, city, source: calls.append((df, city, source)) or (tmp_path / f"{source}_{city}.parquet"))
    monkeypatch.setattr(pipeline_main, "load_postgresql", lambda df, table_name, **kwargs: calls.append((df, table_name)) or 1)

    result = pipeline_main.main()

    assert result == 0
    assert any(call == "state" for call in calls)
    assert any(isinstance(call, tuple) and len(call) == 3 and call[1] == "Manila" and call[2] == "openweather" for call in calls)
    assert any(isinstance(call, tuple) and len(call) == 2 and call[1] == WEATHER_TABLE for call in calls)


def test_pipeline_main_uses_canonical_tables(monkeypatch, tmp_path):
    pipeline_main.CITIES = {"Manila": {"latitude": 14.5995, "longitude": 120.9842}}
    payload = {
        "coord": {"lon": 120.9842, "lat": 14.5995},
        "weather": [{"id": 500, "main": "Rain", "description": "light rain"}],
        "main": {"temp": 32.21, "pressure": 1011, "humidity": 69},
        "wind": {"speed": 3.09, "deg": 150},
        "name": "Manila",
        "dt": 1700000000,
    }
    calls = []

    monkeypatch.setattr(pipeline_main, "extract_openweather_data", lambda *args, **kwargs: payload)
    monkeypatch.setattr(pipeline_main, "extract_geocoding_data", lambda *args, **kwargs: {"name": "Manila", "lat": 14.5995, "lon": 120.9842})
    monkeypatch.setattr(pipeline_main, "is_new_data", lambda **kwargs: True)
    monkeypatch.setattr(pipeline_main, "save_json", lambda **kwargs: tmp_path / "manila.json")
    monkeypatch.setattr(pipeline_main, "update_state", lambda **kwargs: calls.append("state"))
    monkeypatch.setattr(pipeline_main, "save_parquet", lambda df, city, source: calls.append((df, city, source)) or (tmp_path / f"{source}_{city}.parquet"))

    def fake_load(df, table_name, **kwargs):
        calls.append(("load", table_name))
        return 1

    monkeypatch.setattr(pipeline_main, "load_postgresql", fake_load)

    result = pipeline_main.main()

    load_calls = [call for call in calls if isinstance(call, tuple) and len(call) == 2 and call[0] == "load"]

    assert result == 0
    assert any(call == ("load", LOCATIONS_TABLE) for call in load_calls)
    assert any(call == ("load", WEATHER_TABLE) for call in load_calls)
    assert all(call[1] != "openweather_manila" for call in load_calls)
    assert all(call[1] != "geocoding_manila" for call in load_calls)


def test_pipeline_main_returns_nonzero_when_city_fails(monkeypatch):
    pipeline_main.CITIES = {"Manila": {"latitude": 14.5995, "longitude": 120.9842}}

    monkeypatch.setattr(
        pipeline_main,
        "extract_openweather_data",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("API failure")),
    )

    result = pipeline_main.main()

    assert result == 1


def test_load_all_parquet_files_into_single_table(sqlite_engine, tmp_path):
    city_a = pl.DataFrame({"city": ["Manila"], "temperature": [32.21], "source": ["openweather"]})
    city_b = pl.DataFrame({"city": ["Cebu"], "temperature": [29.4], "source": ["openweather"]})
    city_a.write_parquet(tmp_path / "manila.parquet")
    city_b.write_parquet(tmp_path / "cebu.parquet")

    rows = load_all_parquet_to_postgresql(tmp_path, "openweather_all", engine=sqlite_engine)

    assert rows == 2
    assert _count_rows(sqlite_engine, "openweather_all") == 2
    with sqlite_engine.connect() as connection:
        cities = connection.execute(text('SELECT city FROM "openweather_all" ORDER BY city')).scalars().all()

    assert cities == ["Cebu", "Manila"]


def test_default_load_replaces_previous_rows(sqlite_engine):
    df = pl.DataFrame({"city": ["Manila"], "temperature": [32.21]})

    load_postgresql(df, "openweather_manila", engine=sqlite_engine)
    load_postgresql(df, "openweather_manila", engine=sqlite_engine)

    assert _count_rows(sqlite_engine, "openweather_manila") == 1


def test_append_mode_keeps_existing_rows(sqlite_engine):
    df = pl.DataFrame({"city": ["Manila"], "temperature": [32.21]})

    load_postgresql(df, "openweather_manila", engine=sqlite_engine, if_exists="append")
    load_postgresql(df, "openweather_manila", engine=sqlite_engine, if_exists="append")

    assert _count_rows(sqlite_engine, "openweather_manila") == 2


def test_append_mode_adds_missing_columns(sqlite_engine):
    load_postgresql(
        pl.DataFrame({"city": ["Manila"], "temperature": [32.21]}),
        "openweather_manila",
        engine=sqlite_engine,
        if_exists="append",
    )
    load_postgresql(
        pl.DataFrame({"city": ["Manila"], "temperature": [30.5], "humidity": [70]}),
        "openweather_manila",
        engine=sqlite_engine,
        if_exists="append",
    )

    with sqlite_engine.connect() as connection:
        columns = {column["name"] for column in inspect(connection).get_columns("openweather_manila")}
        humidity = connection.execute(
            text('SELECT humidity FROM "openweather_manila" WHERE humidity IS NOT NULL')
        ).scalar_one()

    assert "humidity" in columns
    assert humidity == 70


def test_weather_table_append_adds_new_schema_columns(sqlite_engine):
    first = pl.DataFrame(
        {
            "city": ["Manila"],
            "observation_time": [datetime.now(timezone.utc)],
            "source": ["openweather"],
            "temperature": [32.21],
        }
    )
    second = pl.DataFrame(
        {
            "city": ["Manila"],
            "observation_time": [datetime.now(timezone.utc)],
            "source": ["openweather"],
            "temperature": [30.5],
            "new_metric": [7.5],
        }
    )

    load_postgresql(first, WEATHER_TABLE, engine=sqlite_engine, if_exists="append")
    load_postgresql(second, WEATHER_TABLE, engine=sqlite_engine, if_exists="append")

    with sqlite_engine.connect() as connection:
        columns = {column["name"] for column in inspect(connection).get_columns(WEATHER_TABLE)}
        new_metric = connection.execute(
            text(f'SELECT "new_metric" FROM "{WEATHER_TABLE}" WHERE "new_metric" IS NOT NULL')
        ).scalar_one()

    assert "new_metric" in columns
    assert new_metric == 7.5


def test_fail_mode_raises_when_table_exists(sqlite_engine):
    df = pl.DataFrame({"city": ["Manila"]})

    load_postgresql(df, "openweather_manila", engine=sqlite_engine)

    with pytest.raises(ValueError):
        load_postgresql(df, "openweather_manila", engine=sqlite_engine, if_exists="fail")


def test_invalid_if_exists_mode_is_rejected(sqlite_engine):
    df = pl.DataFrame({"city": ["Manila"]})

    with pytest.raises(ValueError):
        load_postgresql(df, "openweather_manila", engine=sqlite_engine, if_exists="drop-everything")


def test_empty_dataframe_is_skipped(sqlite_engine):
    empty = pl.DataFrame({"city": [], "temperature": []})

    assert load_postgresql(empty, "openweather_manila", engine=sqlite_engine) == 0


def test_load_from_parquet_file_path(sqlite_engine, tmp_path):
    parquet_path = tmp_path / "manila.parquet"
    df = pl.DataFrame({"city": ["Manila"], "temperature": [32.21]})
    df.write_parquet(parquet_path)

    assert load_postgresql(parquet_path, "openweather_manila", engine=sqlite_engine) == 1

    with sqlite_engine.connect() as connection:
        row = connection.execute(text('SELECT city, temperature FROM "openweather_manila"')).one()

    assert row.city == "Manila"
    assert row.temperature == pytest.approx(32.21)


def test_non_dataframe_input_is_rejected(sqlite_engine):
    with pytest.raises(TypeError):
        load_postgresql({"city": "Manila"}, "openweather_manila", engine=sqlite_engine)


def test_backward_compatible_alias(sqlite_engine):
    df = pl.DataFrame({"city": ["Manila"]})

    assert load_data_to_postgresql(df, "city_alias_table", engine=sqlite_engine) == 1


def test_check_database_connection_true_for_reachable_database(sqlite_engine):
    assert check_database_connection(sqlite_engine) is True


def test_check_database_connection_false_for_unreachable_database():
    engine = create_engine("postgresql+psycopg2://weatherflow:weatherflow@127.0.0.1:1/weatherflow")
    try:
        assert check_database_connection(engine) is False
    finally:
        engine.dispose()


def test_ensure_database_ready_true_for_reachable_database(sqlite_engine):
    assert ensure_database_ready(sqlite_engine) is True


def test_ensure_database_ready_false_when_server_is_down():
    engine = create_engine("postgresql+psycopg2://weatherflow:weatherflow@127.0.0.1:1/weatherflow")
    try:
        # The engine is passed on purpose: no database creation is attempted.
        assert ensure_database_ready(engine) is False
    finally:
        engine.dispose()


def test_database_name_comes_from_environment(monkeypatch):
    monkeypatch.setenv("POSTGRES_DB", "weatherflow_test")

    assert get_database_name() == "weatherflow_test"


def test_maintenance_database_defaults_to_postgres(monkeypatch):
    monkeypatch.delenv("POSTGRES_MAINTENANCE_DB", raising=False)

    assert get_maintenance_database() == "postgres"


def test_maintenance_database_can_be_overridden(monkeypatch):
    monkeypatch.setenv("POSTGRES_MAINTENANCE_DB", "template1")

    assert get_maintenance_database() == "template1"