"""Inspect the tables the pipeline loaded into PostgreSQL.

Usage:
    python -m scripts.inspect_data
    python -m scripts.inspect_data "SELECT city, temperature FROM openweather_manila;"
    docker compose run --rm --no-deps app python -m scripts.inspect_data
"""

import sys

from sqlalchemy import text

from common.logging import get_logger
from pipeline.loaded.load_postresql import get_database_target, get_engine

logger = get_logger(__name__, "inspect_data.log")

LIST_TABLES_SQL = """
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name
"""


def list_tables(engine) -> list[str]:
    """Return the public table names of the target database."""

    with engine.connect() as connection:
        return [row[0] for row in connection.execute(text(LIST_TABLES_SQL))]


def main(argv: list[str] | None = None) -> int:
    """Print a table summary, or the result of the query passed on the CLI."""

    argv = sys.argv[1:] if argv is None else argv

    try:
        engine = get_engine()
        with engine.connect() as connection:
            tables = list_tables(engine)

            if not tables:
                logger.warning(
                    f"No tables found in {get_database_target()}. "
                    "Run the pipeline first (python -m pipeline.main)."
                )
                return 1

            logger.info(f"{get_database_target()} contains {len(tables)} table(s):")

            for table in tables:
                count = connection.execute(
                    text(f'SELECT COUNT(*) FROM "{table}"')
                ).scalar_one()
                print(f"  {table}: {count} row(s)")

            if argv:
                query = argv[0]
                print(f"\n{query}")
                result = connection.execute(text(query))
                for row in result:
                    print("  ", tuple(row))

        return 0

    except Exception as exc:
        logger.error(f"Could not inspect the database: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())