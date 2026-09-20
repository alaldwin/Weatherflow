"""Create the PostgreSQL database used by the pipeline (idempotent).

The pipeline creates the database automatically when it is missing, so this
script exists for setups where you want to prepare the database beforehand or
check the connection from inside a container.

Usage:
    python -m scripts.create_database                                    # local
    docker compose run --rm app python -m scripts.create_database        # Docker
"""

from common.logging import get_logger
from pipeline.loaded.load_postresql import (
    create_database,
    database_exists,
    get_database_target,
    get_maintenance_database,
)

logger = get_logger(__name__, "create_database.log")


def main() -> int:
    """Ensure the configured database exists and report the result."""

    logger.info(
        f"Target server {get_database_target()} "
        f"(maintenance database: {get_maintenance_database()})"
    )

    try:
        if database_exists():
            logger.info("Database already exists; nothing to do.")
            return 0

        if create_database():
            logger.info("Database created. Run the pipeline to load the tables.")
            return 0

        logger.warning("Database was not created; check the connection details.")
        return 1

    except Exception as exc:
        logger.error(f"Could not prepare the database: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())