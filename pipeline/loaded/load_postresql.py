import json
import math
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

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
    Table,
    Text,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.engine import Connection, Engine

from common.logging import get_logger

logger = get_logger(__name__, "load_postgresql.log")

load_dotenv()

REQUIRED_ENV_VARS = (
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
)

VALID_IF_EXISTS = ("replace", "append", "fail")
DEFAULT_IF_EXISTS = "replace"  # Default behavior when POSTGRES_IF_EXISTS is not set


def build_database_url() -> str:
    """Build the PostgreSQL SQLAlchemy URL from environment variables."""

    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing PostgreSQL environment variables: {', '.join(missing)}")

    user = quote_plus(os.getenv("POSTGRES_USER", ""))
    password = quote_plus(os.getenv("POSTGRES_PASSWORD", ""))
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "")

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"


def get_database_target() -> str:
    """Return a human readable description of the configured database."""

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "<database>")
    user = os.getenv("POSTGRES_USER", "<user>")

    return f"{user}@{host}:{port}/{database}"


def get_database_name() -> str:
    """Return the configured target database name."""

    return os.getenv("POSTGRES_DB", "")


def get_maintenance_database() -> str:
    """Return the maintenance database used to create the target database."""

    return os.getenv("POSTGRES_MAINTENANCE_DB", "postgres")


def _maintenance_connection():
    """Open a psycopg2 connection to the maintenance database."""

    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing PostgreSQL environment variables: {', '.join(missing)}")

    import psycopg2

    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        user=os.getenv("POSTGRES_USER", ""),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        dbname=get_maintenance_database(),
        connect_timeout=10,
    )


def database_exists() -> bool:
    """Return True when the configured database exists on the server."""

    from psycopg2 import sql

    connection = _maintenance_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("SELECT 1 FROM pg_database WHERE datname = {}").format(
                    sql.Literal(get_database_name())
                )
            )
            return cursor.fetchone() is not None
    finally:
        connection.close()


def create_database() -> bool:
    """Create the configured database when missing; return True when created."""

    from psycopg2 import sql
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    if database_exists():
        logger.info(f"PostgreSQL database '{get_database_name()}' already exists.")
        return False

    connection = _maintenance_connection()
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(get_database_name()))
            )
    finally:
        connection.close()

    logger.info(f"Created PostgreSQL database '{get_database_name()}'.")
    return True


def get_engine(**engine_kwargs: Any) -> Engine:
    """Create a SQLAlchemy engine for the configured PostgreSQL database."""

    return create_engine(build_database_url(), pool_pre_ping=True, **engine_kwargs)


def check_database_connection(engine: Engine | None = None, log_errors: bool = True) -> bool:
    """Return True when the configured PostgreSQL database accepts connections."""

    try:
        engine = engine if engine is not None else get_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        if log_errors:
            logger.error(
                f"PostgreSQL is not reachable at {get_database_target()}: {exc}. "
                "Check that the server is running and that the POSTGRES_* values in "
                "your .env file are correct, then run the pipeline again."
            )
        return False


def ensure_database_ready(engine: Engine | None = None) -> bool:
    """Return True when the target database exists and is reachable.

    A missing database is created automatically on the configured server, so a
    freshly installed local PostgreSQL works without manual preparation.
    """

    if check_database_connection(engine, log_errors=False):
        return True

    # Auto-creation only makes sense against a real server (not a test engine).
    if engine is None:
        try:
            if create_database() and check_database_connection(log_errors=False):
                logger.info(f"Using newly created database '{get_database_name()}'.")
                return True
        except Exception as exc:
            logger.debug(f"Automatic database creation failed: {exc}")

    # Surface the actionable error message once.
    check_database_connection(engine)
    return False


def _quote(identifier: str) -> str:
    """Quote a SQL identifier so reserved words / mixed case keep working."""

    return '"' + identifier.replace('"', '""') + '"'


def _qualified_name(table_name: str, schema: str | None = None) -> str:
    if schema:
        return f"{_quote(schema)}.{_quote(table_name)}"
    return _quote(table_name)


def _sqlalchemy_type(dtype: pl.DataType) -> Any:
    """Map a Polars dtype to a SQLAlchemy column type."""

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
    # Strings, nulls and any unsupported dtype are stored as text.
    return Text()


def _column_definitions(df: pl.DataFrame) -> list[Column]:
    return [Column(name, _sqlalchemy_type(dtype)) for name, dtype in df.schema.items()]


def _clean_value(value: Any) -> Any:
    """Make a DataFrame cell safe for PostgreSQL."""

    if isinstance(value, float) and not math.isfinite(value):
        # NaN / Infinity are not valid for every PostgreSQL column type.
        return None
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return value


def _create_table(connection: Connection, table_name: str, df: pl.DataFrame, schema: str | None) -> None:
    """Create the destination table when it does not exist yet."""

    table = Table(table_name, MetaData(), *_column_definitions(df), schema=schema)
    table.create(bind=connection, checkfirst=True)


def _ensure_columns(connection: Connection, table_name: str, df: pl.DataFrame, schema: str | None) -> None:
    """Add DataFrame columns that are missing from an existing table."""

    inspector = inspect(connection)
    if not inspector.has_table(table_name, schema=schema):
        return

    existing = {column["name"] for column in inspector.get_columns(table_name, schema=schema)}

    for column in _column_definitions(df):
        if column.name in existing:
            continue

        column_type = column.type.compile(dialect=connection.dialect)
        logger.info(f"Adding missing column '{column.name}' to PostgreSQL table {table_name}")
        connection.execute(
            text(
                f"ALTER TABLE {_qualified_name(table_name, schema)} "
                f"ADD COLUMN {_quote(column.name)} {column_type}"
            )
        )


def _coerce_data_frame(
    data: pl.DataFrame | pl.LazyFrame | str | os.PathLike[str],
) -> pl.DataFrame:
    """Normalize DataFrame inputs, including a parquet file path."""

    if isinstance(data, (str, os.PathLike)):
        parquet_path = Path(data)
        if not parquet_path.exists():
            raise FileNotFoundError(f"Parquet file does not exist: {parquet_path}")
        return pl.read_parquet(parquet_path)

    if isinstance(data, pl.LazyFrame):
        return data.collect()

    if isinstance(data, pl.DataFrame):
        return data

    raise TypeError(f"load_postgresql expects a Polars DataFrame or parquet path, got {type(data)!r}")


def load_postgresql(
    df: pl.DataFrame | pl.LazyFrame | str | os.PathLike[str],
    table_name: str,
    if_exists: str | None = None,
    engine: Engine | None = None,
    schema: str | None = None,
) -> int:
    """Load a transformed Polars DataFrame or parquet file into PostgreSQL.

    Args:
        df: Transformed weather data or a parquet file path.
        table_name: Destination table, e.g. ``openweather_manila``.
        if_exists: ``replace`` (default) refreshes the table, ``append`` keeps
            existing rows, ``fail`` raises when the table already exists. When
            omitted the ``POSTGRES_IF_EXISTS`` environment variable is used.
        engine: Optional SQLAlchemy engine (used by the test suite).
        schema: Optional PostgreSQL schema (defaults to the connection default).
    """

    df = _coerce_data_frame(df)

    if df.height == 0:
        logger.warning(f"No rows to load into PostgreSQL table {table_name}; skipping.")
        return 0

    mode = (if_exists or os.getenv("POSTGRES_IF_EXISTS") or DEFAULT_IF_EXISTS).strip().lower()
    if mode not in VALID_IF_EXISTS:
        raise ValueError(f"if_exists must be one of {VALID_IF_EXISTS}, got '{mode}'")

    engine = engine if engine is not None else get_engine()

    try:
        with engine.begin() as connection:

            inspector = inspect(connection)

            if inspector.has_table(table_name, schema=schema):
                if mode == "replace":
                    Table(table_name, MetaData(), schema=schema).drop(connection, checkfirst=True)
                elif mode == "fail":
                    raise ValueError(f"Table '{table_name}' already exists and if_exists='fail'")

            _create_table(connection, table_name, df, schema)
            _ensure_columns(connection, table_name, df, schema)

            table = Table(table_name, MetaData(), autoload_with=connection, schema=schema)
            rows = [
                {key: _clean_value(value) for key, value in row.items()}
                for row in df.to_dicts()
            ]
            connection.execute(table.insert(), rows)

        logger.info(f"Successfully loaded {len(rows)} row(s) into PostgreSQL table: {table_name}")
        return len(rows)

    except Exception as e:
        logger.error(f"Error loading data into PostgreSQL table {table_name}: {e}")
        raise


def load_data_to_postgresql(df: pl.DataFrame | pl.LazyFrame | str | os.PathLike[str], table_name: str, **kwargs: Any) -> int:
    """Backward-compatible alias used by older imports."""

    return load_postgresql(df, table_name, **kwargs)


def load_parquet_to_postgresql(
    parquet_path: str | os.PathLike[str],
    table_name: str,
    **kwargs: Any,
) -> int:
    """Load a local parquet file into PostgreSQL."""

    return load_postgresql(parquet_path, table_name, **kwargs)


def load_all_parquet_to_postgresql(
    parquet_dir: str | os.PathLike[str],
    table_name: str = "openweather_all",
    if_exists: str | None = None,
    engine: Engine | None = None,
    schema: str | None = None,
) -> int:
    """Load every parquet file in a directory into one PostgreSQL table."""

    directory = Path(parquet_dir)
    if not directory.exists():
        raise FileNotFoundError(f"Parquet directory does not exist: {directory}")

    files = sorted(directory.glob("*.parquet"))
    if not files:
        logger.warning(f"No parquet files found in {directory}; nothing to load.")
        return 0

    frames = [pl.read_parquet(file) for file in files]
    combined = pl.concat(frames, how="vertical_relaxed") if frames else pl.DataFrame()
    return load_postgresql(combined, table_name, if_exists=if_exists, engine=engine, schema=schema)

