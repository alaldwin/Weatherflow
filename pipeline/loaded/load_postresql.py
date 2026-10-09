import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2

from urllib.parse import quote_plus

from psycopg2 import sql
import polars as pl

from dotenv import load_dotenv

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    inspect,
    text,
)

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Connection, Engine

from common.logging import get_logger



logger = get_logger(__name__, "load_postgresql.log")

load_dotenv()



# PostgreSQL CONFIGURATION

REQUIRED_ENV_VARS = (
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
)

VALID_IF_EXISTS = ("replace", "append", "fail",)

# Fresh runs should replace stale rows; append is still supported for explicit schema-evolution loads.
DEFAULT_IF_EXISTS = "replace"

"""
 Canonical PostgreSQL table names.

 IMPORTANT:
 Do not create:
   openweather_manila
   openweather_cebu_city
   geocoding_manila

 Use these two tables instead.
"""

LOCATIONS_TABLE = "locations"
WEATHER_TABLE = "weather_observations"



# DATABASE CONNECTION
def build_database_url() -> str:

    """Build the PostgreSQL SQLAlchemy URL."""

    missing = [variable for variable in REQUIRED_ENV_VARS if not os.getenv(variable)]

    if missing:
        raise ValueError("Missing PostgreSQL environment variables: " + ", ".join(missing))

    user = quote_plus(os.getenv("POSTGRES_USER", ""))

    password = quote_plus(os.getenv("POSTGRES_PASSWORD", ""))

    host = os.getenv("POSTGRES_HOST", "localhost",)

    port = os.getenv("POSTGRES_PORT", "5432",)

    database = os.getenv("POSTGRES_DB", "",)

    return (f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}")



def get_database_target() -> str:

    """Return a readable PostgreSQL target."""

    host = os.getenv("POSTGRES_HOST", "localhost",)

    port = os.getenv("POSTGRES_PORT", "5432",)

    database = os.getenv("POSTGRES_DB", "<database>",)

    user = os.getenv("POSTGRES_USER", "<user>",)

    return f"{user}@{host}:{port}/{database}"


def get_database_name() -> str:

    """Return configured database name."""

    return os.getenv("POSTGRES_DB", "",)

 

def get_maintenance_database() -> str:

    """Return maintenance database."""

    return os.getenv("POSTGRES_MAINTENANCE_DB", "postgres",)


def _maintenance_connection():
    """Connect to PostgreSQL maintenance database."""

    missing = [ variable for variable in REQUIRED_ENV_VARS if not os.getenv(variable)]

    if missing:
        raise ValueError("Missing PostgreSQL environment variables: " + ", ".join(missing))
    

    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        user=os.getenv("POSTGRES_USER", ""),
        password=os.getenv("POSTGRES_PASSWORD", "",),
        dbname=get_maintenance_database(),
        connect_timeout=10,
    )


def database_exists() -> bool:

    """Return True when the configured database exists."""

    connection = _maintenance_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL(
                    "SELECT 1 "
                    "FROM pg_database "
                    "WHERE datname = {}"
                ).format(
                    sql.Literal(
                        get_database_name()
                    )
                )
            )

            return cursor.fetchone() is not None

    finally:
        connection.close()


def create_database() -> bool:

    """Create the configured database when missing."""

    from psycopg2 import sql
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    if database_exists():
        logger.info(
            "PostgreSQL database '%s' already exists.",
            get_database_name(),
        )
        return False

    connection = _maintenance_connection()

    connection.set_isolation_level(
        ISOLATION_LEVEL_AUTOCOMMIT
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL(
                    "CREATE DATABASE {}"
                ).format(
                    sql.Identifier(
                        get_database_name()
                    )
                )
            )

    finally:
        connection.close()

    logger.info("Created PostgreSQL database '%s'.", get_database_name(),)

    return True


def get_engine(**engine_kwargs: Any) -> Engine:

    """Create SQLAlchemy PostgreSQL engine."""

    return create_engine(
        build_database_url(),
        pool_pre_ping=True,
        **engine_kwargs,
    )


def check_database_connection(
    engine: Engine | None = None,
    log_errors: bool = True,
) -> bool:

    """Check PostgreSQL connection."""

    try:
        engine = (engine if engine is not None else get_engine())

        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return True

    except Exception as exc:

        if log_errors:
            logger.error("PostgreSQL is not reachable at " "%s: %s", get_database_target(), exc)

        return False


def ensure_database_ready(engine: Engine | None = None) -> bool:

    """Ensure the PostgreSQL database is ready."""

    if check_database_connection(engine, log_errors=False):
        return True
  
    if engine is None:

        try:

            if create_database() and check_database_connection(log_errors=False): 
                return True
  
        except Exception as exc:
            logger.debug("Automatic database creation failed: %s", exc) 
  
    check_database_connection(engine)

    return False



# DATAFRAME HELPERS
def _coerce_data_frame(
    data: (
        pl.DataFrame
        | pl.LazyFrame
        | str
        | os.PathLike[str]
    ),
) -> pl.DataFrame:

    """Convert supported input into a Polars DataFrame."""

    if isinstance(data, (str, os.PathLike)):

        parquet_path = Path(data)

        if not parquet_path.exists():
            raise FileNotFoundError(
                f"Parquet file does not exist: "
                f"{parquet_path}"
            )

        return pl.read_parquet(parquet_path)

    if isinstance(data, pl.LazyFrame):
        return data.collect()

    if isinstance(data, pl.DataFrame):
        return data

    raise TypeError(
        "Expected a Polars DataFrame, "
        "LazyFrame, or Parquet path. "
        f"Got {type(data)!r}"
    )


def _clean_value(value: Any) -> Any:

    """Convert values into PostgreSQL-safe values."""

    if isinstance(value, float):

        if not math.isfinite(value):
            return None

    if isinstance(value, (list, dict)):
        return json.dumps(value)

    return value


def _sqlalchemy_type(dtype: pl.DataType) -> Any:

    """Map Polars dtype to SQLAlchemy type."""

    if isinstance(dtype, pl.Datetime):
        return DateTime(timezone=True)

    if dtype == pl.Date:
        return Date()

    if dtype == pl.Boolean:
        return Boolean()

    if dtype in (pl.Int64, pl.UInt64, pl.UInt32, pl.Int32):
        return BigInteger()

    if dtype in (pl.Int8, pl.Int16, pl.UInt8, pl.UInt16):
        return Integer()

    if isinstance(dtype, pl.Decimal):
        return Numeric(38, 10)

    if dtype in (pl.Float32, pl.Float64):
        return Float()

    return Text()


def _column_definitions(df: pl.DataFram) -> list[Column]:
    """Create SQLAlchemy columns from DataFrame schema."""

    return [Column(name, _sqlalchemy_type(dtype)) for name, dtype in df.schema.items()]


def _infer_legacy_source(table_name: str) -> str:
    """Infer the legacy source name from the table name."""

    lowered = table_name.lower()

    if lowered.startswith("geocoding_"):
        return "geocoding"

    if lowered.startswith("weather_"):
        return "openweather"

    if lowered.startswith("openweather_"):
        return "openweather"

    return "openweather"


def _create_legacy_table(
    connection: Connection,
    table_name: str,
    df: pl.DataFrame,
) -> Table:
    """Create a simple table from the DataFrame schema without legacy uniqueness rules."""

    metadata = MetaData()
    columns = [Column(name, _sqlalchemy_type(dtype), nullable=True) for name, dtype in df.schema.items()]
    table = Table(table_name, metadata, *columns)
    table.create(bind=connection, checkfirst=True)
    return table


def _ensure_legacy_table_columns(
    connection: Connection,
    table_name: str,
    df: pl.DataFrame,
) -> None:
    """Add columns missing from an existing legacy table."""

    inspector = inspect(connection)
    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}

    for column_name, dtype in df.schema.items():
        if column_name in existing_columns:
            continue

        column = Column(column_name, _sqlalchemy_type(dtype), nullable=True)
        ddl_type = column.type.compile(dialect=connection.dialect)
        connection.execute(
            text(f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {ddl_type}')
        )


def _load_legacy_table(
    data: pl.DataFrame | pl.LazyFrame,
    table_name: str,
    if_exists: str | None = None,
    engine: Engine | None = None,
) -> int:
    """Load into legacy city-specific tables retained for backward compatibility."""

    if if_exists is None:
        if_exists = DEFAULT_IF_EXISTS

    if if_exists not in VALID_IF_EXISTS:
        raise ValueError(f"Unsupported if_exists value: {if_exists!r}")

    df = _coerce_data_frame(data)

    if df.is_empty():
        logger.warning("No data to load into legacy table '%s'.", table_name)
        return 0

    legacy_source = table_name.lower().startswith("geocoding_")
    if legacy_source:
        required = {"city", "latitude", "longitude"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing geocoding columns: {missing}")
    elif "city" not in df.columns:
        raise ValueError("Missing weather columns: {'city'}")

    engine = engine if engine is not None else get_engine()
    rows = [
        {key: _clean_value(value) for key, value in row.items()}
        for row in df.to_dicts()
    ]

    if not rows:
        return 0

    with engine.begin() as connection:
        inspector = inspect(connection)
        exists = inspector.has_table(table_name)

        if exists:
            if if_exists == "fail":
                raise ValueError(f"Table '{table_name}' already exists.")
            if if_exists == "replace":
                connection.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
                _create_legacy_table(connection, table_name, df)
            elif if_exists == "append":
                _ensure_legacy_table_columns(connection, table_name, df)
        else:
            _create_legacy_table(connection, table_name, df)

        table = Table(table_name, MetaData(), autoload_with=connection)
        connection.execute(table.insert().values(rows))

    logger.info("Loaded %d row(s) into legacy table '%s'.", len(rows), table_name)
    return len(rows)


# LOCATIONS TABLE

def _create_locations_table(
    connection: Connection,
) -> Table:

    """
    Create one locations table.

    Geocoding data from every city goes here.
    """

    metadata = MetaData()

    table = Table(LOCATIONS_TABLE, metadata,

        Column("id", BigInteger, primary_key=True, autoincrement=True),

        Column("city", String(255), nullable=False),

        Column("latitude", Float, nullable=False),

        Column("longitude", Float, nullable=False),

        Column("country", String(10), nullable=True),

        Column("state", String(255), nullable=True),

        UniqueConstraint("city", "latitude", "longitude", name="uq_locations_city_coordinates"),
    )

    table.create(bind=connection, checkfirst=True)

    return table


def load_locations(
    data: pl.DataFrame | pl.LazyFrame,
    engine: Engine | None = None,
) -> int:

    """
    Load all geocoding records into locations.

    Expected columns:

        city
        latitude
        longitude
        country
        state
    """

    df = _coerce_data_frame(data)

    if df.is_empty():
        logger.warning("No geocoding data to load.")
        return 0

    required_columns = {
        "city",
        "latitude",
        "longitude",
    }

    missing = (required_columns - set(df.columns))

    if missing:
        raise ValueError(
            "Missing geocoding columns: "
            f"{missing}"
        )

    engine = (engine if engine is not None else get_engine())

    rows = [
        {
            key: _clean_value(value)
            for key, value in row.items()
            if key in {
                "city",
                "latitude",
                "longitude",
                "country",
                "state",
            }
        }
        for row in df.to_dicts()
    ]

    if not rows:
        return 0

    try:

        with engine.begin() as connection:

            table = _create_locations_table(connection)

            statement = pg_insert(table).values(rows)

            statement = (
                statement.on_conflict_do_update(
                    constraint=(
                        "uq_locations_city_coordinates"
                    ),
                    set_={
                        "country": (
                            statement.excluded.country
                        ),
                        "state": (
                            statement.excluded.state
                        ),
                    },
                )
            )

            connection.execute(
                statement
            )

        logger.info("Loaded %d location record(s)" "into '%s'.", len(rows),  LOCATIONS_TABLE)

        return len(rows)

    except Exception:
        logger.exception("Failed to load locations.")
        raise



# WEATHER OBSERVATIONS TABLE

def _create_weather_table(connection: Connection) -> Table:
    """
    Create one weather observations table.

    All cities share this table.
    """

    metadata = MetaData()

    table = Table(WEATHER_TABLE, metadata,

        Column("id", BigInteger, primary_key=True, autoincrement=True),

        # Location
        Column("city", String(255), nullable=False), 
        Column("city_id", BigInteger, nullable=True), 
        Column("latitude", Float, nullable=True),
        Column("longitude", Float, nullable=True), 
        Column("country", String(10), nullable=True), 
        Column("timezone", Integer, nullable=True), 
        Column("base", Text, nullable=True),

        # Weather Condition
        Column("weather_id", Integer, nullable=True), 
        Column("weather_main", String(100), nullable=True), 
        Column("weather_description", Text, nullable=True), 
        Column("weather_icon", String(20), nullable=True),

        # Temperature and atmospheric conditions
        Column("temperature", Float, nullable=True), 
        Column("feels_like", Float, nullable=True), 
        Column("temp_min", Float, nullable=True), 
        Column("temp_max", Float, nullable=True), 
        Column("pressure", Integer, nullable=True), 
        Column("humidity", Integer, nullable=True), 
        Column("sea_level", Integer, nullable=True), 
        Column("ground_level", Integer, nullable=True), 
        Column("visibility", Integer, nullable=True),

        # Wind, rain, and clouds 
        Column("wind_speed", Float, nullable=True), 
        Column("wind_direction", Integer, nullable=True), 
        Column("wind_gust", Float, nullable=True), 
        Column("rain_1h", Float, nullable=True),
        Column("cloudiness", Integer, nullable=True),

        # Timestamps and API metadata 
        Column("observation_time", DateTime(timezone=True), nullable=False), 
        Column("sunrise", BigInteger, nullable=True), 
        Column("sunset", BigInteger, nullable=True), 
        Column("cod", String(20), nullable=True), 
        Column("source", String(50), nullable=False), 
        Column("ingested_time", DateTime(timezone=True), nullable=True),

        UniqueConstraint(
            "city",
            "observation_time",
            "source",
            name=(
                "uq_weather_city_observation_source"
            ),
        ),
    )

    table.create(bind=connection, checkfirst=True)

    return table



def _ensure_weather_table_columns( connection: Connection, df: pl.DataFrame, ) -> None:
    """Add missing weather columns to an existing table."""

    table = _create_weather_table(connection)

    inspector = inspect(connection)

    existing_columns = { column["name"] for column in inspector.get_columns(WEATHER_TABLE) }

    # Use the canonical table definition for SQL column types.
    for column in table.columns: 
        if column.name == "id" or column.name in existing_columns: 
            continue 

        ddl_type = column.type.compile( dialect=connection.dialect ) 

        connection.execute( 
            text( 
                f'ALTER TABLE "{WEATHER_TABLE}" ' 
                f'ADD COLUMN "{column.name}" {ddl_type}' 
            ) 
        )

    # Support columns present in a future Parquet schema.
    inspector = inspect(connection) 
    existing_columns = { column["name"] for column in inspector.get_columns(WEATHER_TABLE) }

    for column_name, dtype in df.schema.items(): 
        if column_name in existing_columns: 
            continue

        column_type = _sqlalchemy_type(dtype) 
        ddl_type = column_type.compile( 
            dialect=connection.dialect 
        )

        connection.execute( 
            text( 
                f'ALTER TABLE "{WEATHER_TABLE}" ' 
                f'ADD COLUMN "{column_name}" {ddl_type}' 
            ) 
        )



def load_weather_observations(data: pl.DataFrame | pl.LazyFrame,engine: Engine | None = None) -> int:
    """
    Load OpenWeather observations into one table.

    Duplicate key:

        city + observation_time + source

    Existing observations are updated instead
    of inserted again.
    """

    df = _coerce_data_frame(data)

    if df.is_empty():
        logger.warning("No weather observations to load.")
        return 0

    required_columns = {"city", "observation_time", "source"}

    missing = (required_columns - set(df.columns))

    if missing:
        raise ValueError(f"Missing weather columns: {missing}")

    engine = (engine if engine is not None else get_engine())

    allowed_columns = {
        "city",
        "city_id",
        "latitude",
        "longitude",
        "country",
        "timezone",
        "base",
        "weather_id",
        "weather_main",
        "weather_description",
        "weather_icon",
        "temperature",
        "feels_like",
        "temp_min",
        "temp_max",
        "pressure",
        "humidity",
        "sea_level",
        "ground_level",
        "visibility",
        "wind_speed",
        "wind_direction",
        "wind_gust",
        "rain_1h",
        "cloudiness",
        "observation_time",
        "sunrise",
        "sunset",
        "cod",
        "source",
        "ingested_time",
    }
    allowed_columns |= set(df.columns)

    rows = [
        {
            key: _clean_value(value)
            for key, value in row.items()
            if key in allowed_columns
        }
        for row in df.to_dicts()
    ]

    if not rows:
        return 0

    try:

        with engine.begin() as connection:
            _create_weather_table(connection)
            _ensure_weather_table_columns(connection, df)

            # Reflect the table after any schema changes.
            table = Table(WEATHER_TABLE, MetaData(), autoload_with=connection)

            statement = pg_insert(table).values(rows)

            # Update every non-key field when an observation already exists.
            key_columns = {"id", "city", "observation_time", "source"}

            update_columns = {
                column: getattr(statement.excluded, column)
                for column in table.columns
                if column.name in allowed_columns and column.name not in key_columns
            }

            statement = (
                statement.on_conflict_do_update(constraint=("uq_weather_city_observation_source"), set_=update_columns)
            )

            connection.execute(statement)

        logger.info("Loaded %d weather observation(s) " "into '%s'.", len(rows), WEATHER_TABLE)

        return len(rows)

    except Exception:
        logger.exception("Failed to load weather observations.")
        raise



# MAIN LOADER

def load_postgresql(
    df: (
        pl.DataFrame
        | pl.LazyFrame
        | str
        | os.PathLike[str]
    ),
    table_name: str,
    if_exists: str | None = None,
    engine: Engine | None = None,
    schema: str | None = None,
) -> int:

    """
    Main PostgreSQL loader.

    Supported tables:

        locations
        weather_observations

    All cities are stored in these shared tables.
    """

    if if_exists is None:
        if_exists = DEFAULT_IF_EXISTS

    if if_exists not in VALID_IF_EXISTS:
        raise ValueError(f"Unsupported if_exists value: {if_exists!r}")

    legacy_prefixes = ("openweather_", "geocoding_", "weather_")
    if table_name.startswith(legacy_prefixes) or table_name not in {LOCATIONS_TABLE, WEATHER_TABLE}:
        return _load_legacy_table(df, table_name, if_exists=if_exists, engine=engine)

    # Canonical table routing
    if table_name == LOCATIONS_TABLE:
        return load_locations(_coerce_data_frame(df), engine=engine)

    if table_name == WEATHER_TABLE:
        return load_weather_observations(_coerce_data_frame(df), engine=engine)

    raise ValueError(
        f"Unsupported PostgreSQL table "
        f"'{table_name}'. "
        f"Use '{LOCATIONS_TABLE}' or "
        f"'{WEATHER_TABLE}'."
    )



# BACKWARD-COMPATIBLE FUNCTIONS

def load_data_to_postgresql(df: (pl.DataFrame | pl.LazyFrame | str| os.PathLike[str]), table_name: str, **kwargs: Any) -> int:

    """Backward-compatible alias."""

    return load_postgresql(df, table_name, **kwargs)


def load_parquet_to_postgresql(
    parquet_path: str | os.PathLike[str],
    table_name: str,
    **kwargs: Any,
) -> int:

    """Load one Parquet file into PostgreSQL."""

    return load_postgresql(parquet_path, table_name, **kwargs)


def load_all_parquet_to_postgresql(
    parquet_dir: str | os.PathLike[str],
    table_name: str = WEATHER_TABLE,
    if_exists: str | None = None,
    engine: Engine | None = None,
    schema: str | None = None,
) -> int:

    """
    Load all Parquet files in a directory.

    Example:

        data/parquet/openweather/

    All city files are combined into the single
    weather_observations table.
    """

    directory = Path(parquet_dir)

    if not directory.exists():
        raise FileNotFoundError(
            "Parquet directory does not exist: "
            f"{directory}"
        )

    files = sorted(directory.glob("*.parquet"))

    if not files:
        logger.warning("No Parquet files found in %s.", directory)
        return 0

    frames = [pl.read_parquet(file) for file in files]

    combined = pl.concat(frames, how="diagonal_relaxed")

    return load_postgresql(combined, table_name=table_name, if_exists=if_exists, engine=engine, schema=schema)

