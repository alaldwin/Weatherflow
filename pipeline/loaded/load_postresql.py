import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
import pandas as pd

from common.logging import get_logger

logger = get_logger(__name__, "load_postresql.log")

load_dotenv()


def build_database_url() -> str:
    """Build the PostgreSQL URL from environment variables."""
    required_vars = [
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing PostgreSQL environment variables: {', '.join(missing)}")

    return (
        f"postgresql+psycopg2://"
        f"{os.getenv('POSTGRES_USER')}:"
        f"{os.getenv('POSTGRES_PASSWORD')}@"
        f"{os.getenv('POSTGRES_HOST')}:"
        f"{os.getenv('POSTGRES_PORT')}/"
        f"{os.getenv('POSTGRES_DB')}"
    )


def load_postgresql(df, table_name):
    """Load the Polars DataFrame into a PostgreSQL database."""
    try:
        engine = create_engine(build_database_url())

        # Convert Polars DataFrame to pandas for reliable to_sql behavior
        # Avoid using Polars' to_pandas() (may require optional arrow deps).
        if hasattr(df, "to_dicts"):
            pdf = pd.DataFrame(df.to_dicts())
        elif hasattr(df, "to_pandas"):
            pdf = df.to_pandas()
        else:
            pdf = pd.DataFrame(df)

        # Use default to_sql writer (avoid method requiring optional extras)
        pdf.to_sql(name=table_name, con=engine, if_exists="replace", index=False)

        logger.info(f"Successfully loaded data into PostgreSQL table: {table_name}")
        return True
    except Exception as e:
        logger.error(f"Error loading data into PostgreSQL table {table_name}: {e}")
        raise


def load_data_to_postgresql(df, table_name):
    """Backward-compatible alias used by older imports."""
    return load_postgresql(df, table_name)

